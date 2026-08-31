"""Testes de `itinerai_agent/utils/state.py` — o reducer `_merge_page_results`
(os modelos pydantic são exercitados no import)."""

from itinerai_agent.utils.state import WikipediaPageResult, _merge_page_results

R1 = WikipediaPageResult(kind="tourism")
R2 = WikipediaPageResult(kind="destination")


def test_merge_none_none():
    assert _merge_page_results(None, None) == {}


def test_merge_existing_only():
    assert _merge_page_results({"tourism": R1}, None) == {"tourism": R1}


def test_merge_new_only():
    assert _merge_page_results(None, {"destination": R2}) == {"destination": R2}


def test_merge_disjoint_keys():
    merged = _merge_page_results({"tourism": R1}, {"destination": R2})
    assert merged == {"tourism": R1, "destination": R2}


def test_merge_new_overwrites_key():
    merged = _merge_page_results({"tourism": R1}, {"tourism": R2})
    assert merged["tourism"] is R2
