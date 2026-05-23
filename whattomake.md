# Project: Antigravity Discovery Agent (Powered by ADK + MongoDB MCP)

## The Real-World Challenge
Developers waste time sifting through hundreds of hackathons on Devpost trying to find the perfect match for their tech stack, location, and schedule. Standard filters and basic search don't capture complex requirements like "Find me an AI hackathon in the next 3 weeks that isn't invite-only and has a prize pool over $5000."

## The Goal
We upgraded the existing Hackathon Discovery tool into a **functional, conversational Agent**. It is no longer just a static dashboard; it is an AI assistant that autonomously queries, filters, and manages your hackathon pipeline using the **MongoDB MCP Server** and **Google Cloud Agent Builder (ADK)**.

## Hackathon Track
**Partner Track:** MongoDB

## How We Fulfilled the Requirements

1. **Google Cloud Agent Builder**: 
   We built the core intelligence using Google's official **Agent Development Kit (ADK)** (`google-adk`). By using the ADK `Agent` and `InMemoryRunner`, we tapped into the Agent Builder ecosystem, ensuring the agent is production-ready and easy to deploy to Vertex AI or Cloud Run as a managed agent.

2. **The Partner Superpower (MongoDB MCP)**: 
   Instead of hardcoded API endpoints for filtering, the Agent connects to the official **MongoDB MCP Server** (`@modelcontextprotocol/server-mongodb`). 
   - We used the ADK's native `McpToolset` to mount the MongoDB server.
   - When a user asks a complex question ("Show me hackathons ending in May with AI tags"), the Agent automatically formulates a MongoDB query.
   - It executes this query against our MongoDB Atlas database using the MCP server, bypassing the need for manual API coding.

3. **Move Beyond Chat (Multi-Step Mission)**:
   - **Data Ingestion**: A background job scrapes Devpost and populates MongoDB with hackathons.
   - **Reasoning**: The user chats with the ADK Agent in the dashboard.
   - **Action**: The user can say "Track the second hackathon you mentioned." The Agent will formulate an update query and use the MCP server to mutate the database, moving that hackathon to the user's "Tracked" list. It manages your pipeline for you.

## Implementation Details
- **Backend**: FastAPI (`src/main.py`)
- **Agent Orchestration**: Google ADK (`src/agent.py`)
- **MCP Server**: `mongodb-mcp-server` triggered via `npx` stdio transport.
- **Frontend**: Custom dashboard with an embedded "Agent Chat" tab to talk directly to the database.

## Notes for Judges
If you encounter a `403 PERMISSION_DENIED` error when chatting with the Agent, ensure your Google Cloud Project has the Gemini API (`generativelanguage.googleapis.com`) enabled, or that you provide a valid `GEMINI_API_KEY` (starting with `AIza...`) in the `.env` file so the ADK can route to the public API instead of Vertex AI.
