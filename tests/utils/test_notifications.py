"""Testes do cliente do webhook do n8n (`notifications.py`, T14/#25).

HTTP sempre simulado — nenhum teste toca a rede. O módulo lê `WEBHOOK_URL` e
`WEBHOOK_TOKEN` como atributos próprios em tempo de chamada, então os testes os
trocam por `monkeypatch` (mesmo padrão de `tools.OUTPUT_DIR` no `conftest.py`).
"""

import types
from unittest.mock import Mock

import pytest
import requests

from itinerai_agent.utils import audit as A
from itinerai_agent.utils import notifications as NT


def _raise_http():
    raise requests.exceptions.HTTPError("500")


def resp(status=200, boom=None):
    return types.SimpleNamespace(
        status_code=status,
        raise_for_status=(boom or (lambda: None)),
    )


def payload(recipient="joao@exemplo.com", run_id="r1"):
    return NT.ItineraryNotification(
        destination="Lisboa",
        num_days=3,
        recipient=recipient,
        markdown="# Roteiro",
        run_id=run_id,
    )


@pytest.fixture
def configured(monkeypatch):
    """Integração ligada, com URL e token."""
    monkeypatch.setattr(NT, "WEBHOOK_URL", "http://n8n.local/webhook/itinerai-email")
    monkeypatch.setattr(NT, "WEBHOOK_TOKEN", "tok123")


# --- mask_email ------------------------------------------------------

def test_mask_email_normal():
    assert NT.mask_email("joao@exemplo.com") == "j***@exemplo.com"


def test_mask_email_without_at():
    assert NT.mask_email("sem-arroba") == "***"


def test_mask_email_empty():
    assert NT.mask_email("") == ""


# --- send_itinerary: sem configuração --------------------------------

def test_not_configured_makes_no_call(monkeypatch):
    monkeypatch.setattr(NT, "WEBHOOK_URL", "")
    post = Mock()
    monkeypatch.setattr(NT.requests, "post", post)

    result = NT.send_itinerary(payload())

    assert result.status == "not_configured"
    post.assert_not_called()


# --- send_itinerary: sucesso -----------------------------------------

def test_success_returns_sent(monkeypatch, configured):
    monkeypatch.setattr(NT.requests, "post", lambda url, **kw: resp(200))
    assert NT.send_itinerary(payload()).status == "sent"


def test_success_sends_url_headers_and_body(monkeypatch, configured):
    post = Mock(return_value=resp(200))
    monkeypatch.setattr(NT.requests, "post", post)

    NT.send_itinerary(payload())

    url = post.call_args.args[0]
    kwargs = post.call_args.kwargs
    assert url == "http://n8n.local/webhook/itinerai-email"
    assert kwargs["headers"][NT.TOKEN_HEADER] == "tok123"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["timeout"] == NT.N8N_TIMEOUT
    assert kwargs["json"] == {
        "destination": "Lisboa",
        "num_days": 3,
        "recipient": "joao@exemplo.com",
        "markdown": "# Roteiro",
        "run_id": "r1",
    }


def test_success_records_audit_ok(monkeypatch, configured):
    monkeypatch.setattr(NT.requests, "post", lambda url, **kw: resp(200))
    NT.send_itinerary(payload())
    trail = A.load_audit_trail("-")
    assert any(s.step == "n8n_webhook" and s.status == "ok" for s in trail)


def test_no_token_omits_header(monkeypatch, configured):
    monkeypatch.setattr(NT, "WEBHOOK_TOKEN", "")
    post = Mock(return_value=resp(200))
    monkeypatch.setattr(NT.requests, "post", post)

    NT.send_itinerary(payload())

    assert NT.TOKEN_HEADER not in post.call_args.kwargs["headers"]


# --- send_itinerary: falhas ------------------------------------------

def test_http_error_status_returns_failed(monkeypatch, configured):
    monkeypatch.setattr(NT.requests, "post", lambda url, **kw: resp(500, boom=_raise_http))

    result = NT.send_itinerary(payload())

    assert result.status == "failed"
    assert result.detail == "HTTPError"


def test_failure_records_audit_error(monkeypatch, configured):
    monkeypatch.setattr(NT.requests, "post", lambda url, **kw: resp(500, boom=_raise_http))
    NT.send_itinerary(payload())
    trail = A.load_audit_trail("-")
    assert any(s.step == "n8n_webhook" and s.status == "error" for s in trail)


def test_connection_error_returns_failed(monkeypatch, configured):
    monkeypatch.setattr(
        NT.requests, "post", Mock(side_effect=requests.exceptions.ConnectionError())
    )
    assert NT.send_itinerary(payload()).status == "failed"


def test_timeout_does_not_retry(monkeypatch, configured):
    """Regressão do achado M1 do code review: enviar e-mail não é idempotente,
    então um `Timeout` NÃO pode virar uma segunda tentativa — o n8n pode já ter
    despachado a mensagem."""
    post = Mock(side_effect=requests.exceptions.Timeout())
    monkeypatch.setattr(NT.requests, "post", post)

    result = NT.send_itinerary(payload())

    assert result.status == "failed"
    assert post.call_count == 1


def test_no_audit_retry_lines(monkeypatch, configured):
    monkeypatch.setattr(
        NT.requests, "post", Mock(side_effect=requests.exceptions.Timeout())
    )
    NT.send_itinerary(payload())
    trail = A.load_audit_trail("-")
    assert not any(s.status == "retry" for s in trail)
