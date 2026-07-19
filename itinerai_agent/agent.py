from langgraph.graph import END, START, StateGraph

from itinerai_agent.utils.nodes import call_llm, call_tools, should_call_tools
from itinerai_agent.utils.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("call_llm", call_llm)
    builder.add_node("call_tools", call_tools)
    builder.add_edge(START, "call_llm")
    builder.add_conditional_edges("call_llm", should_call_tools, {"call_tools": "call_tools", END: END})
    builder.add_edge("call_tools", "call_llm")
    return builder.compile()


graph = build_graph()
