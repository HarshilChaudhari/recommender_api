from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional # Import Optional for user_id in search
from recommender import (
    like_movie,
    dislike_movie,
    undislike_movie, # Import the new undislike_movie function
    train_model,
    recommend_content_based,
    search_movies as recommender_search_movies # Alias to avoid name collision
)
from models import LikeRequest, UserSignup, UserLogin
from utils.auth_utils import hash_password, verify_password, get_current_user
from db import users_collection, likes_collection, dislikes_collection
import pickle
import pandas as pd
import jwt
import os
from fastapi.middleware.cors import CORSMiddleware
import math # Import math for ceil

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
    token = jwt.encode({"user_id": db_user["user_id"]}, SECRET_KEY, algorithm="HS256") # Use db_user["user_id"] to be safe
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
        background_tasks.add_task(train_model) # Assuming train_model is cheap or truly background
        return {"message": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) # Return 404 if movie not found
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/dislike")
def dislike(req: LikeRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    try:
        result = dislike_movie(user_id, req.tmdb_id, req.movie_title)
        background_tasks.add_task(train_model) # Assuming train_model is cheap or truly background
        return {"message": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) # Return 404 if movie not found
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/undislike")
def undislike(req: LikeRequest, user_id: str = Depends(get_current_user)):
    try:
        # Call the new undislike_movie function from recommender.py
        result_message = undislike_movie(user_id, req.tmdb_id, req.movie_title)
        # You might want to run train_model in background here too if needed
        # background_tasks.add_task(train_model)
        return {"message": result_message}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) # No dislike found for user/movie
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/disliked")
def get_disliked_movies(
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000)
):
    try:
        entries = list(dislikes_collection.find({"user_id": user_id}))
        tmdb_ids = [entry["tmdb_id"] for entry in entries]
        movies = movies_df[movies_df["tmdb_id"].isin(tmdb_ids)]
        
        total_results = len(movies)
        total_pages = math.ceil(total_results / page_size) if total_results > 0 else 0

        start = (page - 1) * page_size
        end = start + page_size
        paginated_df = movies.iloc[start:end].astype(object) # Ensure correct types for JSON serialization

        return {
            "movies": paginated_df[["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]].to_dict(orient="records"),
            "total_results": total_results, # Updated to total_results
            "total_pages": total_pages, # New field
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/train")
def train():
    try:
        message = train_model() # train_model now returns a message
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/recommend")
def recommend(
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100) # Keep page_size reasonable for recommendations
):
    try:
        # recommend_content_based now returns {movies, total_results, total_pages, page, page_size}
        # Pass the global model data
        recommendation_data = recommend_content_based(user_id, movies_df, tfidf_matrix, tfidf_vectorizer, page, page_size)
        return recommendation_data
    except ValueError as e: # Handle specific ValueErrors from recommender.py (e.g., no liked movies)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# -------------------------------
# Browse/Search/Liked/All Movies Routes
# -------------------------------

@app.get("/popular")
def get_popular_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    try:
        # Sort by vote_count and vote_average to get popular movies
        sorted_df = movies_df.sort_values(
            by=["vote_count", "vote_average"],
            ascending=False
        )
        
        total_results = len(sorted_df)
        total_pages = math.ceil(total_results / page_size) if total_results > 0 else 0

        start = (page - 1) * page_size
        end = start + page_size
        paginated_df = sorted_df.iloc[start:end][["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]]
        
        return {
            "movies": paginated_df.astype(object).to_dict(orient="records"),
            "total_results": total_results,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/search")
def search_movies_endpoint( # Renamed to avoid conflict with imported recommender_search_movies
    query: str = Query(..., min_length=2),
    scope: str = Query("all", regex="^(all|liked|disliked|recommended)$"), # Added 'disliked' scope
    user_id: Optional[str] = Depends(get_current_user), # user_id is optional for 'all' scope
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    try:
        # Validate user_id for scoped searches
        if scope in ["liked", "disliked", "recommended"] and not user_id:
            raise HTTPException(status_code=400, detail=f"User ID is required for '{scope}' scope search.")

        # Call the search function from recommender.py
        # Pass movies_df because the recommender_search_movies function in recommender.py
        # now accepts it as part of its internal logic, and it needs access to the main movie data.
        # Also pass user_id explicitly for scoped searches.
        search_results = recommender_search_movies(
            query=query,
            scope=scope,
            page=page,
            page_size=page_size,
           # movies_df=movies_df, # Pass movies_df
           # user_id=user_id # Pass user_id
        )
        return search_results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/movies")
def get_all_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    try:
        total_results = len(movies_df)
        total_pages = math.ceil(total_results / page_size) if total_results > 0 else 0

        start = (page - 1) * page_size
        end = start + page_size

        # Sort by vote_count and release_date to give some ordering to "all" movies
        sorted_df = movies_df.sort_values(by=["vote_count", "release_date"], ascending=[False, False])
        movies = sorted_df.iloc[start:end][["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]]

        return {
            "movies": movies.astype(object).to_dict(orient="records"),
            "total_results": total_results, # Updated to total_results
            "total_pages": total_pages, # New field
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/liked")
def get_liked_movies(
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000) # Increased max page_size for liked movies full refresh
):
    try:
        liked_entries = list(likes_collection.find({"user_id": user_id}))
        liked_tmdb_ids = [entry["tmdb_id"] for entry in liked_entries]
        liked_movies = movies_df[movies_df["tmdb_id"].isin(liked_tmdb_ids)]

        total_results = len(liked_movies)
        total_pages = math.ceil(total_results / page_size) if total_results > 0 else 0

        start = (page - 1) * page_size
        end = start + page_size

        paginated_df = liked_movies.iloc[start:end].astype(object)

        return {
            "movies": paginated_df[["title", "genres", "poster_path", "release_date", "overview", "tmdb_id"]].to_dict(orient="records"),
            "total_results": total_results, # Updated to total_results
            "total_pages": total_pages, # New field
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
