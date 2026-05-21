import os
import json
from pydantic import BaseModel, Field
from typing import List
from google import genai
from google.genai import types
import datetime
from dotenv import load_dotenv
from src.database import get_db, get_profile, get_hackathons

# Load env variables
load_dotenv()

# Pydantic schemas for Gemini Structured Outputs
class MatchItem(BaseModel):
    url: str = Field(description="The exact Devpost URL of the hackathon being evaluated")
    match_score: int = Field(description="Integrity score between 1 and 10 based on developer profile alignment")
    match_reason: str = Field(description="A concise, high-value one-line reason (max 120 chars) explaining the score and fit")

class MatchResultsSchema(BaseModel):
    matches: List[MatchItem]

def match_hackathons_with_gemini():
    """
    Evaluates hackathons against the user profile using Gemini 2.0 Flash.
    Saves scores and reasons back to the hackathons collection.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set in the .env file. Skipping Gemini matching.")
        return False
        
    profile = get_profile()
    if not profile:
        print("No user profile found. Please complete Step 1 (User Profile Input) first.")
        return False
        
    hackathons = get_hackathons(sort_by_score=False)
    if not hackathons:
        print("No hackathons found in the database. Please run Step 2 (Devpost Scraper) first.")
        return False
        
    print(f"Starting matching process for {len(hackathons)} hackathons...")
    
    # Initialize the new Google GenAI client
    client = genai.Client(api_key=api_key)
    
    # Prepare the prompt context
    developer_profile_str = f"""
    === DEVELOPER PROFILE ===
    - Tech Stack: {', '.join(profile.get('tech_stack', []))}
    - Interests: {', '.join(profile.get('interests', []))}
    - Experience Level: {profile.get('experience_level', 'Intermediate')}
    - Weekly Availability: {profile.get('weekly_availability', '10 hours')}
    """
    
    # Format hackathons list for Gemini (keep it concise to save tokens)
    hackathons_data = []
    for h in hackathons:
        hackathons_data.append({
            "title": h.get("title"),
            "url": h.get("url"),
            "tags": h.get("tags", []),
            "prize_pool": h.get("prize_pool", "N/A"),
            "eligibility": h.get("eligibility", "Open")
        })
        
    prompt = f"""
    You are an expert technical recruiter and AI agent specializing in hackathon team composition and candidate matching.
    Your task is to evaluate a list of hackathons against a developer's profile and score each hackathon on a scale of 1 to 10.
    
    {developer_profile_str}
    
    === HACKATHONS TO EVALUATE ===
    {json.dumps(hackathons_data, indent=2)}
    
    === INSTRUCTIONS ===
    For each hackathon in the list, evaluate how well it matches the developer's tech stack, interests, experience, and time constraints.
    - A score of 10 means perfect stack alignment, extreme interest match, and appropriate experience.
    - A score of 1 means zero alignment or impossible constraints.
    - Provide a concise, professional, and inspiring one-line reason (under 120 characters) highlighting why the hackathon is a fit (or why not).
    
    You must output your evaluation matching the requested JSON schema.
    """
    
    try:
        # Call Gemini 2.0 Flash with Structured Output Config
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MatchResultsSchema,
                temperature=0.2,
            ),
        )
        
        # Parse the structured response
        results_data = json.loads(response.text)
        matches = results_data.get("matches", [])
        
        # Save scores back to MongoDB
        db = get_db()
        updated_count = 0
        
        for item in matches:
            url = item.get("url")
            score = item.get("match_score")
            reason = item.get("match_reason")
            
            # Update the hackathon document
            res = db.hackathons.update_one(
                {"url": url},
                {"$set": {
                    "match_score": score,
                    "match_reason": reason,
                    "evaluated_at": datetime.datetime.now()
                }}
            )
            updated_count += res.modified_count
            
        print(f"Gemini Matching complete. Scored and updated {updated_count} hackathons in the database.")
        return True
        
    except Exception as e:
        print(f"Error during Gemini matching: {e}")
        return False

if __name__ == "__main__":
    # Test script locally
    match_hackathons_with_gemini()
