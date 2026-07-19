from langchain_core.messages import SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import END

from itinerai_agent.utils.prompts import AGENT_SYSTEM_PROMPT
from itinerai_agent.utils.state import AgentState
from itinerai_agent.utils.tools import search_events_and_festivals, search_tourist_attractions

_TOOLS = [search_tourist_attractions, search_events_and_festivals]
_TOOLS_BY_NAME = {tool.__name__: tool for tool in _TOOLS}

_llm = ChatGroq(model="llama-3.1-8b-instant")
_llm_with_tools = _llm.bind_tools(_TOOLS)


def call_llm(state: AgentState) -> dict:
    response = _llm_with_tools.invoke([SystemMessage(content=AGENT_SYSTEM_PROMPT), *state.messages])
    return {"messages": [response]}


def should_call_tools(state: AgentState) -> str:
    last_message = state.messages[-1]
    if getattr(last_message, "tool_calls", None):
        return "call_tools"
    return END


def call_tools(state: AgentState) -> dict:
    last_message = state.messages[-1]

    tool_messages = []
    update: dict = {}
    for call in last_message.tool_calls:
        tool_fn = _TOOLS_BY_NAME[call["name"]]
        result = tool_fn(**call["args"])
        tool_messages.append(ToolMessage(content=result.model_dump_json(), tool_call_id=call["id"]))

        if call["name"] == "search_tourist_attractions":
            update["destination"] = result.destination
            update["tourist_attractions"] = result.attractions
        elif call["name"] == "search_events_and_festivals":
            update["destination"] = result.destination
            update["traditional_events"] = result.events

    update["messages"] = tool_messages
    return update
