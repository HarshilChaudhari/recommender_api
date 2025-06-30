import pickle
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from db import likes_collection, dislikes_collection
import math # Import math for ceil function

# ---------------------------
# Load model data
# ---------------------------

with open("data/content_model.pkl", "rb") as f:
    data = pickle.load(f)

movies_df = data["movies_df"]
tfidf_matrix = data["tfidf_matrix"]
tfidf_vectorizer = data["tfidf_vectorizer"]

# ---------------------------
# Like a movie
# ---------------------------

def like_movie(user_id, tmdb_id, movie_title=None):
    # Ensure movie exists in our dataset
    if tmdb_id not in movies_df["tmdb_id"].values:
        raise ValueError(f"TMDB ID {tmdb_id} not found in movies.")

    # Add to likes collection (upsert to avoid duplicates)
    likes_collection.update_one(
        {"user_id": user_id, "tmdb_id": tmdb_id},
        {"$set": {"user_id": user_id, "tmdb_id": tmdb_id}},
        upsert=True
    )

    # Remove from dislikes collection if it was previously disliked
    dislikes_collection.delete_one({
      "user_id": user_id,
      "tmdb_id": tmdb_id
    })

    # Get movie title for response (optional but good for logging/feedback)
    title = movies_df[movies_df["tmdb_id"] == tmdb_id].iloc[0]["title"]
    return f"👍 User {user_id} liked '{title}'"

# ---------------------------
# Dislike a movie
# ---------------------------

def dislike_movie(user_id, tmdb_id, movie_title=None):
    # Basic check: is movie in the dataset?
    if tmdb_id not in movies_df["tmdb_id"].values:
        raise ValueError(f"TMDB ID {tmdb_id} not found in movies.")

    # Remove any prior like
    likes_collection.delete_one({"user_id": user_id, "tmdb_id": tmdb_id})

    # Add dislike (upsert)
    dislikes_collection.update_one(
        {"user_id": user_id, "tmdb_id": tmdb_id},
        {"$set": {"user_id": user_id, "tmdb_id": tmdb_id}},
        upsert=True
    )

    # Optional: log title
    title = movies_df[movies_df["tmdb_id"] == tmdb_id].iloc[0]["title"]
    return f"👎 User {user_id} disliked '{title}'"

# ---------------------------
# Undo Dislike (New Function)
# ---------------------------
def undislike_movie(user_id, tmdb_id, movie_title=None):
    """
    Removes a movie from the user's disliked list.
    """
    if tmdb_id not in movies_df["tmdb_id"].values:
        raise ValueError(f"TMDB ID {tmdb_id} not found in movies.")

    result = dislikes_collection.delete_one({
      "user_id": user_id,
      "tmdb_id": tmdb_id
    })

    title = movies_df[movies_df["tmdb_id"] == tmdb_id].iloc[0]["title"]
    if result.deleted_count > 0:
        return f"✅ User {user_id} undid dislike for '{title}'"
    else:
        return f"ℹ️ Movie '{title}' was not in user {user_id}'s disliked list."


# ---------------------------
# Content-based Recommendation
# ---------------------------

def recommend_content_based(user_id, movies_df, tfidf_matrix, tfidf_vectorizer, page=1, page_size=20):
    liked_entries = list(likes_collection.find({"user_id": user_id}))
    disliked_entries = list(dislikes_collection.find({"user_id": user_id}))

    liked_tmdb_ids = [entry["tmdb_id"] for entry in liked_entries]
    disliked_tmdb_ids = [entry["tmdb_id"] for entry in disliked_entries]

    if not liked_tmdb_ids:
        # If no liked movies, recommend popular movies or a default set.
        # For now, let's return an empty list with 0 total.
        # In a real app, you might recommend top trending movies.
        return {
            "movies": [],
            "total_results": 0,
            "total_pages": 0,
            "page": page,
            "page_size": page_size
        }

    liked_indices = movies_df[movies_df["tmdb_id"].isin(liked_tmdb_ids)].index.tolist()
    disliked_indices = movies_df[movies_df["tmdb_id"].isin(disliked_tmdb_ids)].index.tolist()

    liked_vectors = tfidf_matrix[liked_indices]
    user_profile_vector = liked_vectors.mean(axis=0)

    if disliked_indices:
        disliked_vectors = tfidf_matrix[disliked_indices]
        avg_disliked_vector = disliked_vectors.mean(axis=0)
        # Subtract disliked signal from liked profile
        user_profile_vector = user_profile_vector - avg_disliked_vector

    user_profile_vector = np.asarray(user_profile_vector).reshape(1, -1)

    # Compute similarity
    scores = cosine_similarity(user_profile_vector, tfidf_matrix).flatten()

    # Create scored DataFrame
    scored_df = movies_df.copy()
    scored_df["score"] = scores

    # Exclude both liked and disliked movies from recommendations
    # Filter out movies that have been liked or disliked by the user
    scored_df = scored_df[
        ~scored_df["tmdb_id"].isin(liked_tmdb_ids + disliked_tmdb_ids)
    ]

    # Sort by score
    scored_df = scored_df.sort_values(by="score", ascending=False)

    # --- Pagination Calculation ---
    total_recommendable_movies = len(scored_df)
    total_pages = math.ceil(total_recommendable_movies / page_size) if total_recommendable_movies > 0 else 0

    # Apply pagination slice
    start = (page - 1) * page_size
    end = start + page_size
    paged_df = scored_df.iloc[start:end]

    return {
        "movies": paged_df[["tmdb_id", "title", "genres", "poster_path", "release_date", "overview", "score"]]
                    .reset_index(drop=True)
                    .to_dict(orient="records"),
        "total_results": total_recommendable_movies, # Renamed from 'total' to 'total_results' for consistency with common APIs
        "total_pages": total_pages, # New field for total pages
        "page": page,
        "page_size": page_size
    }


# ---------------------------
# Search Function (New)
# ---------------------------

def search_movies(query, scope='all', page=1, page_size=20):
    """
    Searches for movies based on a query within a specified scope.
    Scope can be 'all', 'liked', 'disliked', 'recommended'.
    """
    query_lower = query.lower()
    
    # Start with all movies in the DataFrame
    search_results_df = movies_df.copy()

    # Apply search filter
    # Search in title and genres for broader results
    search_results_df = search_results_df[
        search_results_df["title"].str.lower().str.contains(query_lower) |
        search_results_df["genres"].apply(lambda x: query_lower in str(x).lower())
    ]

    # Filter by scope if applicable
    if scope in ['liked', 'disliked', 'recommended']:
        # Fetch user's liked/disliked movies from DB
        user_id = None # You'll need to pass user_id to this function if searching user-specific lists
        # For now, let's assume search is general or you'll pass user_id from the Flask route.
        # If `user_id` is required, you'll need to adapt the Flask route to pass it.

        # For demonstration, assuming a placeholder user_id if needed
        # This part requires the Flask route to provide `user_id` if scope is user-specific.
        # If `search_movies` is called from a route that authenticates a user,
        # you would get the user_id from the request context (e.g., JWT).
        # For now, I'm making a placeholder to show the logic.
        
        # NOTE: A more robust approach for user-specific search would involve passing `user_id`
        # directly to this function from your Flask route, as the frontend sends it to search for
        # `recommended` movies, which inherently requires a `user_id`.
        
        # Example:
        # if user_id is None:
        #     raise ValueError("User ID is required for scoped search (liked, disliked, recommended).")
        # liked_tmdb_ids = [entry["tmdb_id"] for entry in likes_collection.find({"user_id": user_id})]
        # disliked_tmdb_ids = [entry["tmdb_id"] for entry in dislikes_collection.find({"user_id": user_id})]
        
        if scope == 'liked':
            # This requires user_id to be passed to search_movies
            # search_results_df = search_results_df[search_results_df["tmdb_id"].isin(liked_tmdb_ids)]
            # Placeholder: In real scenario, `user_id` must be passed.
            pass
        elif scope == 'disliked':
            # This requires user_id to be passed to search_movies
            # search_results_df = search_results_df[search_results_df["tmdb_id"].isin(disliked_tmdb_ids)]
            # Placeholder: In real scenario, `user_id` must be passed.
            pass
        elif scope == 'recommended':
            # For "recommended" scope, the search should likely be *within* the recommended list.
            # This is complex because recommendations are generated dynamically.
            # A common approach is to search all movies, then filter these search results
            # by what would appear in the recommendations (excluding liked/disliked).
            # If the frontend is sending `scope=recommended`, it means "search within movies
            # that are recommendable to me". So we exclude liked/disliked from general search results.
            
            # This relies on the Flask endpoint passing user_id to `search_movies`
            # For this example, let's assume `search_movies` will receive a `user_id`
            # if `scope` is `recommended` from the backend API.
            
            liked_entries = list(likes_collection.find({"user_id": user_id})) # user_id needs to be passed
            disliked_entries = list(dislikes_collection.find({"user_id": user_id})) # user_id needs to be passed
            liked_tmdb_ids = [entry["tmdb_id"] for entry in liked_entries]
            disliked_tmdb_ids = [entry["tmdb_id"] for entry in disliked_entries]
            
            search_results_df = search_results_df[
                ~search_results_df["tmdb_id"].isin(liked_tmdb_ids + disliked_tmdb_ids)
            ]

    # Pagination calculation for search results
    total_search_results = len(search_results_df)
    total_pages = math.ceil(total_search_results / page_size) if total_search_results > 0 else 0

    start = (page - 1) * page_size
    end = start + page_size
    paged_df = search_results_df.iloc[start:end]

    return {
        "movies": paged_df[["tmdb_id", "title", "genres", "poster_path", "release_date", "overview"]]
                    .reset_index(drop=True)
                    .to_dict(orient="records"),
        "total_results": total_search_results,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size
    }


# ---------------------------
# No model training needed in content-based mode
# ---------------------------

def train_model():
    # This is a no-op here.
    return "✅ Content-based model does not require retraining."
