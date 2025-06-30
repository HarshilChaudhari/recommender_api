# db.py
from pymongo import MongoClient
import os
 #mongodb+srv://Harshil:Harsh%4012345@cluster0.v0f2u.mongodb.net/Movie?retryWrites=true&w=majority&appName=Cluster0
# Replace with your actual MongoDB URI or use environment variable
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Harshil:Harsh%4012345@cluster0.v0f2u.mongodb.net/Movie?retryWrites=true&w=majority&appName=Cluster0")

client = MongoClient(MONGO_URI)
db = client.movie_recommender
likes_collection = db.likes
users_collection = db.users
dislikes_collection = db.dislikes
