"""Testes da política de resiliência HTTP de `tools.py` (T02/#13), cobertos aqui
pela T07/#18. HTTP e `time.sleep` sempre simulados."""

import types
from unittest.mock import Mock

import pytest
import requests

from itinerai_agent.utils import audit as A
from itinerai_agent.utils import tools as T
from itinerai_agent.utils.state import TouristAttraction, WikipediaPageResult


def _raise_http():
    raise requests.exceptions.HTTPError("500")


def resp(status=200, text="", boom=None):
    return types.SimpleNamespace(
        status_code=status,
        text=text,
        raise_for_status=(boom or (lambda: None)),
    )


@pytest.fixture
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(T.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


# --- _get_wikipedia --------------------------------------------------

def test_get_success_first_try(monkeypatch, no_sleep):
    monkeypatch.setattr(T.requests, "get", lambda url, **kw: resp(200))
    assert T._get_wikipedia("http://x").status_code == 200
    assert no_sleep == []


def test_get_retries_then_succeeds(monkeypatch, no_sleep):
    monkeypatch.setattr(
        T.requests,
        "get",
        Mock(side_effect=[requests.exceptions.ConnectionError(), resp(200)]),
    )
    assert T._get_wikipedia("http://x").status_code == 200
    assert no_sleep == [0.5]
    trail = A.load_audit_trail("-")
    assert any(s.step == "wikipedia_fetch" and s.status == "retry" for s in trail)


def test_get_exhausts_retries_raises(monkeypatch, no_sleep):
    monkeypatch.setattr(
        T.requests, "get", Mock(side_effect=requests.exceptions.Timeout())
    )
    with pytest.raises(requests.exceptions.Timeout):
        T._get_wikipedia("http://x")
    assert no_sleep == [0.5, 1.0]


def test_get_non_retryable_propagates_immediately(monkeypatch, no_sleep):
    monkeypatch.setattr(
        T.requests, "get", Mock(side_effect=requests.exceptions.HTTPError())
    )
    with pytest.raises(requests.exceptions.HTTPError):
        T._get_wikipedia("http://x")
    assert no_sleep == []


# --- _fetch_wikipedia_page -----------------------------------------

def test_fetch_404_returns_none(monkeypatch):
    monkeypatch.setattr(T, "_get_wikipedia", lambda url: resp(404))
    assert T._fetch_wikipedia_page("Tourism in Paris") is None


def test_fetch_parses_content(monkeypatch):
    html = "<div id='mw-content-text'><p>Paris é linda</p><li>Louvre</li></div>"
    monkeypatch.setattr(T, "_get_wikipedia", lambda url: resp(200, text=html))
    text, url = T._fetch_wikipedia_page("Tourism in Paris")
    assert text == "Paris é linda\nLouvre"
    assert url == "https://en.wikipedia.org/wiki/Tourism_in_Paris"


def test_fetch_missing_content_div(monkeypatch):
    monkeypatch.setattr(
        T, "_get_wikipedia", lambda url: resp(200, text="<html><body>x</body></html>")
    )
    assert T._fetch_wikipedia_page("Paris") is None


def test_fetch_empty_content(monkeypatch):
    monkeypatch.setattr(
        T, "_get_wikipedia", lambda url: resp(200, text="<div id='mw-content-text'></div>")
    )
    assert T._fetch_wikipedia_page("Paris") is None


def test_fetch_http_error_propagates(monkeypatch):
    monkeypatch.setattr(T, "_get_wikipedia", lambda url: resp(500, boom=_raise_http))
    with pytest.raises(requests.exceptions.HTTPError):
        T._fetch_wikipedia_page("Paris")


# --- fetch_page_attractions --------------------------------------

def test_fpa_network_failure_marks_unavailable(monkeypatch):
    def boom(title):
        raise requests.exceptions.ConnectionError("sem rede")

    monkeypatch.setattr(T, "_fetch_wikipedia_page", boom)
    result = T.fetch_page_attractions("Tourism in P", "P", "tourism")
    assert result == WikipediaPageResult(kind="tourism", found=False, unavailable=True)
    trail = A.load_audit_trail("-")
    assert any(s.step == "wikipedia_fetch" and s.status == "error" for s in trail)


def test_fpa_page_missing(monkeypatch):
    monkeypatch.setattr(T, "_fetch_wikipedia_page", lambda title: None)
    result = T.fetch_page_attractions("P", "P", "destination")
    assert result.found is False
    assert result.unavailable is False


def test_fpa_page_with_attractions(monkeypatch):
    monkeypatch.setattr(T, "_fetch_wikipedia_page", lambda title: ("t", "http://u"))
    monkeypatch.setattr(
        T,
        "_extract_attractions",
        lambda dest, text: [TouristAttraction(name="A", description="d", location="l")],
    )
    result = T.fetch_page_attractions("Tourism in P", "P", "tourism")
    assert result.found is True
    assert result.source_url == "http://u"
    assert len(result.attractions) == 1


def test_fpa_page_without_attractions(monkeypatch):
    monkeypatch.setattr(T, "_fetch_wikipedia_page", lambda title: ("t", "http://u"))
    monkeypatch.setattr(T, "_extract_attractions", lambda dest, text: [])
    result = T.fetch_page_attractions("Tourism in P", "P", "tourism")
    assert result.found is False
    assert result.source_url == "http://u"


# --- search_tourist_attractions --------------------------------

def test_search_returns_first_hit(monkeypatch):
    hit = WikipediaPageResult(
        kind="tourism",
        found=True,
        source_url="http://t",
        attractions=[TouristAttraction(name="A", description="d", location="l")],
    )
    monkeypatch.setattr(
        T,
        "fetch_page_attractions",
        lambda title, destination, kind: hit
        if kind == "tourism"
        else WikipediaPageResult(kind="destination"),
    )
    result = T.search_tourist_attractions("Paris")
    assert result.found is True
    assert result.destination == "Paris"
    assert len(result.attractions) == 1


def test_search_all_unavailable(monkeypatch):
    monkeypatch.setattr(
        T,
        "fetch_page_attractions",
        lambda title, destination, kind: WikipediaPageResult(
            kind=kind, found=False, unavailable=True
        ),
    )
    result = T.search_tourist_attractions("Nowhere")
    assert result.found is False
    assert result.unavailable is True
    assert result.attractions == []


def test_search_all_empty_not_unavailable(monkeypatch):
    monkeypatch.setattr(
        T,
        "fetch_page_attractions",
        lambda title, destination, kind: WikipediaPageResult(kind=kind, found=False),
    )
    result = T.search_tourist_attractions("Nowhere")
    assert result.found is False
    assert result.unavailable is False
