import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import StreamingResponse
import json
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from backend.agent_graph import create_agent_graph
from backend.oauth import router as oauth_router, get_google_calendar_service
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.agents import AgentAction, AgentFinish
from googleapiclient.discovery import Resource

# Load env variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

app = FastAPI(title="Super Calendar Agent")

# Mount OAuth router
app.include_router(oauth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Super Calendar Agent backend is running."}

class ChatRequest(BaseModel):
    message: str
    history: list

async def get_agent_response_stream(req: ChatRequest, service: Resource):
    """Streams the agent's response, including tool usage, as Server-Sent Events."""
    
    # Create and compile the graph for each request, ensuring it has the correct service
    compiled_graph = create_agent_graph(service).compile()
    
    # Convert history to LangChain messages
    history_messages = []
    # Exclude the last assistant message which is a placeholder/old response
    for msg in req.history[:-1]: 
        if msg["role"] == "user":
            history_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history_messages.append(AIMessage(content=msg["content"]))

    # Define the initial state for the graph
    state = {
        "input": req.message,
        "chat_history": history_messages,
    }
    
    # Stream the graph execution
    async for chunk in compiled_graph.astream(state):
        if "agent" in chunk:
            agent_outcome = chunk["agent"].get("agent_outcome")
            if agent_outcome:
                if isinstance(agent_outcome, AgentAction):
                    # The agent is using a tool
                    tool_name = agent_outcome.tool
                    yield f"data: {json.dumps({'tool': tool_name, 'tool_input': agent_outcome.tool_input})}\n\n"
                elif isinstance(agent_outcome, AgentFinish):
                    # The agent has finished
                    final_response = agent_outcome.return_values["output"]
                    yield f"data: {json.dumps({'response': final_response})}\n\n"

@app.post("/chat")
async def chat_endpoint(req: ChatRequest, service: Resource = Depends(get_google_calendar_service)):
    return StreamingResponse(get_agent_response_stream(req, service), media_type="text/event-stream")
