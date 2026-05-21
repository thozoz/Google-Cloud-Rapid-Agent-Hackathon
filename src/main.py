import os
import contextlib
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn
from src.database import init_db, save_profile, get_profile, get_hackathons, track_hackathon, get_tracked_hackathons
from src.scraper import scrape_devpost
from src.matcher import match_hackathons_with_ai, match_hackathons_with_gemini
from src.reminder import check_deadlines_and_notify

# Scheduler initialization
scheduler = AsyncIOScheduler()

def run_background_scrape_and_match():
    """Background task to run Devpost scraper and score them using the default provider."""
    print("[Background Job] Starting automatic scraping and matching...")
    try:
        scraped = scrape_devpost(max_pages=3)
        if scraped:
            match_hackathons_with_gemini()
    except Exception as e:
        print(f"Error in background scrape and match job: {e}")

def run_background_deadline_reminder():
    """Background task to scan tracked hackathons and send daily alerts."""
    print("[Background Job] Starting automatic deadline reminder check...")
    try:
        check_deadlines_and_notify()
    except Exception as e:
        print(f"Error in background deadline reminder job: {e}")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    print(">> Starting Hackathon Discovery & Tracking Agent...")
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Database initialization failed. Check your MONGODB_URI: {e}")
        
    # Start APScheduler background jobs
    scheduler.add_job(run_background_scrape_and_match, 'interval', hours=12, id="scrape_match_job", replace_existing=True)
    scheduler.add_job(run_background_deadline_reminder, 'interval', hours=24, id="deadline_alert_job", replace_existing=True)
    scheduler.start()
    print("APScheduler started in background. Scraper job: every 12h. Deadline checks: every 24h.")
    
    yield
    
    # Shutdown Events
    print("Shutting down background scheduler...")
    scheduler.shutdown()

# Initialize FastAPI App
app = FastAPI(
    title="Hackathon Discovery & Tracking Agent API",
    description="Autonomous Agent for scraping, scoring, and tracking Devpost hackathons.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class ProfileModel(BaseModel):
    tech_stack: List[str]
    interests: List[str]
    experience_level: str
    weekly_availability: str

class TrackRequest(BaseModel):
    url: str
    track: bool

# API Routes

@app.post("/api/profile")
async def update_user_profile(profile: ProfileModel):
    """Saves or updates the user profile in MongoDB."""
    try:
        saved_data = save_profile(profile.model_dump())
        return {"status": "success", "message": "Profile updated successfully.", "profile": saved_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/profile")
async def retrieve_user_profile():
    """Retrieves the user profile from MongoDB."""
    try:
        profile = get_profile()
        if not profile:
            return {"status": "empty", "message": "No profile exists yet."}
        return {"status": "success", "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/providers")
async def list_providers():
    """Returns available AI providers and which keys are configured."""
    import os
    return {
        "providers": [
            {
                "id": "gemini",
                "label": "Gemini 2.0 Flash",
                "model": "gemini-2.0-flash",
                "configured": bool(os.getenv("GEMINI_API_KEY")),
            },
            {
                "id": "groq",
                "label": "Groq — Llama 70B",
                "model": "llama-3.3-70b-versatile",
                "configured": bool(os.getenv("GROQ_API_KEY")),
            },
            {
                "id": "openrouter",
                "label": "OpenRouter — Qwen3 Next 80B (Free)",
                "model": "qwen/qwen3-next-80b-a3b-instruct:free",
                "configured": bool(os.getenv("OPENROUTER_API_KEY")),
            },
            {
                "id": "cerebras",
                "label": "Cerebras — Qwen 3 235B (Free)",
                "model": "qwen-3-235b-a22b-instruct-2507",
                "configured": bool(os.getenv("CEREBRAS_API_KEY")),
            },
            {
                "id": "ollama",
                "label": "Ollama — Local",
                "model": os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
                "configured": True,
            },
        ]
    }

@app.post("/api/scrape")
async def trigger_manual_scrape(
    provider: str = Query(default="gemini", description="AI provider to use: 'gemini', 'groq', 'openrouter', 'cerebras', or 'ollama'")
):
    """Manually triggers scraping and AI matching. Use ?provider=groq to switch."""
    print(f"Manual scrape and match requested. Provider: {provider}")
    try:
        scraped = scrape_devpost(max_pages=3)
        if not scraped:
            return {"status": "success", "message": "Scrape completed. No new hackathons found.", "provider": provider}

        matched_success = match_hackathons_with_ai(provider=provider)
        return {
            "status": "success",
            "message": f"Successfully scraped {len(scraped)} hackathons.",
            "provider": provider,
            "ai_evaluated": matched_success,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")

@app.get("/api/hackathons")
async def list_hackathons():
    """Lists all hackathons from MongoDB, sorted by their match score."""
    try:
        hackathons = get_hackathons(sort_by_score=True)
        return {"status": "success", "count": len(hackathons), "hackathons": hackathons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/track")
async def toggle_track_hackathon(req: TrackRequest):
    """Adds or removes a hackathon from the tracked collection."""
    try:
        success = track_hackathon(req.url, req.track)
        status_msg = "tracked" if req.track else "untracked"
        return {"status": "success", "message": f"Hackathon successfully {status_msg}."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/tracked")
async def list_tracked():
    """Lists all tracked hackathons."""
    try:
        tracked = get_tracked_hackathons()
        return {"status": "success", "count": len(tracked), "tracked": tracked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/remind")
async def trigger_manual_reminders():
    """Manually scans tracked hackathons and fires deadline warnings."""
    print("Manual deadline check requested.")
    try:
        reminded = check_deadlines_and_notify()
        return {
            "status": "success", 
            "message": f"Scanned tracked hackathons. Sent {len(reminded)} reminders.", 
            "reminded": reminded
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reminder error: {str(e)}")

# Mount static files UI at root
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    print(f"Warning: Static frontend directory not found at: {static_dir}. Frontend UI will not be served.")

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
