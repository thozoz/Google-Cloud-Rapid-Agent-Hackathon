import os
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

# Load env variables
load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = "hackathon_agent"

_client = None

def get_db():
    global _client
    if not MONGO_URI:
        raise ValueError("MONGODB_URI environment variable is not set in your .env file.")
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DB_NAME]

def init_db():
    """Initializes collections and indexes."""
    db = get_db()
    
    # Ensure unique index on Devpost URL in hackathons collection to prevent duplicates
    db.hackathons.create_index("url", unique=True)
    
    # Ensure unique index on URL in tracked collection
    db.tracked.create_index("url", unique=True)
    print("Database collections and indexes initialized successfully.")

def save_profile(profile_data):
    """Saves or updates the user profile."""
    db = get_db()
    # We use a static id to represent the single user's profile
    db.profile.update_one(
        {"_id": "user_profile"},
        {"$set": profile_data},
        upsert=True
    )
    return profile_data

def get_profile():
    """Retrieves the user profile, or returns None if it doesn't exist."""
    db = get_db()
    return db.profile.find_one({"_id": "user_profile"})

def save_hackathons(hackathons_list):
    """Bulk inserts or updates hackathons based on their unique URL."""
    if not hackathons_list:
        return 0
    
    db = get_db()
    operations = []
    for h in hackathons_list:
        operations.append(
            UpdateOne(
                {"url": h["url"]},
                {"$set": h},
                upsert=True
            )
        )
    
    result = db.hackathons.bulk_write(operations)
    return result.upserted_count + result.modified_count

def get_hackathons(sort_by_score=True):
    """Retrieves all hackathons from the database."""
    db = get_db()
    cursor = db.hackathons.find()
    hackathons = list(cursor)
    
    # Standardize _id to string for JSON serialization
    for h in hackathons:
        h["_id"] = str(h["_id"])
        
    if sort_by_score:
        # Sort descending by match_score, defaulting to 0 if not yet scored
        hackathons.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
    return hackathons

def track_hackathon(url, track=True):
    """Adds or removes a hackathon from the tracked collection."""
    db = get_db()
    if track:
        # Get the hackathon details
        hackathon = db.hackathons.find_one({"url": url})
        if not hackathon:
            raise ValueError(f"Hackathon with URL {url} not found in the scraped list.")
        
        # Insert into tracked collection
        hackathon["_id"] = str(hackathon["_id"])
        db.tracked.update_one(
            {"url": url},
            {"$set": hackathon},
            upsert=True
        )
        return True
    else:
        # Remove from tracked collection
        result = db.tracked.delete_one({"url": url})
        return result.deleted_count > 0

def get_tracked_hackathons():
    """Retrieves all tracked hackathons."""
    db = get_db()
    tracked = list(db.tracked.find())
    for t in tracked:
        t["_id"] = str(t["_id"])
    return tracked
