"""Testes dos helpers puros e dos decorators de instrumentação de
`itinerai_agent/utils/nodes.py`."""

import types

import pytest
from langchain_core.messages import AIMessage

from itinerai_agent.utils import audit
from itinerai_agent.utils import nodes as N

_UNRECOVERABLE_MSG = (
    "Desculpe, me atrapalhei ao preparar seu pedido. Pode reformular ou tentar "
    "novamente em instantes?"
)


# --- _summarize_args ------------------------------------------------

def test_summarize_short_str():
    assert N._summarize_args({"destination": "Paris"}) == {"destination": "Paris"}


def test_summarize_long_str_truncated():
    out = N._summarize_args({"d": "x" * 200})
    assert out == {"d": "x" * 120 + "…"}


def test_summarize_scalars_passthrough():
    raw = {"n": 3, "f": 1.5, "b": True, "z": None}
    assert N._summarize_args(raw) == raw


def test_summarize_sized_collection():
    assert N._summarize_args({"items": [1, 2, 3]}) == {"items": "<list len=3>"}


def test_summarize_opaque_object():
    assert N._summarize_args({"o": object()}) == {"o": "<object>"}


# --- _parse_leaked_tool_calls -------------------------------------

def test_parse_single_valid():
    content = '<function=build_itinerary>{"destination": "P", "num_days": 2}</function>'
    calls = N._parse_leaked_tool_calls(content)
    assert len(calls) == 1
    assert calls[0]["name"] == "build_itinerary"
    assert calls[0]["args"] == {"destination": "P", "num_days": 2}
    assert calls[0]["id"].startswith("leaked_")
    assert calls[0]["type"] == "tool_call"


def test_parse_unknown_name_skipped():
    assert N._parse_leaked_tool_calls("<function=foo>{}</function>") == []


def test_parse_malformed_json_skipped():
    assert N._parse_leaked_tool_calls("<function=build_itinerary>{nope}</function>") == []


def test_parse_two_calls():
    content = (
        '<function=search_tourist_attractions>{"destination": "P"}</function>'
        '<function=build_itinerary>{"destination": "P", "num_days": 2}</function>'
    )
    calls = N._parse_leaked_tool_calls(content)
    assert [c["name"] for c in calls] == [
        "search_tourist_attractions",
        "build_itinerary",
    ]


# --- _drop_premature_build_itinerary ---------------------------

def test_drop_when_search_present():
    calls = [
        {"name": "search_tourist_attractions", "args": {}, "id": "a", "type": "tool_call"},
        {"name": "build_itinerary", "args": {}, "id": "b", "type": "tool_call"},
    ]
    kept = N._drop_premature_build_itinerary(calls)
    assert [c["name"] for c in kept] == ["search_tourist_attractions"]


def test_keep_when_no_search():
    calls = [{"name": "build_itinerary", "args": {}, "id": "b", "type": "tool_call"}]
    assert N._drop_premature_build_itinerary(calls) == calls


# --- _repair_leaked_response ----------------------------------

def test_repair_passthrough_when_structured():
    msg = AIMessage(
        content="x",
        tool_calls=[
            {
                "name": "build_itinerary",
                "args": {"destination": "P", "num_days": 2},
                "id": "c1",
                "type": "tool_call",
            }
        ],
    )
    assert N._repair_leaked_response(msg) is msg


def test_repair_passthrough_when_no_marker():
    msg = AIMessage(content="Olá, tudo bem")
    assert N._repair_leaked_response(msg) is msg


def test_repair_recovers_leaked_call():
    msg = AIMessage(
        content='<function=search_tourist_attractions>{"destination": "Paris"}</function>'
    )
    out = N._repair_leaked_response(msg)
    assert out.content == ""
    assert out.tool_calls[0]["name"] == "search_tourist_attractions"
    assert out.tool_calls[0]["args"] == {"destination": "Paris"}


def test_repair_unrecoverable_returns_friendly():
    out = N._repair_leaked_response(AIMessage(content="<function=unknown>{}</function>"))
    assert out.content == _UNRECOVERABLE_MSG
    assert not out.tool_calls


def test_repair_drops_premature_build():
    content = (
        '<function=search_tourist_attractions>{"destination": "P"}</function>'
        '<function=build_itinerary>{"destination": "P", "num_days": 2}</function>'
    )
    out = N._repair_leaked_response(AIMessage(content=content))
    assert [c["name"] for c in out.tool_calls] == ["search_tourist_attractions"]


# --- _logged_node / _logged_router ---------------------------

def test_logged_node_success():
    @N._logged_node
    def sample(state):
        return {"ok": 1}

    assert sample(types.SimpleNamespace(run_id="r1")) == {"ok": 1}
    assert sample.__name__ == "sample"
    trail = audit.load_audit_trail("r1")
    assert len(trail) == 1
    assert (trail[0].step, trail[0].step_type, trail[0].status) == (
        "sample",
        "node",
        "ok",
    )
    assert trail[0].duration_ms is not None


def test_logged_node_error_reraises_and_audits():
    @N._logged_node
    def boom(state):
        raise ValueError("x")

    with pytest.raises(ValueError):
        boom(types.SimpleNamespace(run_id="r1"))
    trail = audit.load_audit_trail("r1")
    assert trail[0].status == "error"
    assert trail[0].error == "ValueError"


def test_logged_node_missing_run_id_uses_dash():
    @N._logged_node
    def sample2(state):
        return {}

    sample2(types.SimpleNamespace())
    assert any(s.step == "sample2" for s in audit.load_audit_trail("-"))


def test_logged_router_returns_and_logs():
    @N._logged_router
    def route(state):
        return "call_tools"

    assert route(types.SimpleNamespace(run_id="r1")) == "call_tools"
