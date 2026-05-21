import os
import json
import re
import datetime
from pydantic import BaseModel, Field
from typing import List, Literal
from dotenv import load_dotenv
from src.database import get_db, get_profile, get_hackathons

load_dotenv()

# ---------------------------------------------------------------------------
# Pydantic schemas (used by Gemini structured output)
# ---------------------------------------------------------------------------

class MatchItem(BaseModel):
    url: str = Field(description="The exact Devpost URL of the hackathon being evaluated")
    match_score: int = Field(description="Score between 1 and 10 based on developer profile alignment")
    match_reason: str = Field(description="A concise one-line reason (max 120 chars) explaining the score")

class MatchResultsSchema(BaseModel):
    matches: List[MatchItem]

# ---------------------------------------------------------------------------
# Shared prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(profile: dict, hackathons: list) -> str:
    developer_profile_str = f"""
=== DEVELOPER PROFILE ===
- Tech Stack: {', '.join(profile.get('tech_stack', []))}
- Interests:  {', '.join(profile.get('interests', []))}
- Experience: {profile.get('experience_level', 'Intermediate')}
- Availability: {profile.get('weekly_availability', '10 hours')} per week
"""
    hackathons_data = [
        {
            "title": h.get("title"),
            "url": h.get("url"),
            "tags": h.get("tags", []),
            "prize_pool": h.get("prize_pool", "N/A"),
            "eligibility": h.get("eligibility", "Open"),
        }
        for h in hackathons
    ]

    return f"""You are an expert AI agent specializing in hackathon matching.
Evaluate each hackathon against the developer profile and score it 1-10.

{developer_profile_str}

=== HACKATHONS TO EVALUATE ===
{json.dumps(hackathons_data, indent=2)}

=== INSTRUCTIONS ===
- Score 10 = perfect stack/interest/experience alignment.
- Score 1  = no alignment at all.
- Provide a concise one-line reason under 120 characters.
- You MUST respond ONLY with valid JSON matching this exact schema:
  {{"matches": [{{"url": "...", "match_score": <int>, "match_reason": "..."}}]}}
- No extra text, no markdown fences, just raw JSON.
"""

# ---------------------------------------------------------------------------
# Provider: Gemini 2.0 Flash
# ---------------------------------------------------------------------------

def _match_with_gemini(prompt: str) -> list:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MatchResultsSchema,
            temperature=0.2,
        ),
    )
    data = json.loads(response.text)
    return data.get("matches", [])

# ---------------------------------------------------------------------------
# Provider: Groq — Llama 70B
# ---------------------------------------------------------------------------

def _match_with_groq(prompt: str) -> list:
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in your .env file.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4096,
    )

    raw_text = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps in ```json ... ```
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    data = json.loads(raw_text)
    return data.get("matches", [])

# ---------------------------------------------------------------------------
# Dispatcher — call this from main.py
# ---------------------------------------------------------------------------

PROVIDERS = {
    "gemini": _match_with_gemini,
    "groq":   _match_with_groq,
}

def match_hackathons_with_ai(provider: str = "gemini") -> bool:
    """
    Evaluates all hackathons in the DB against the user profile.
    provider: 'gemini' (default) | 'groq'
    Saves match_score, match_reason, and ai_provider back to MongoDB.
    """
    provider = provider.lower()
    if provider not in PROVIDERS:
        print(f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS.keys())}")
        return False

    profile = get_profile()
    if not profile:
        print("No user profile found. Save a profile first.")
        return False

    hackathons = get_hackathons(sort_by_score=False)
    if not hackathons:
        print("No hackathons in database. Run the scraper first.")
        return False

    print(f"[Matcher] Starting with provider='{provider}' for {len(hackathons)} hackathons...")

    prompt = _build_prompt(profile, hackathons)

    try:
        matches = PROVIDERS[provider](prompt)
    except Exception as e:
        print(f"[Matcher] Provider '{provider}' error: {e}")
        return False

    # Persist scores back to MongoDB
    db = get_db()
    updated_count = 0
    for item in matches:
        url = item.get("url")
        score = item.get("match_score")
        reason = item.get("match_reason")
        if not url:
            continue
        res = db.hackathons.update_one(
            {"url": url},
            {"$set": {
                "match_score": score,
                "match_reason": reason,
                "ai_provider": provider,
                "evaluated_at": datetime.datetime.now(),
            }}
        )
        updated_count += res.modified_count

    print(f"[Matcher] Done. Updated {updated_count} hackathons using '{provider}'.")
    return True


# ---------------------------------------------------------------------------
# Backwards-compat shim (so APScheduler's existing job still works)
# ---------------------------------------------------------------------------

def match_hackathons_with_gemini() -> bool:
    return match_hackathons_with_ai(provider="gemini")
