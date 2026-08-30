"""Configuração e fixtures globais da suíte de testes do ItinerAI (T07/#18)."""

# --- 1. GROQ_API_KEY dummy ANTES de qualquer import de itinerai_agent --------
#
# tools.py e nodes.py constroem `ChatGroq(...)` no import do módulo. O
# `@model_validator(mode="after")` do ChatGroq instancia `groq.Groq(api_key=...)`,
# que levanta `groq.GroqError` (Exception simples — NÃO ValueError, logo NÃO é
# convertida em ValidationError pelo pydantic) quando a chave está ausente. Um
# valor fake destrava o import: `groq.Groq(api_key="test-key")` não valida nada e
# não faz rede, e nenhum teste chama `.invoke` de verdade (tudo mockado). Precisa
# rodar ANTES da coleta, por isso fica no topo do módulo, não numa fixture.
import os

os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-120b")
os.environ.setdefault("GROQ_TEMPERATURE", "0.7")
os.environ.setdefault("WIKIPEDIA_TIMEOUT", "10")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.pop("LOG_TO_STDERR", None)

import logging
from collections.abc import Iterator

import pytest

from itinerai_agent.utils import audit, memory, tools


@pytest.fixture(autouse=True)
def _isolate_disk(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Redireciona para um `tmp_path` por teste todos os caminhos de disco que
    os módulos resolvem em TEMPO DE CHAMADA (`if X is None: X = MODULE.CONST`).

    Cobre inclusive os caminhos sem injeção de `db_path`:
    `audit.try_record` (sempre usa `AUDIT_DB_PATH`) e `build_itinerary`
    (sempre usa `tools.OUTPUT_DIR`)."""
    monkeypatch.setattr(memory, "MEMORY_DB_PATH", tmp_path / "itinerai_memory.db")
    monkeypatch.setattr(audit, "AUDIT_DB_PATH", tmp_path / "itinerai_audit.db")
    monkeypatch.setattr(tools, "OUTPUT_DIR", tmp_path / "output")


@pytest.fixture
def restore_package_logger() -> Iterator[logging.Logger]:
    """Snapshot/restore do logger `itinerai_agent`: os testes de
    `configure_logging()` plugam handlers globais e setam `propagate=False`."""
    lg = logging.getLogger("itinerai_agent")
    saved_handlers = lg.handlers[:]
    saved_level = lg.level
    saved_propagate = lg.propagate
    yield lg
    for handler in lg.handlers[:]:
        if handler not in saved_handlers:
            handler.close()
            lg.removeHandler(handler)
    lg.setLevel(saved_level)
    lg.propagate = saved_propagate
