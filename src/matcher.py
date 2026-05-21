import os
import json
import re
import datetime
import math
from pydantic import BaseModel, Field
from typing import List
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
- Provide a specific one-line reason (max 150 chars). Mention exactly which parts of the developer's tech stack or interests matched (or failed to match) the hackathon's tags and theme.
- You MUST respond ONLY with valid JSON matching this exact schema:
  {{"matches": [{{"url": "...", "match_score": <int>, "match_reason": "..."}}]}}
- No extra text, no markdown fences, just raw JSON.
"""

def _build_single_prompt(profile: dict, h: dict) -> str:
    developer_profile_str = f"""
=== DEVELOPER PROFILE ===
- Tech Stack: {', '.join(profile.get('tech_stack', []))}
- Interests:  {', '.join(profile.get('interests', []))}
- Experience: {profile.get('experience_level', 'Intermediate')}
- Availability: {profile.get('weekly_availability', '10 hours')} per week
"""
    hackathon_data = {
        "title": h.get("title"),
        "url": h.get("url"),
        "tags": h.get("tags", []),
        "prize_pool": h.get("prize_pool", "N/A"),
        "eligibility": h.get("eligibility", "Open"),
    }

    return f"""You are an expert AI agent specializing in hackathon matching.
Evaluate the following hackathon against the developer profile and score it 1-10.

{developer_profile_str}

=== HACKATHON TO EVALUATE ===
{json.dumps(hackathon_data, indent=2)}

=== INSTRUCTIONS ===
- Score 10 = perfect stack/interest/experience alignment.
- Score 1  = no alignment at all.
- Use the FULL spectrum of numbers between 1 and 10 (e.g., 1, 3, 5, 7, 9 are perfectly fine). Do NOT restrict yourself to even numbers. Be highly granular.
- Provide a specific one-line reason (max 150 chars). Mention exactly which parts of the developer's tech stack or interests matched (or failed to match) the hackathon's tags and theme. Be very specific about technologies.
- You MUST respond ONLY with valid JSON matching this exact schema:
  {{"match_score": <int>, "match_reason": "..."}}
- No extra text, no markdown fences, just raw JSON.
"""

# ---------------------------------------------------------------------------
# Provider: Gemini 2.0 Flash
# ---------------------------------------------------------------------------

def _match_with_gemini(profile: dict, hackathons: list) -> list:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")

    prompt = _build_prompt(profile, hackathons)

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
# Generic OpenAI-compatible API handler
# ---------------------------------------------------------------------------

def _evaluate_with_openai_compat(
    profile: dict,
    hackathons: list,
    provider_name: str,
    api_key: str,
    api_endpoint: str,
    model: str,
    extra_headers: dict = None
) -> list:
    """Generic evaluator for OpenAI-compatible APIs with retry logic for rate limits."""
    import httpx
    import time
    
    results = []
    print(f"[{provider_name}] Starting evaluation for {len(hackathons)} hackathons...")
    
    # Only add Authorization header if api_key is provided (some providers like Ollama don't need it)
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)
    
    for h in hackathons:
        try:
            prompt = _build_single_prompt(profile, h)
            
            # Add delay for local providers (Ollama) to prevent VRAM thrashing
            if provider_name == "Ollama":
                time.sleep(0.5)  # 500ms delay between requests
            
            # Retry logic for rate limiting (429)
            max_retries = 3
            retry_count = 0
            response = None
            
            while retry_count < max_retries:
                try:
                    request_body = {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                        "max_tokens": 1024,
                    }
                    

                    response = httpx.post(
                        f"{api_endpoint}/chat/completions",
                        headers=headers,
                        json=request_body,
                        timeout=60  # Extended timeout for slower local inference
                    )
                    
                    # Handle 429 (Too Many Requests) with exponential backoff
                    if response.status_code == 429:
                        wait_time = 2 ** retry_count  # 1s, 2s, 4s
                        print(f"  [{provider_name}] Rate limited. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    
                    break  # Success or non-429 error
                except httpx.ReadTimeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        print(f"  [{provider_name}] Timeout. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        raise
            
            if response is None:
                print(f"  [{provider_name}] Failed to get response after retries")
                continue
            
            if response.status_code != 200:
                print(f"  [{provider_name}] Status {response.status_code}")
                continue
            
            data = response.json()
            raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            # Clean JSON response
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
            
            data = json.loads(raw_text)
            score_raw = data.get("match_score")
            reason = data.get("match_reason")
            
            # Normalize score
            score = None
            try:
                if isinstance(score_raw, (int, float)):
                    score = int(math.floor(float(score_raw) + 0.5))
                elif isinstance(score_raw, str):
                    m = re.search(r"(\d+(?:\.\d+)?)", score_raw)
                    if m:
                        score = int(math.floor(float(m.group(1)) + 0.5))
            except Exception as _e:
                print(f"  [{provider_name}] Parse error: {_e}")
            
            # Clamp & truncate
            if isinstance(score, int):
                score = max(1, min(10, score))
            if reason:
                reason = reason[:150]
            
            if score is not None and reason:
                results.append({"url": h.get("url"), "match_score": score, "match_reason": reason})
                print(f"  [{provider_name}] {h.get('title')[:40]} -> {score}")
        except Exception as e:
            print(f"  [{provider_name}] Error: {e}")
    
    return results

# ---------------------------------------------------------------------------
# Provider: Groq — Llama 3.3 70B
# ---------------------------------------------------------------------------

def _match_with_groq(profile: dict, hackathons: list) -> list:
    api_key = os.getenv("GROQ_API_KEY")
    return _evaluate_with_openai_compat(
        profile, hackathons,
        provider_name="Groq",
        api_key=api_key,
        api_endpoint="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile"
    )

# ---------------------------------------------------------------------------
# Provider: OpenRouter — Qwen3 Next 80B (Free)
# ---------------------------------------------------------------------------

def _match_with_openrouter(profile: dict, hackathons: list) -> list:
    api_key = os.getenv("OPENROUTER_API_KEY")
    return _evaluate_with_openai_compat(
        profile, hackathons,
        provider_name="OpenRouter",
        api_key=api_key,
        api_endpoint="https://openrouter.ai/api/v1",
        model="qwen/qwen3-next-80b-a3b-instruct:free",
        extra_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "Hackathon Matcher"}
    )

# ---------------------------------------------------------------------------
# Provider: Cerebras — Llama 3.1 8B
# ---------------------------------------------------------------------------

def _match_with_cerebras(profile: dict, hackathons: list) -> list:
    api_key = os.getenv("CEREBRAS_API_KEY")
    return _evaluate_with_openai_compat(
        profile, hackathons,
        provider_name="Cerebras",
        api_key=api_key,
        api_endpoint="https://api.cerebras.ai/v1",
        model="qwen-3-235b-a22b-instruct-2507"
    )

# ---------------------------------------------------------------------------
# Provider: Ollama — Local (Gemma 4)
# ---------------------------------------------------------------------------

def _match_with_ollama(profile: dict, hackathons: list) -> list:
    # Ollama runs locally, no API key needed
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
    return _evaluate_with_openai_compat(
        profile, hackathons,
        provider_name="Ollama",
        api_key=None,
        api_endpoint=ollama_endpoint,
        model=ollama_model
    )

# ---------------------------------------------------------------------------
# Dispatcher — call this from main.py
# ---------------------------------------------------------------------------

PROVIDERS = {
    "gemini": _match_with_gemini,
    "groq": _match_with_groq,
    "openrouter": _match_with_openrouter,
    "cerebras": _match_with_cerebras,
    "ollama": _match_with_ollama,
}

def match_hackathons_with_ai(provider: str = "gemini") -> bool:
    """
    Evaluates all hackathons in the DB against the user profile.
    provider: 'gemini' (default) | 'groq' | 'openrouter' | 'cerebras' | 'ollama'
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

    try:
        matches = PROVIDERS[provider](profile, hackathons)
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
