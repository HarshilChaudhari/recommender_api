import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from scipy.sparse import coo_matrix
from lightfm import LightFM
from db import likes_collection

# ---------------------------
# Load model data from file
# ---------------------------

with open("data/preprocessed_model_data.pkl", "rb") as f:
    data = pickle.load(f)

movies_df = data["movies_df"]
movie_enc = data["movie_enc"]
item_features_sparse = data["item_features_sparse"]

# ---------------------------
# Globals
# ---------------------------

user_enc = LabelEncoder()
likes_data = []
interactions = None
model = None

# ---------------------------
# Load Likes from MongoDB
# ---------------------------

def load_likes_from_db():
    global likes_data, user_enc

    all_likes = list(likes_collection.find({}))
    if not all_likes:
        print("ℹ️ No likes in database.")
        return

    user_ids = sorted({like["user_id"] for like in all_likes})
    user_enc.fit(user_ids)

    likes_data.clear()
    for entry in all_likes:
        try:
            user_idx = user_enc.transform([entry["user_id"]])[0]
            movie_idx = movie_enc.transform([entry["tmdb_id"]])[0]
            likes_data.append((user_idx, movie_idx))
        except:
            continue

# ---------------------------
# Train the model
# ---------------------------

def train_model():
    global model, interactions

    if not likes_data:
        raise ValueError("No likes provided yet.")

    user_ids, movie_ids = zip(*likes_data)
    interactions = coo_matrix(
        (np.ones(len(user_ids)), (user_ids, movie_ids)),
        shape=(len(user_enc.classes_), len(movie_enc.classes_))
    )

    model = LightFM(loss="warp")
    model.fit(interactions, item_features=item_features_sparse, epochs=10, num_threads=2)
    print("✅ Model trained.")


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

    load_likes_from_db()
    title = movies_df[movies_df["tmdb_id"] == tmdb_id].iloc[0]["title"]
    return f"👍 User {user_id} liked '{title}'"


# ---------------------------
# Dislike a movie
# ---------------------------

def dislike_movie(user_id, tmdb_id, movie_title=None):
    result = likes_collection.delete_one({"user_id": user_id, "tmdb_id": tmdb_id})
    
    if result.deleted_count == 0:
        raise ValueError(f"No like found for user {user_id} and tmdb_id {tmdb_id}")
    
    load_likes_from_db()
    title = movies_df[movies_df["tmdb_id"] == tmdb_id].iloc[0]["title"]
    return f"👎 User {user_id} disliked '{title}'"



# ---------------------------
# Recommend movies
# ---------------------------

def recommend_hybrid(user_id, n=10):
    if model is None:
        raise ValueError("Model not trained yet. Please train first.")

    if user_id not in user_enc.classes_:
        raise ValueError(f"User {user_id} not found. Like a movie first.")

    user_idx = user_enc.transform([user_id])[0]
    scores = model.predict(
        user_ids=np.repeat(user_idx, len(movie_enc.classes_)),
        item_ids=np.arange(len(movie_enc.classes_)),
        item_features=item_features_sparse
    )

    # Get tmdb_ids of movies the user has already liked
    liked_entries = list(likes_collection.find({"user_id": user_id}))
    liked_tmdb_ids = set(entry["tmdb_id"] for entry in liked_entries)

    # Filter out liked movies
    all_tmdb_ids = movie_enc.inverse_transform(np.arange(len(scores)))
    mask = np.array([tmdb_id not in liked_tmdb_ids for tmdb_id in all_tmdb_ids])

    filtered_scores = scores[mask]
    filtered_tmdb_ids = all_tmdb_ids[mask]

    if len(filtered_scores) == 0:
        return pd.DataFrame(columns=["tmdb_id", "title", "genres", "poster_path", "score", "release_date", "overview"])

    top_indices = np.argsort(-filtered_scores)[:n]
    top_tmdb_ids = filtered_tmdb_ids[top_indices]
    top_scores = filtered_scores[top_indices]

    # Extract movie info and attach scores
    movie_info = movies_df[movies_df["tmdb_id"].isin(top_tmdb_ids)].copy()
    movie_info["score"] = movie_info["tmdb_id"].map(dict(zip(top_tmdb_ids, top_scores)))
    movie_info = movie_info.sort_values(by="score", ascending=False)

    return movie_info[["tmdb_id", "title", "genres", "poster_path", "score", "release_date", "overview"]]





# ---------------------------
# Automatically retrain on startup
# ---------------------------

load_likes_from_db()
if likes_data:
    try:
        train_model()
    except Exception as e:
        print("⚠️ Error during model training:", str(e))
else:
    print("ℹ️ No likes found on startup — model not trained.")

