import os
from dotenv import load_dotenv
from googleapiclient.discovery import Resource

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from typing import List, Any, Optional
import json

from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from langchain.tools import StructuredTool
from langchain.agents import create_json_chat_agent, AgentExecutor
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import datetime
from zoneinfo import ZoneInfo
from .calendar_tools import get_availability, create_event, update_event, delete_event, list_events, search_events
from langchain_core.messages import BaseMessage
from langchain_core.agents import AgentAction, AgentFinish
import operator
from typing import TypedDict, Annotated, Union
from langchain_core.exceptions import OutputParserException

class AgentState(TypedDict):
    """
    Represents the state of our agent.

    Attributes:
        input: The input string from the user.
        chat_history: The list of previous messages in the conversation.
        agent_outcome: The outcome of the agent's decision (tool call or final answer).
        intermediate_steps: A list of (tool_call, tool_output) tuples.
        output: The final string response from the agent.
    """
    input: str
    chat_history: list[BaseMessage]
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]

# Define Pydantic Schemas for Tools
class CheckAvailabilityArgs(BaseModel):
    start: str
    end: str

class CreateEventArgs(BaseModel):
    summary: str
    start: str
    end: str
    attendees: list = None
    description: str = ""

class UpdateEventArgs(BaseModel):
    event_id: str
    summary: Optional[str] = Field(None, description="The new title for the event.")
    start: Optional[str] = Field(None, description="The new start time in ISO 8601 format.")
    end: Optional[str] = Field(None, description="The new end time in ISO 8601 format.")
    description: Optional[str] = Field(None, description="The new description for the event.")

class DeleteEventArgs(BaseModel):
    event_id: str = Field(..., description="The ID of the event to delete.")

class ListEventsArgs(BaseModel):
    start: str
    end: str

class SearchEventArgs(BaseModel):
    query: str = Field(..., description="The name of the event to search for.")



def create_agent_graph(service: Resource) -> StateGraph:
    """Creates the agent graph with the provided Google Calendar service."""

    # Define Tool Functions *inside* this scope to capture the 'service' object
    def check_availability_func(start: str, end: str) -> str:
        """Check if the calendar is free between start and end (ISO 8601)."""
        available = get_availability(service, start, end)
        return "Available" if available else "Busy"

    def create_event_func(summary: str, start: str, end: str, attendees: list = None, description: str = "") -> str:
        """Create a calendar event with the given summary (title), time, attendees, and optional description."""
        event = create_event(service, summary, start, end, attendees, description)
        return f"Event created: {event.get('htmlLink', '')}"

    def update_event_func(event_id: str, summary: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, description: Optional[str] = None) -> str:
        """Update an existing calendar event's summary (title), start/end time, or description."""
        new_values = {}
        if summary:
            new_values['summary'] = summary
        if start:
            new_values['start'] = {'dateTime': start, 'timeZone': 'UTC'}
        if end:
            new_values['end'] = {'dateTime': end, 'timeZone': 'UTC'}
        if description:
            new_values['description'] = description
        
        if not new_values:
            return "No update values provided."

        event = update_event(service, event_id, new_values)
        return f"Event updated: {event.get('htmlLink', '')}"

    def delete_event_func(event_id: str) -> str:
        """Delete a calendar event with the given event_id."""
        delete_event(service, event_id)
        return "Event deleted."

    def list_events_func(start: str, end: str) -> str:
        """List calendar events in the specified date range (ISO 8601).
        Returns a JSON string of the events list. Each event is a dictionary
        containing details like 'id', 'summary', 'start', and 'end'."""
        events = list_events(service, start, end)
        if not events:
            return "No events found."
        if isinstance(events, str): # Handle auth error message
            return events
        # Return the raw data as a JSON string so the agent can use it, especially the 'id'
        return json.dumps(events)

    def search_events_func(query: str) -> str:
        """Search for events by name to find their event_id."""
        return search_events(service, query)

    def get_current_time_func() -> str:
        """Returns the current date and time in Indian Standard Time (IST, UTC+05:30) in ISO 8601 format."""
        return datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

    # Create Structured Tools
    tools = [
        StructuredTool.from_function(func=check_availability_func, name="check_availability", description="Check if the calendar is free between start and end (ISO 8601).", args_schema=CheckAvailabilityArgs),
        StructuredTool.from_function(func=create_event_func, name="create_event", description="Create a calendar event with the given summary (title), time, attendees, and optional description.", args_schema=CreateEventArgs),
        StructuredTool.from_function(func=update_event_func, name="update_event", description="Update an existing calendar event's summary (title), start/end time, or description.", args_schema=UpdateEventArgs),
        StructuredTool.from_function(func=delete_event_func, name="delete_event", description="Delete a calendar event with the given event_id. Always use search_events to find the event_id first.", args_schema=DeleteEventArgs),
        StructuredTool.from_function(func=search_events_func, name="search_events", description="Search for events by name to find their event_id.", args_schema=SearchEventArgs),
        StructuredTool.from_function(func=list_events_func, name="list_events", description="List calendar events in the specified date range (ISO 8601).", args_schema=ListEventsArgs),
        StructuredTool.from_function(func=get_current_time_func, name="get_current_time", description="Returns the current date and time in Indian Standard Time (IST, UTC+05:30) in ISO 8601 format."),
    ]

    # Gemini LLM via LangChain
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

    # Agent initialization
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a powerful calendar assistant. You have access to a suite of tools to help users manage their Google Calendar.
IMPORTANT: Before you can delete or update an event, you MUST know its `event_id`. If the user asks to delete an event by name (e.g., "delete the team meeting"), you must first use the `search_events` tool to find the `event_id` for that event. Only after you have the `event_id` can you use the `delete_event` tool.
---
CRITICAL INSTRUCTIONS FOR DATE AND TIME:
1. The `get_current_time` tool is your ONLY source of truth for the current date and time.
2. You MUST ALWAYS use the year provided by this tool when interpreting relative dates like 'today', 'tomorrow', 'next Sunday', or 'next month'.
3. **Example Scenario**: If the user says "list events for next Sunday" and the `get_current_time` tool returns `2025-06-28T18:45:00`, you MUST calculate the date for the upcoming Sunday in the year 2025. Do NOT default to any other year.
4. **Strategy**: If a user's request involves a relative date, your first step should be to use the `get_current_time` tool to establish the correct date context before proceeding.
---
CRITICAL INSTRUCTIONS FOR MODIFYING EVENTS:
1. Before you can delete or update an event, you MUST know its `event_id`.
2. If the user asks to delete an event by name (e.g., "delete the team meeting"), you must first use the `search_events` tool to find the `event_id` for that event.
3. Only after you have the `event_id` can you use the `delete_event` or `update_event` tools.
---

Respond to the human as helpfully and accurately as possible. You have access to the following tools:

{tools}

When you receive the result from a tool (especially get_current_time), you MUST use that information to inform your next action. For example, if get_current_time returns a date in 2025, and the user asks to create an event for "next Sunday", you must create the event in 2025. Do not create events in the past unless the user explicitly asks for a past date.

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only the json blob as a response.

The `action_input` value for a tool should be a dictionary of parameters. do NOT stringify this dictionary.

When you have the final answer, use the "Final Answer" action. The value for "action_input" should be a single string that is your response to the user.

Here is an example of a valid tool-use response:
```json
{{
  "action": "create_event",
  "action_input": {{
    "summary": "Team Meeting",
    "start": "2025-07-01T10:00:00",
    "end": "2025-07-01T11:00:00"
  }}
}}
```

Here is an example of a valid final answer:
```json
{{
  "action": "Final Answer",
  "action_input": "I have scheduled the event 'Team Meeting' for you tomorrow at 10 AM."
}}
"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent_runnable = create_json_chat_agent(llm, tools, prompt_template)

    # Define Graph Nodes
    def run_agent(state: AgentState):
        """Invokes the agent to decide on an action."""
        try:
            agent_outcome = agent_runnable.invoke(state)
        except OutputParserException as e:
            raw_output = str(e).removeprefix("Could not parse LLM output: ")
            agent_outcome = AgentFinish(return_values={"output": raw_output}, log=raw_output)
        except Exception as e:
            error_message = f"An error occurred with the language model: {e}"
            agent_outcome = AgentFinish(return_values={"output": error_message}, log=error_message)
        return {"agent_outcome": agent_outcome}

    def execute_tools(state: AgentState):
        """Executes the tool specified by the agent."""
        agent_action = state["agent_outcome"]
        tool_to_use = {t.name: t for t in tools}[agent_action.tool]
        observation = tool_to_use.invoke(agent_action.tool_input)
        return {"intermediate_steps": [(agent_action, observation)]}

    def decide(state: AgentState):
        """Determines the next step based on the agent's outcome."""
        if isinstance(state["agent_outcome"], AgentFinish):
            return "end"
        else:
            return "continue"

    # Build the graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", run_agent)
    workflow.add_node("action", execute_tools)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        decide,
        {
            "continue": "action",
            "end": END,
        },
    )
    workflow.add_edge("action", "agent")

    return workflow
