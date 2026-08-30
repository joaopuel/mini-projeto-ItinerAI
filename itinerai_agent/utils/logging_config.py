"""Bootstrap do logging estruturado em JSON do ItinerAI (T04/#15).

Emite um evento JSON por linha (uma linha = um evento) para `logs/itinerai.log`,
com um `run_id` por turno da conversa correlacionando todos os eventos do turno.
Somente stdlib — sem novas dependências no `requirements.txt`.

A configuração é responsabilidade da APLICAÇÃO: `main.py` chama
`configure_logging()` logo após `load_dotenv()` e antes de importar o grafo. A
biblioteca (`itinerai_agent/__init__.py`) mantém apenas o `NullHandler` — quando
o agente roda pela LangGraph platform (que não passa por `main.py`), os logs são
absorvidos e o terminal fica limpo.

Regras de design (não alterar sem alinhar):

- **Só arquivo por padrão.** `LOG_TO_STDERR=1` espelha os eventos no stderr para
  depuração; o padrão desligado mantém o terminal do usuário 100% limpo.
- **Nada de segredos nem conteúdo de mensagens.** O `JsonFormatter` ainda redige
  o valor de `GROQ_API_KEY` da string final como defesa em profundidade; os nós
  logam só metadados (contagens, nomes de tools, decisões), nunca o texto das
  mensagens.
- **`run_id` por turno**, propagado de duas formas: no `AgentState.run_id` (lido
  pelos decorators de nó em `nodes.py`) e num `ContextVar` (herdado pelas
  chamadas mais profundas em `tools.py`, inclusive nos ramos paralelos do
  fan-out da busca).
- O filtro do `run_id` fica nos **handlers**, não no logger: um filtro de logger
  não roda para os records propagados dos loggers filhos
  (`itinerai_agent.utils.*`); um filtro de handler roda.
"""

import contextvars
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from itinerai_agent.utils.config import LOG_LEVEL, LOG_TO_STDERR

# utils/ -> itinerai_agent/ -> raiz do projeto. Resolvido a partir do arquivo
# (não do cwd), no mesmo padrão de `tools.OUTPUT_DIR` e `memory.MEMORY_DB_PATH`.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_FILE = _LOG_DIR / "itinerai.log"

_PACKAGE_LOGGER = "itinerai_agent"
# Marca os handlers criados aqui, para `configure_logging()` ser idempotente.
_HANDLER_SENTINEL = "_itinerai_json_handler"
# Teto de tamanho para valores string nos campos `extra` (evita despejar textos).
_MAX_VALUE_CHARS = 500

# run_id de correlação — UM POR TURNO (uma chamada `graph.invoke`). Fica neste
# módulo folha (só stdlib + config) para `main.py` e `nodes.py` importarem sem
# ciclo.
run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "itinerai_run_id", default="-"
)


def new_run_id() -> str:
    """Gera um novo `run_id` (UUID4 canônico) para um turno da conversa."""
    return str(uuid.uuid4())


# Atributos padrão de um `LogRecord`: tudo que NÃO estiver aqui é tratado como
# campo `extra` e entra no JSON. `message`/`asctime` são adicionados por
# formatters; `run_id` é tratado à parte (chave fixa).
_RESERVED_LOG_RECORD_KEYS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName", "run_id"}


class JsonFormatter(logging.Formatter):
    """Formata cada registro como uma única linha JSON.

    Chaves fixas: `timestamp` (UTC ISO-8601), `level`, `logger`, `event` (a
    mensagem renderizada) e `run_id`. Qualquer campo passado via `extra=` é
    mesclado; `exc_info` vira `error` + `traceback`.
    """

    def __init__(self) -> None:
        super().__init__()
        # Lido após o `load_dotenv()` do `main.py`. Só redige se parecer uma
        # chave real (nunca substitui "" quando a variável está ausente).
        key = os.getenv("GROQ_API_KEY") or ""
        self._secret = key if len(key) >= 8 else None

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        payload: dict[str, object] = {
            "timestamp": timestamp.replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "run_id": getattr(record, "run_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_KEYS:
                continue
            if isinstance(value, str) and len(value) > _MAX_VALUE_CHARS:
                value = value[:_MAX_VALUE_CHARS] + "…"
            payload[key] = value
        if record.exc_info:
            exc_type = record.exc_info[0]
            payload.setdefault("error", exc_type.__name__ if exc_type else "Exception")
            payload["traceback"] = self.formatException(record.exc_info)
        rendered = json.dumps(payload, ensure_ascii=False, default=str)
        if self._secret:
            rendered = rendered.replace(self._secret, "***REDACTED***")
        return rendered


class _RunIdFilter(logging.Filter):
    """Injeta o `run_id` (do `ContextVar`) em todo record que chega ao handler,
    inclusive nos propagados dos loggers filhos (`itinerai_agent.utils.*`)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = run_id_var.get()
        return True


def configure_logging() -> logging.Logger:
    """Pluga o handler JSON (arquivo + stderr opcional) no logger do pacote.

    Idempotente: chamadas repetidas não duplicam handlers. Deve ser chamada
    pela aplicação (`main.py`) logo após `load_dotenv()`.
    """
    logger = logging.getLogger(_PACKAGE_LOGGER)
    logger.setLevel(
        logging.getLevelNamesMapping().get(str(LOG_LEVEL).upper(), logging.INFO)
    )

    if any(getattr(handler, _HANDLER_SENTINEL, False) for handler in logger.handlers):
        return logger  # já configurado

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = JsonFormatter()
    run_id_filter = _RunIdFilter()

    handlers: list[logging.Handler] = [
        RotatingFileHandler(
            _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    ]
    if LOG_TO_STDERR:
        handlers.append(logging.StreamHandler())  # sys.stderr

    for handler in handlers:
        setattr(handler, _HANDLER_SENTINEL, True)
        handler.setFormatter(formatter)
        handler.addFilter(run_id_filter)
        logger.addHandler(handler)

    # Nada propaga para o root logger / `logging.lastResort` → terminal limpo
    # mesmo que outra biblioteca configure o root.
    logger.propagate = False
    return logger
