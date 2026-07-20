from langgraph.graph import END, START, StateGraph

from itinerai_agent.utils.nodes import (
    call_llm,
    call_tools,
    route_after_validation,
    should_call_tools,
    validate_input,
)
from itinerai_agent.utils.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("validate_input", validate_input)
    builder.add_node("call_llm", call_llm)
    builder.add_node("call_tools", call_tools)
    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input", route_after_validation, {"call_llm": "call_llm", END: END}
    )
    builder.add_conditional_edges("call_llm", should_call_tools, {"call_tools": "call_tools", END: END})
    builder.add_edge("call_tools", "call_llm")
    return builder.compile()


graph = build_graph()
