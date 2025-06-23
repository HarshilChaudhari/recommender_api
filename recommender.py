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

def like_movie(user_id, movie_title):
    match = movies_df[movies_df["title"].str.lower() == movie_title.lower()]
    if match.empty:
        raise ValueError(f"Movie '{movie_title}' not found.")

    tmdb_id = match.iloc[0]["tmdb_id"]

    likes_collection.update_one(
        {"user_id": user_id, "tmdb_id": int(tmdb_id)},
        {"$set": {"user_id": user_id, "tmdb_id": int(tmdb_id)}},
        upsert=True
    )

    load_likes_from_db()
    return f"👍 User {user_id} liked '{movie_title}'"


# ---------------------------
# Dislike a movie
# ---------------------------

def dislike_movie(user_id, movie_title):
    match = movies_df[movies_df["title"].str.lower() == movie_title.lower()]
    if match.empty:
        raise ValueError(f"Movie '{movie_title}' not found.")

    tmdb_id = match.iloc[0]["tmdb_id"]

    result = likes_collection.delete_one({
        "user_id": user_id,
        "tmdb_id": int(tmdb_id)
    })

    if result.deleted_count == 0:
        raise ValueError(f"No like found for user {user_id} and movie '{movie_title}'")

    load_likes_from_db()  # Rebuild encoder and interactions
    return f"👎 User {user_id} disliked '{movie_title}'"


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

    top_items = np.argsort(-scores)[:n]
    tmdb_ids = movie_enc.inverse_transform(top_items)

    return movies_df[movies_df["tmdb_id"].isin(tmdb_ids)][["title", "genres"]].reset_index(drop=True)

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
