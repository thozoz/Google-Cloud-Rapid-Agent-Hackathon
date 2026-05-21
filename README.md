# Hackathon Discovery & Tracking Agent

FastAPI app that scrapes Devpost hackathons, scores them against a saved developer profile, and tracks deadlines. The dashboard ships with a static frontend and supports two AI providers for matching: Gemini and Groq.

## Features

- Scrape hackathons from Devpost.
- Score hackathons with Gemini or Groq.
- Save a single developer profile in MongoDB.
- Track and untrack hackathons.
- Send deadline reminders through Discord webhooks when configured.
- Serve a browser dashboard from the same FastAPI app.

## Project Structure

- [src/main.py](src/main.py) - FastAPI routes, provider list, and background jobs.
- [src/matcher.py](src/matcher.py) - AI scoring logic for Gemini and Groq.
- [src/scraper.py](src/scraper.py) - Devpost scraping.
- [src/database.py](src/database.py) - MongoDB persistence helpers.
- [src/reminder.py](src/reminder.py) - Deadline reminder notifications.
- [src/static/index.html](src/static/index.html) - Dashboard UI.
- [src/static/app.js](src/static/app.js) - Frontend behavior.
- [src/static/index.css](src/static/index.css) - Dashboard styling.

## Setup

1. Create and activate your virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root.

You can copy [.env.example](.env.example) and fill in your values.

## Environment Variables

Required:

- `MONGODB_URI` - MongoDB Atlas connection string.
- `GEMINI_API_KEY` - Gemini API key for AI matching.
- `GROQ_API_KEY` - Groq API key for testing with Llama 70B.

Optional:

- `DISCORD_WEBHOOK_URL` - Discord webhook used for deadline alerts.

## Run

Start the API and dashboard with:

```bash
.\.venv\Scripts\python -m uvicorn src.main:app --reload
```

Then open the app at:

```text
http://127.0.0.1:8000
```

## AI Provider Selection

The frontend lets you choose which provider to use before running scrape-and-match.

- Gemini uses `gemini-2.0-flash`.
- Groq uses `llama3-70b-8192`.

You can also call the scrape endpoint directly with a provider query parameter:

```text
POST /api/scrape?provider=gemini
POST /api/scrape?provider=groq
```

## API Endpoints

- `GET /api/providers` - Lists available providers and whether their keys are configured.
- `POST /api/profile` - Saves the developer profile.
- `GET /api/profile` - Loads the developer profile.
- `POST /api/scrape` - Scrapes Devpost and scores hackathons.
- `GET /api/hackathons` - Returns scored hackathons.
- `POST /api/track` - Tracks or untracks a hackathon.
- `GET /api/tracked` - Returns tracked hackathons.
- `POST /api/remind` - Manually checks tracked hackathons for deadline warnings.

## Notes

- Background scraping runs every 12 hours.
- Deadline checks run every 24 hours.
- Do not commit your real `.env` file.
 
Note: Background scraping currently uses Gemini by default (see `src/main.py`).
If you want the background job to use Groq instead, update `run_background_scrape_and_match()` in `src/main.py` to call `match_hackathons_with_ai(provider="groq")`.