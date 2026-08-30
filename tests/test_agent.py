"""Testes de `itinerai_agent/agent.py` — apenas construção/compilação do grafo
(o fluxo ponta a ponta com `graph.invoke` é a T08)."""


def test_build_graph_returns_compiled_graph():
    from itinerai_agent.agent import build_graph

    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_agent_module_compiles_graph_on_import():
    from itinerai_agent import agent

    assert agent.graph is not None
    assert hasattr(agent.graph, "invoke")
