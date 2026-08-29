from langgraph.graph import END, START, StateGraph

from itinerai_agent.utils.nodes import (
    call_llm,
    call_tools,
    dispatch_search,
    fetch_destination_page,
    fetch_tourism_page,
    merge_pages,
    persist_memory,
    route_after_llm,
    route_after_validation,
    validate_input,
)
from itinerai_agent.utils.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("validate_input", validate_input)
    builder.add_node("persist_memory", persist_memory)
    builder.add_node("call_llm", call_llm)
    builder.add_node("call_tools", call_tools)
    builder.add_node("dispatch_search", dispatch_search)
    builder.add_node("fetch_tourism_page", fetch_tourism_page)
    builder.add_node("fetch_destination_page", fetch_destination_page)
    builder.add_node("merge_pages", merge_pages)

    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input", route_after_validation, {"persist_memory": "persist_memory", END: END}
    )
    builder.add_edge("persist_memory", "call_llm")
    builder.add_conditional_edges(
        "call_llm",
        route_after_llm,
        {"dispatch_search": "dispatch_search", "call_tools": "call_tools", END: END},
    )
    # Fan-out: dispatch_search dispara as duas buscas de página em paralelo.
    builder.add_edge("dispatch_search", "fetch_tourism_page")
    builder.add_edge("dispatch_search", "fetch_destination_page")
    # Fan-in: merge_pages roda uma única vez, após os dois ramos (barreira
    # nomeada — segura porque os dois ramos são incondicionais).
    builder.add_edge(["fetch_tourism_page", "fetch_destination_page"], "merge_pages")
    builder.add_edge("merge_pages", "call_llm")
    builder.add_edge("call_tools", "call_llm")
    return builder.compile()


graph = build_graph()
