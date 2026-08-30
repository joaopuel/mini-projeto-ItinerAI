"""Testes da extração estruturada de `tools.py` — `_invoke_structured` e
`_extract_attractions` com o LLM de extração simulado."""

import types

import pytest

from itinerai_agent.utils import tools as T
from itinerai_agent.utils.state import TouristAttraction


class FakeLLM:
    def __init__(self, content=None, exc=None):
        self.content = content
        self.exc = exc

    def invoke(self, prompt):
        if self.exc is not None:
            raise self.exc
        return types.SimpleNamespace(content=self.content)


def attr(name):
    return TouristAttraction(name=name, description="d", location="l")


# --- _invoke_structured ------------------------------------------------

def test_invoke_ok_object(monkeypatch):
    monkeypatch.setattr(
        T,
        "_extraction_llm",
        FakeLLM(content='{"attractions": [{"name": "A", "description": "d", "location": "l"}]}'),
    )
    result = T._invoke_structured(T._ExtractedAttractions, "prompt")
    assert result is not None
    assert result.attractions[0].name == "A"


def test_invoke_ok_list_wrapped(monkeypatch):
    monkeypatch.setattr(
        T, "_extraction_llm", FakeLLM(content='[{"name": "A", "area": "Centro"}]')
    )
    result = T._invoke_structured(T._ClusteredAttractions, "prompt")
    assert result is not None
    assert result.attractions[0].name == "A"


def test_invoke_no_json_returns_none(monkeypatch):
    monkeypatch.setattr(T, "_extraction_llm", FakeLLM(content="desculpe, não sei"))
    assert T._invoke_structured(T._ExtractedAttractions, "prompt") is None


def test_invoke_non_str_content_returns_none(monkeypatch):
    monkeypatch.setattr(T, "_extraction_llm", FakeLLM(content=123))
    assert T._invoke_structured(T._ExtractedAttractions, "prompt") is None


def test_invoke_schema_mismatch_returns_none(monkeypatch):
    monkeypatch.setattr(
        T, "_extraction_llm", FakeLLM(content='{"attractions": "não é lista"}')
    )
    assert T._invoke_structured(T._ExtractedAttractions, "prompt") is None


def test_invoke_exception_returns_none(monkeypatch):
    monkeypatch.setattr(T, "_extraction_llm", FakeLLM(exc=RuntimeError("boom")))
    assert T._invoke_structured(T._ExtractedAttractions, "prompt") is None


# --- _extract_attractions -------------------------------------------

def test_extract_none_returns_empty(monkeypatch):
    monkeypatch.setattr(T, "_invoke_structured", lambda schema, prompt: None)
    assert T._extract_attractions("Lisboa", "texto da página") == []


def test_extract_dedups_by_name_case_insensitive(monkeypatch):
    extracted = T._ExtractedAttractions(attractions=[attr("A"), attr("a"), attr("B")])
    monkeypatch.setattr(T, "_invoke_structured", lambda schema, prompt: extracted)
    result = T._extract_attractions("Lisboa", "texto")
    assert [a.name for a in result] == ["A", "B"]
