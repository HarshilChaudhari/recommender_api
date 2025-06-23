from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from recommender import like_movie, recommend_hybrid, train_model

app = FastAPI(
    title="🎬 Movie Recommender API",
    description="Hybrid recommendation system using FastAPI + LightFM",
    version="1.0.0"
)

# -------------------------------
# Request Models
# -------------------------------

class LikeRequest(BaseModel):
    user_id: str
    movie_title: str

class RecommendResponse(BaseModel):
    title: str
    genres: List[str]

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


@app.post("/train")
def train():
    try:
        train_model()
        return {"message": "✅ Model trained successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/recommend/{user_id}", response_model=List[RecommendResponse])
def recommend(user_id: str, n: Optional[int] = 10):
    try:
        df = recommend_hybrid(user_id, n=n)
        return df.to_dict(orient="records")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
