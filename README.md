# Hackathon Discovery & Matching Agent

A small FastAPI application that scrapes hackathons from Devpost, scores them against a saved developer profile using an LLM, and provides a browser dashboard to review and track opportunities. The app supports multiple AI providers (Gemini and Groq) and can send deadline reminders via Discord webhooks.

## Why This Exists

Finding suitable hackathons is time-consuming and fragmented. This agent automates the end-to-end workflow—scrape, score, track, and remind—so developers can focus on building instead of searching.

Created for the Google Cloud Agent Builder Hackathon. The app uses MongoDB MCP for persistence and supports Groq and Gemini for profile-driven matching.

## Key Features

- Scrape active hackathons from Devpost.
- Score hackathons against a developer profile using an AI provider (Gemini or Groq).
- Persist a single developer profile and scored hackathons in MongoDB.
- Track/untrack hackathons and receive optional deadline reminders via Discord.
- Serve a lightweight static dashboard from the same FastAPI server.

## Project Layout

- `src/main.py` - FastAPI application, routes, and background job orchestration.
- `src/matcher.py` - AI prompt construction and scoring logic for supported providers.
- `src/scraper.py` - Devpost scraping utilities.
- `src/database.py` - MongoDB helpers and persistence layer.
- `src/reminder.py` - Deadline checking and notification logic.
- `src/static/index.html` - Dashboard frontend.
- `src/static/app.js` - Frontend behavior and provider selection UI.
- `src/static/index.css` - Dashboard styles.

## Quick Start

1. Create and activate a virtual environment.

	 - Windows (PowerShell):

		 ```powershell
		 .venv\Scripts\Activate.ps1
		 ```

	 - Unix / macOS:

		 ```bash
		 python3 -m venv .venv
		 source .venv/bin/activate
		 ```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root. You can copy `.env.example` if provided and fill in your values.

## Environment Variables

Required:

- `MONGODB_URI` — MongoDB connection string (Atlas or local).
- `GEMINI_API_KEY` — API key for Google Gemini (used when `provider=gemini`).
- `GROQ_API_KEY` — API key for Groq (used when `provider=groq`).
- `OPENROUTER_API_KEY` — API key for OpenRouter (used when `provider=openrouter`). Sign up at [openrouter.ai](https://openrouter.ai).
- `CEREBRAS_API_KEY` — API key for Cerebras (used when `provider=cerebras`). Sign up at [cerebras.ai](https://cerebras.ai).
- `OLLAMA_ENDPOINT` — Ollama server endpoint (default: `http://localhost:11434/v1`). Change if Ollama runs on a different host or port.
- `OLLAMA_MODEL` — Model to use with Ollama (default: `gemma4:e4b`). Run `ollama list` to see installed models.

Optional:

- `DISCORD_WEBHOOK_URL` — Discord webhook URL for deadline reminders.

## Run the App

Start the API (development mode):

```bash
.venv\Scripts\python -m uvicorn src.main:app --reload
```

Open the dashboard at:

http://127.0.0.1:8000

## AI Providers

The app supports selecting an AI provider for scoring. The default background job uses the configured provider in `src/main.py` (Gemini is the default in the current code).

- Gemini: `gemini-2.0-flash`
- Groq: `llama-3.3-70b-versatile` (Llama 3.3, 70B)
- OpenRouter: `qwen/qwen3-next-80b-a3b-instruct:free` (Qwen3 Next 80B, free tier)
- Cerebras: `qwen-3-235b-a22b-instruct-2507` (Qwen 3 235B, free tier)
- Ollama: `gemma4:e4b` (configurable via `OLLAMA_MODEL` env variable)

You can trigger a scrape and match via the API and specify the provider:

```
POST /api/scrape?provider=gemini
POST /api/scrape?provider=groq
POST /api/scrape?provider=openrouter
POST /api/scrape?provider=cerebras
POST /api/scrape?provider=ollama
```

## API Endpoints

- `GET /api/providers` — List available providers and whether API keys are set.
- `POST /api/profile` — Save or update the developer profile used for matching.
- `GET /api/profile` — Retrieve the saved developer profile.
- `POST /api/scrape` — Scrape Devpost and score hackathons (accepts `provider` query parameter).
- `GET /api/hackathons` — Return the latest scored hackathons.
- `POST /api/track` — Track or untrack a hackathon by ID.
- `GET /api/tracked` — List tracked hackathons.
- `POST /api/remind` — Trigger deadline checks and send reminders if needed.

## Behavior Notes

- Background scraping is scheduled (current code uses a 12-hour interval).
- Deadline checks run on a separate schedule (current code uses a 24-hour interval).
- The matcher enforces short, UI-friendly analysis strings (approximately 150 characters) and normalizes scores with a round-half-up strategy to avoid even-number bias.

## Customization

To change which provider the background job uses, edit `run_background_scrape_and_match()` in `src/main.py` and call `match_hackathons_with_ai(provider="groq")` or `provider="gemini"` as desired.

## Troubleshooting

- If the dashboard fails to load, confirm your `.env` variables and that MongoDB is reachable via `MONGODB_URI`.
- Check the application logs printed by Uvicorn for stack traces and errors.

If you'd like, I can also run the server locally in this workspace to verify the README changes and confirm the app starts successfully.