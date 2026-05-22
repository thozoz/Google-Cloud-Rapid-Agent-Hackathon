# Hackathon Discovery & Matching Agent

A small FastAPI application that scrapes hackathons from Devpost, scores them against a saved developer profile using an LLM, and provides a browser dashboard to review and track opportunities. Supports multiple AI providers (Gemini, Groq, OpenRouter, Cerebras, Ollama) and can send deadline reminders via Discord webhooks.

## Why This Exists

Finding suitable hackathons is time-consuming and fragmented. This agent automates the end-to-end workflow—scrape, score, track, and remind—so developers can focus on building instead of searching.

Created for the Google Cloud Agent Builder Hackathon. Uses MongoDB for persistence and supports multiple AI providers for profile-driven matching.

## Key Features

- Scrape active and upcoming hackathons from Devpost.
- Score hackathons against your profile using your choice of AI provider.
- Persist a developer profile and scored hackathons in MongoDB.
- Track/untrack hackathons and receive optional deadline reminders via Discord.
- Lightweight dashboard with minimalist dark theme and profile-based recommendations.

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

The app supports selecting which AI provider to use for scoring. Trigger via `?provider=<name>`:

- **Gemini**: `gemini-2.0-flash`
- **Groq**: `llama-3.3-70b-versatile` (Llama 3.3, 70B)
- **OpenRouter**: `qwen/qwen3-next-80b-a3b-instruct:free` (free tier)
- **Cerebras**: `qwen-3-235b-a22b-instruct-2507` (free tier)
- **Ollama**: `gemma4:e4b` (local, configurable via `OLLAMA_MODEL`)

Trigger scraping with a specific provider:

```
POST /api/scrape?provider=gemini
POST /api/scrape?provider=groq
POST /api/scrape?provider=openrouter
POST /api/scrape?provider=cerebras
POST /api/scrape?provider=ollama
```

Other endpoints:

```
GET /api/providers           # List available providers
GET /api/profile             # Get saved profile
POST /api/profile            # Save profile
GET /api/hackathons          # List scored hackathons
POST /api/track              # Track/untrack a hackathon
GET /api/tracked             # List tracked projects
POST /api/remind             # Trigger deadline reminders
```

## Background Jobs

- **Scraping**: Runs every 12 hours automatically.
- **Deadline Reminders**: Runs every 24 hours automatically.
- **Analysis**: Scores capped 1-10, reasons truncated to ~150 characters for readability.

## Troubleshooting

- **Dashboard won't load**: Verify `.env` variables and that MongoDB is reachable.
- **Scraping fails**: Check API key configuration and network connectivity.
- **No matches returned**: Verify that Devpost has active/upcoming hackathons available.