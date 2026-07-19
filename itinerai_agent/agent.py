from langgraph.graph import END, START, StateGraph

from itinerai_agent.utils.nodes import call_llm
from itinerai_agent.utils.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("call_llm", call_llm)
    builder.add_edge(START, "call_llm")
    builder.add_edge("call_llm", END)
    return builder.compile()


graph = build_graph()
