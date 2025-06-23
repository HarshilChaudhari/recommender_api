from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from recommender import like_movie, recommend_hybrid, train_model
from models import LikeRequest, RecommendResponse
import pickle
import pandas as pd

app = FastAPI(
    title="🎬 Movie Recommender API",
    description="Hybrid recommendation system using FastAPI + LightFM + MongoDB",
    version="1.0.0"
)

# -------------------------------
# Load preprocessed movies data
# -------------------------------
with open("data/preprocessed_model_data.pkl", "rb") as f:
    data = pickle.load(f)
movies_df = data["movies_df"]

# -------------------------------
# API Routes
# -------------------------------

@app.get("/")
def root():
    return {"message": "Welcome to the Movie Recommender API!"}


@app.post("/like")
def like(req: LikeRequest):
    try:
        result = like_movie(req.user_id, req.movie_title)
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


@app.get("/recommend/{user_id}", response_model=List[RecommendResponse])
def recommend(user_id: str, n: Optional[int] = 10):
    try:
        df = recommend_hybrid(user_id, n=n)
        return df.to_dict(orient="records")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/popular")
def get_popular_movies(n: int = 20):
    """Return top n popular movies based on vote count and average."""
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
    """Search movies by title keyword."""
    try:
        results = movies_df[movies_df["title"].str.contains(query, case=False, na=False)]
        return results[["title", "genres"]].head(20).reset_index(drop=True).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
