from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from typing import List
from recommender import like_movie, recommend_hybrid, train_model, dislike_movie
from models import LikeRequest, RecommendResponse, UserSignup, UserLogin
from utils.auth_utils import hash_password, verify_password, get_current_user
from db import users_collection
import pickle
import pandas as pd
import jwt
import os

app = FastAPI(
    title="🎬 Movie Recommender API",
    description="Hybrid recommendation system using FastAPI + LightFM + MongoDB",
    version="1.0.0"
)

SECRET_KEY = os.getenv("SECRET_KEY", "fd1b2d22ccf1b78d895b82d435671359bd2404ada60e8548cf71fa96fb998988")

# -------------------------------
# Load preprocessed movies data
# -------------------------------
with open("data/preprocessed_model_data.pkl", "rb") as f:
    data = pickle.load(f)
movies_df = data["movies_df"]

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
# API Routes
# -------------------------------

@app.get("/")
def root():
    return {"message": "Welcome to the Movie Recommender API!"}


@app.post("/like")
def like(req: LikeRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    try:
        result = like_movie(user_id, req.movie_title)
        background_tasks.add_task(train_model)
        return {"message": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/dislike")
def dislike(req: LikeRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    try:
        result = dislike_movie(user_id, req.movie_title)
        background_tasks.add_task(train_model)
        return {"message": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")



@app.post("/train")
def train():
    try:
        train_model()
        return {"message": "✅ Model trained successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/recommend", response_model=List[RecommendResponse])
def recommend(user_id: str = Depends(get_current_user)):
    try:
        df = recommend_hybrid(user_id)
        return df.to_dict(orient="records")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/popular")
def get_popular_movies(n: int = 20):
    try:
        top_movies = movies_df.sort_values(
            by=["vote_count", "vote_average"],
            ascending=False
        ).head(n)[["title", "genres"]]
        return top_movies.reset_index(drop=True).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/search")
def search_movies(query: str = Query(..., min_length=2)):
    try:
        results = movies_df[movies_df["title"].str.contains(query, case=False, na=False)]
        return results[["title", "genres"]].head(20).reset_index(drop=True).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
