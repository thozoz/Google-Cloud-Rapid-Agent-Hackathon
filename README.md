> ⚠️ **Hackathon submission (June 2026). Archived and not maintained.**

# Hackathon Discovery & Matching Agent (Powered by ADK & MongoDB MCP)

A FastAPI application that scrapes hackathons from Devpost, scores them against a saved developer profile, and acts as an **autonomous agent** using **Google Cloud Agent Builder (ADK)** and the **MongoDB MCP Server** to query, filter, and track hackathons via natural language.

Built for the **Google Cloud Agent Builder Hackathon** (MongoDB Track).

## Key Features

- **Google ADK Orchestration**: Uses Google's official `google-adk` framework to create a robust, production-ready AI Agent running `gemini-3.5-flash`.
- **MongoDB MCP Server Integration**: Instead of hardcoding search filters, the Agent connects to the database via the official MongoDB MCP server (`@modelcontextprotocol/server-mongodb`). This gives the Agent the "superpower" to independently execute raw NoSQL queries and explore the database structure dynamically.
- **Move Beyond Chat**: The Agent actively manages your pipeline. Tell it to *"Track the AI hackathon ending next week,"* and it will formulate the correct `mongodb_update` request via MCP to update the database for you.
- **Devpost Scraper**: A background APScheduler job automatically scrapes active and upcoming hackathons into MongoDB Atlas.
- **Lightweight Dashboard**: A sleek, dark-themed UI that displays AI-scored recommendations, tracked projects, and features an embedded **Agent Chat**.

## Architecture & Project Layout

- `src/main.py` - FastAPI application, REST endpoints, and background job orchestration.
- `src/agent.py` - Google ADK `InMemoryRunner` orchestration. Mounts the MongoDB MCP tools securely and exposes the conversational loop.
- `src/matcher.py` - Background AI scoring logic to pre-evaluate new hackathons against the user's profile.
- `src/scraper.py` - Devpost HTML/JSON scraping utilities.
- `src/database.py` - Internal MongoDB helpers.
- `src/static/` - Frontend dashboard and real-time Agent Chat UI (HTML/JS/Tailwind CSS).
- `whattomake.md` & `ADK_TROUBLESHOOTING_LOG.md` - Documentation of the hackathon build process and ADK integration challenges.

## Quick Start

1. **Clone and setup a virtual environment:**

	 - Windows (PowerShell):
		 ```powershell
		 python -m venv .venv
		 .venv\Scripts\Activate.ps1
		 ```
	 - Unix / macOS:
		 ```bash
		 python3 -m venv .venv
		 source .venv/bin/activate
		 ```

2. **Install dependencies:**
	```bash
	pip install -r requirements.txt
	```
	*(This will install FastAPI, google-adk, mcp, pymongo, etc.)*

3. **Install the MongoDB MCP Server:**
	```bash
	npm install -g @modelcontextprotocol/server-mongodb
	```

4. **Environment Variables:**
	Create a `.env` file in the project root:
	```env
	# MongoDB Atlas connection string
	MONGODB_URI=mongodb+srv://<user>:<password>@cluster0...

	# The Agent uses Vertex AI via Application Default Credentials
	GOOGLE_GENAI_USE_VERTEXAI=TRUE
	GOOGLE_CLOUD_PROJECT=your-gcp-project-id
	GOOGLE_CLOUD_LOCATION=us-central1
	```

5. **Authenticate with Google Cloud:**
	Since we are using Vertex AI, ensure your machine is authenticated:
	```bash
	gcloud auth application-default login
	```

## Run the App

Start the API:
```bash
python -m uvicorn src.main:app --reload
```

Open the dashboard at:
http://127.0.0.1:8000

Navigate to the **Agent Chat** tab to start talking to your database! Try asking:
* *"Find me AI hackathons ending in June"*
* *"What collections are in this database?"*
* *"Track the last hackathon you mentioned."*

## How the Agent Works (Google Cloud Agent Builder & MCP)

The app leverages **Google's Agent Development Kit (ADK)** to scaffold a `gemini-3.5-flash` agent. 
We use the ADK's `McpToolset` to mount the Node.js `mongodb-mcp-server` via standard `stdio` transport.

When you ask the Agent a question in the UI:
1. The ADK `InMemoryRunner` parses your intent.
2. The Agent invokes a tool call (e.g., `mongodb_find` or `mongodb_update`).
3. The MCP server executes the raw NoSQL command securely against your MongoDB Atlas cluster.
4. The Agent parses the MCP response and summarizes the results for you in a human-readable format.

*(Note: We implemented a schema sanitizer within the MCP client interceptor to ensure full compatibility between the complex JSON Schemas returned by the MongoDB MCP server and the strict Pydantic validation used by the `google-adk`).*