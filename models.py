# models.py
from pydantic import BaseModel
from typing import List

class LikeRequest(BaseModel):
    user_id: str
    movie_title: str

class RecommendResponse(BaseModel):
    title: str
    genres: List[str]

class UserSignup(BaseModel):
    user_id: str
    password: str

class UserLogin(BaseModel):
    user_id: str
    password: str

