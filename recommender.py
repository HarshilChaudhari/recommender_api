import pickle
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from db import likes_collection

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
    if tmdb_id not in movies_df["tmdb_id"].values:
        raise ValueError(f"TMDB ID {tmdb_id} not found in movies.")

    likes_collection.update_one(
        {"user_id": user_id, "tmdb_id": tmdb_id},
        {"$set": {"user_id": user_id, "tmdb_id": tmdb_id}},
        upsert=True
    )

    title = movies_df[movies_df["tmdb_id"] == tmdb_id].iloc[0]["title"]
    return f"👍 User {user_id} liked '{title}'"

# ---------------------------
# Dislike a movie
# ---------------------------

def dislike_movie(user_id, tmdb_id, movie_title=None):
    result = likes_collection.delete_one({"user_id": user_id, "tmdb_id": tmdb_id})

    if result.deleted_count == 0:
        raise ValueError(f"No like found for user {user_id} and tmdb_id {tmdb_id}")

    title = movies_df[movies_df["tmdb_id"] == tmdb_id].iloc[0]["title"]
    return f"👎 User {user_id} disliked '{title}'"

# ---------------------------
# Content-based Recommendation
# ---------------------------

def recommend_content_based(user_id, movies_df, tfidf_matrix, tfidf_vectorizer, page=1, page_size=20):
    from db import likes_collection

    liked_entries = list(likes_collection.find({"user_id": user_id}))
    liked_tmdb_ids = [entry["tmdb_id"] for entry in liked_entries]

    if not liked_tmdb_ids:
        raise ValueError("User has not liked any movies.")

    # Get indices of liked movies
    liked_indices = movies_df[movies_df["tmdb_id"].isin(liked_tmdb_ids)].index.tolist()

    if not liked_indices:
        raise ValueError("Liked movies not found in dataset.")

    # Average TF-IDF vector of liked movies
    liked_vectors = tfidf_matrix[liked_indices]
    user_profile_vector = liked_vectors.mean(axis=0)

    # Fix: Convert matrix to ndarray
    user_profile_vector = np.asarray(user_profile_vector).reshape(1, -1)

    # Compute cosine similarity and flatten to 1D array
    scores = cosine_similarity(user_profile_vector, tfidf_matrix).flatten()

    # Build DataFrame with scores
    scored_df = movies_df.copy()
    scored_df["score"] = scores

    # Exclude already liked movies
    scored_df = scored_df[~scored_df["tmdb_id"].isin(liked_tmdb_ids)]

    # Sort by score
    scored_df = scored_df.sort_values(by="score", ascending=False)

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    paged_df = scored_df.iloc[start:end]

    return {
        "movies": paged_df[["tmdb_id", "title", "genres", "poster_path", "release_date", "overview", "score"]].reset_index(drop=True).to_dict(orient="records"),
        "total": len(scored_df),
        "page": page,
        "page_size": page_size
    }



# ---------------------------
# No model training needed in content-based mode
# ---------------------------

def train_model():
    # This is a no-op here.
    return "✅ Content-based model does not require retraining."


