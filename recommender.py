import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from scipy.sparse import coo_matrix
from lightfm import LightFM

# Load preprocessed data
with open("data/preprocessed_model_data.pkl", "rb") as f:
    data = pickle.load(f)

movies_df = data["movies_df"]
movie_enc = data["movie_enc"]
item_features_sparse = data["item_features_sparse"]

likes_data = []
user_enc = LabelEncoder()

def like_movie(user_id, movie_title):
    global likes_data

    match = movies_df[movies_df["title"].str.lower() == movie_title.lower()]
    if match.empty:
        raise ValueError(f"Movie '{movie_title}' not found.")

    tmdb_id = match.iloc[0]["tmdb_id"]
    movie_idx = movie_enc.transform([tmdb_id])[0]

    # Initialize LabelEncoder with the first user
    if not hasattr(user_enc, "classes_"):
        user_enc.fit([user_id])

    # Register user if not already encoded
    if user_id not in user_enc.classes_:
        new_classes = list(user_enc.classes_) + [user_id]
        user_enc.classes_ = np.array(new_classes)

    user_idx = user_enc.transform([user_id])[0]
    likes_data.append((user_idx, movie_idx))

    return f"👍 User {user_id} liked '{movie_title}'"


def train_model():
    global model, interactions

    if not likes_data:
        raise ValueError("No likes provided yet.")

    user_ids, movie_ids = zip(*likes_data)
    interactions = coo_matrix((np.ones(len(user_ids)), (user_ids, movie_ids)),
                              shape=(len(user_enc.classes_), len(movie_enc.classes_)))

    model = LightFM(loss='warp')
    model.fit(interactions, item_features=item_features_sparse, epochs=10, num_threads=2)

def recommend_hybrid(user_id, n=10):
    if not hasattr(user_enc, "classes_"):
        raise ValueError(f"User encoder not initialized. Have any users liked movies?")

    if user_id not in user_enc.classes_:
        raise ValueError(f"User ID {user_id} not found. Like a movie first.")

    user_idx = user_enc.transform([user_id])[0]
    scores = model.predict(
        user_ids=np.repeat(user_idx, len(movie_enc.classes_)),
        item_ids=np.arange(len(movie_enc.classes_)),
        item_features=item_features_sparse
    )
    top_items = np.argsort(-scores)[:n]
    tmdb_ids = movie_enc.inverse_transform(top_items)

    return movies_df[movies_df["tmdb_id"].isin(tmdb_ids)][["title", "genres"]].reset_index(drop=True)
