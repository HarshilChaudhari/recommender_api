from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from typing import List
from recommender import (
    like_movie, dislike_movie, train_model,
    recommend_content_based
)
from models import LikeRequest, UserSignup, UserLogin
from utils.auth_utils import hash_password, verify_password, get_current_user
from db import users_collection, likes_collection, dislikes_collection 
import pickle
import pandas as pd
import jwt
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="🎬 Movie Recommender API",
    description="Content-based movie recommender using TF-IDF",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "fd1b2d22ccf1b78d895b82d435671359bd2404ada60e8548cf71fa96fb998988")

# -------------------------------
# Load model
# -------------------------------
with open("data/content_model.pkl", "rb") as f:
    model_data = pickle.load(f)

movies_df = model_data["movies_df"]
tfidf_matrix = model_data["tfidf_matrix"]
tfidf_vectorizer = model_data["tfidf_vectorizer"]

# -------------------------------
# Auth Endpoints
# -------------------------------

@app.post("/signup")
def signup(user: UserSignup):
    if users_collection.find_one({"user_id": user.user_id}):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_pw = hash_password(user.password)
    users_collection.insert_one({"user_id": user.user_id, "password": hashed_pw})
    return {"message": "✅ User registered successfully"}

@app.post("/login")
def login(user: UserLogin):
    db_user = users_collection.find_one({"user_id": user.user_id})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode({"user_id": user.user_id}, SECRET_KEY, algorithm="HS256")
    return {"token": token}

# -------------------------------
# Recommendation Routes
# -------------------------------

@app.get("/")
def root():
    return {"message": "Welcome to the Movie Recommender API!"}

@app.post("/like")
def like(req: LikeRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    try:
        result = like_movie(user_id, req.tmdb_id, req.movie_title)
        background_tasks.add_task(train_model)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/dislike")
def dislike(req: LikeRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    try:
        result = dislike_movie(user_id, req.tmdb_id, req.movie_title)
        background_tasks.add_task(train_model)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/undislike")
def undislike(req: LikeRequest, user_id: str = Depends(get_current_user)):
    from db import dislikes_collection
    try:
        result = dislikes_collection.delete_one({"user_id": user_id, "tmdb_id": req.tmdb_id})
        if result.deleted_count == 0:
            raise ValueError(f"No dislike found for user {user_id} and tmdb_id {req.tmdb_id}")
        return {"message": f"🗑️ Removed dislike for {req.movie_title}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/disliked")
def get_disliked_movies(
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000)
):
    try:
        from db import dislikes_collection
        entries = list(dislikes_collection.find({"user_id": user_id}))
        tmdb_ids = [entry["tmdb_id"] for entry in entries]
        movies = movies_df[movies_df["tmdb_id"].isin(tmdb_ids)]
        total = len(movies)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_df = movies.iloc[start:end].astype(object)
        return {
            "movies": paginated_df[["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]].to_dict(orient="records"),
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/train")
def train():
    try:
        train_model()
        return {"message": "✅ Model trained successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/recommend")
def recommend(
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    try:
        return recommend_content_based(user_id, movies_df, tfidf_matrix, tfidf_vectorizer, page, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# -------------------------------
# Browse/Search/Liked Routes
# -------------------------------

@app.get("/popular")
def get_popular_movies(n: int = 20):
    try:
        top_movies = movies_df.sort_values(
            by=["vote_count", "vote_average"],
            ascending=False
        ).head(n)[["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]]
        return top_movies.reset_index(drop=True).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/search")
def search_movies(
    query: str = Query(..., min_length=2),
    scope: str = Query("all", regex="^(all|liked|recommended)$"),
    user_id: str = Depends(get_current_user)
):
    try:
        if scope == "all":
            results = movies_df[movies_df["title"].str.contains(query, case=False, na=False)]
        elif scope == "liked":
            liked_entries = list(likes_collection.find({"user_id": user_id}))
            liked_tmdb_ids = [entry["tmdb_id"] for entry in liked_entries]
            liked_movies = movies_df[movies_df["tmdb_id"].isin(liked_tmdb_ids)]
            results = liked_movies[liked_movies["title"].str.contains(query, case=False, na=False)]
        elif scope == "recommended":
            df = recommend_content_based(user_id, movies_df, tfidf_matrix, tfidf_vectorizer)
            results = df[df["title"].str.contains(query, case=False, na=False)]
        else:
            raise HTTPException(status_code=400, detail="Invalid scope")
        
        results = results.astype(object)
        return results[["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]].head(20).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/movies")
def get_all_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    try:
        start = (page - 1) * page_size
        end = start + page_size
        total = len(movies_df)

        sorted_df = movies_df.sort_values(by=["vote_count", "release_date"], ascending=[False, False])
        movies = sorted_df.iloc[start:end][["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]]

        return {
            "movies": movies.astype(object).to_dict(orient="records"),
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/liked")
def get_liked_movies(
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000)
):
    try:
        liked_entries = list(likes_collection.find({"user_id": user_id}))
        liked_tmdb_ids = [entry["tmdb_id"] for entry in liked_entries]
        liked_movies = movies_df[movies_df["tmdb_id"].isin(liked_tmdb_ids)]

        total = len(liked_movies)
        start = (page - 1) * page_size
        end = start + page_size

        paginated_df = liked_movies.iloc[start:end].astype(object)

        return {
            "movies": paginated_df[["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]].to_dict(orient="records"),
            "total": total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")



