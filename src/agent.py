import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# We instruct the ADK (Google Cloud Agent Builder SDK) to use the API key if present, 
# or default to Vertex AI if running in GCP Cloud Run.
if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams, StdioServerParameters

import mcp.client.session

def sanitize_schema(schema):
    if isinstance(schema, dict):
        cleaned = {}
        for k, v in schema.items():
            if k in ["$schema", "const", "propertyNames", "additionalProperties", "additional_properties"]:
                continue
            cleaned[k] = sanitize_schema(v)
        return cleaned
    elif isinstance(schema, list):
        return [sanitize_schema(i) for i in schema]
    return schema

# Monkey-patch the MCP client to sanitize schemas so ADK's pydantic parser doesn't crash
original_list_tools = mcp.client.session.ClientSession.list_tools

async def patched_list_tools(self, *args, **kwargs):
    result = await original_list_tools(self, *args, **kwargs)
    for t in result.tools:
        if t.inputSchema:
            t.inputSchema = sanitize_schema(t.inputSchema)
    return result

mcp.client.session.ClientSession.list_tools = patched_list_tools

class HackathonAgent:
    _instance = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = HackathonAgent()
            await cls._instance.connect()
        return cls._instance

    def __init__(self):
        self.uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        self.runner = None
        # We don't need to force Vertex off, we are actually using Vertex now
        # via the standard ADC environment config set in .env.

    async def connect(self):
        print("[Agent] Connecting to MongoDB MCP Server via ADK (Google Cloud Agent Builder)...")
        
        # Use npx.cmd on Windows to prevent asyncio subprocess from hanging/failing
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        server_params = StdioServerParameters(
            command=npx_cmd,
            args=["-y", "mongodb-mcp-server@latest"],
            env={**os.environ.copy(), "MDB_MCP_CONNECTION_STRING": self.uri}
        )
        
        print("[Agent] Initializing McpToolset...")
        mcp_toolset = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=server_params,
                timeout=30.0
            )
        )
        
        print("[Agent] Creating Agent instance...")
        agent = Agent(
            name="hackathon_agent",
            model="gemini-2.5-pro",
            instruction=(
                "You are a Hackathon Discovery AI Agent built with Google Agent Development Kit (ADK). "
                "You have access to a MongoDB database via tools. "
                "The database name is 'hackathon_agent', and the collections are 'hackathons' and 'tracked'. "
                "Use the MCP tools to execute queries, find hackathons, or update them. "
                "If the user asks to track a hackathon, you can update the document in 'hackathons' to tracked: true "
                "or just tell them to use the UI for it if it's easier. Better yet, try to use a tool to do it if available. "
                "Provide helpful, concise summaries of hackathons matching their criteria. "
                "Note: A 'Google' hackathon might not have 'Google' in the title. Look at the 'organization' field or tags to see if Google is the organizer."
            ),
            tools=[mcp_toolset]
        )
        
        print("[Agent] Creating InMemoryRunner...")
        self.runner = InMemoryRunner(agent=agent)
        print("[Agent] Ready.")

    async def send_message(self, user_message: str) -> str:
        if not self.runner:
            await self.connect()

        try:
            # Inject user profile into the context so the agent knows what to look for
            from src.database import get_profile
            profile = get_profile()
            context_msg = user_message
            if profile:
                profile_str = f"\n\n[System Note - User Profile Context: Tech Stack: {', '.join(profile.get('tech_stack', []))}, Interests: {', '.join(profile.get('interests', []))}]"
                context_msg += profile_str

            print(f"[Agent] Sending message to ADK Runner: {user_message}")
            events = await self.runner.run_debug(context_msg, quiet=True)
            
            final_output = ""
            for event in events:
                # ADK Agent text responses are typically inside event.message
                if getattr(event, "message", None) and hasattr(event.message, "parts"):
                    for part in event.message.parts:
                        if hasattr(part, "text") and part.text:
                            final_output += part.text
                
                # Sometime tools or direct node outputs go to event.output
                if getattr(event, "output", None):
                    if isinstance(event.output, str):
                        final_output += event.output
                    elif hasattr(event.output, "parts"):
                        for part in event.output.parts:
                            if hasattr(part, "text") and part.text:
                                final_output += part.text
            
            return final_output if final_output else "I successfully executed that using MCP, but didn't have a verbal response."
        except Exception as e:
            err_str = str(e)
            if "403" in err_str and "PERMISSION_DENIED" in err_str:
                return "Agent Error: GCP Permission Denied. Please ensure the Gemini API is enabled in your Google Cloud Project or you have provided a valid GEMINI_API_KEY (AIza...)."
            print(f"[Agent] Error during ADK execution: {e}")
            return f"An error occurred: {err_str}"

async def close_agent():
    agent = HackathonAgent._instance
    if agent and agent.runner:
        try:
            await agent.runner.close()
        except Exception as e:
            print(f"[Agent] Error closing runner: {e}")
