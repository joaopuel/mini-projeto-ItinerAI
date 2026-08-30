"""Trilha de auditoria do ItinerAI em SQLite (T05/#16).

Grava **uma linha por passo executado** (nó do grafo ou tool) com a **latência
medida**, correlacionada aos logs estruturados (T04) pelo **mesmo `run_id`**. É
o segundo sinal de observabilidade exigido pelo §4.6; a T06 cruza os dois para
reconstruir e investigar uma execução real.

Design (mesmo espírito de `memory.py` — não alterar sem alinhar):

- **SQLite via `sqlite3` da stdlib**, sem nova dependência. Banco **próprio**
  (`itinerai_audit.db`, na raiz do projeto, não versionado) — separado da
  memória de registro único porque a trilha é *append-only* e cresce a cada
  turno. Apagar o arquivo reseta a trilha.
- **Funções puras e testáveis**: todas aceitam um `db_path` opcional que cai
  para `AUDIT_DB_PATH` em tempo de chamada (facilita testes com banco
  temporário — cobertos pela T07/#18).
- **`try_record(...)` é o wrapper best-effort** usado pela instrumentação em
  `nodes.py`/`tools.py`/`main.py`: engole e loga qualquer erro. Auditar **nunca**
  derruba um turno (observabilidade não é caminho crítico; também cobre um lock
  transitório do SQLite quando os dois ramos do fan-out escrevem ao mesmo tempo).
- **`created_at` em UTC ISO-8601 `…Z`**, igual aos logs da T04 (correlação). A
  `memory.py` permanece em hora local (dado de produto, não correlacionado).
"""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Banco na raiz do projeto (não versionado — ver .gitignore). Resolvido a partir
# do arquivo, não do cwd — mesma estratégia de `memory.MEMORY_DB_PATH` e
# `tools.OUTPUT_DIR`.
AUDIT_DB_PATH = Path(__file__).resolve().parents[2] / "itinerai_audit.db"

_TABLE_NAME = "execution_audit"

# Vocabulário controlado (documentação; não é CHECK no schema para manter a
# escrita barata e tolerante).
STEP_TYPES = ("node", "tool", "turn")
STATUSES = ("ok", "error", "retry", "fallback")


class AuditStep(BaseModel):
    """Um passo da trilha de auditoria de um turno.

    `duration_ms` é `None` em linhas pontuais (ex.: `retry`); `error` é `None`
    quando `status == "ok"`. `created_at` é preenchido por `record_audit_step`
    no momento da escrita (UTC)."""

    run_id: str
    step: str
    step_type: str
    status: str
    duration_ms: float | None = None
    error: str | None = None
    created_at: str | None = None


@contextmanager
def _connect(db_path: Path | None) -> Iterator[sqlite3.Connection]:
    """Abre uma conexão, resolvendo `db_path` em tempo de chamada e garantindo
    que a pasta exista.

    `timeout=10`: os dois ramos do fan-out da busca escrevem de threads
    diferentes; o segundo escritor espera o primeiro liberar o lock (as
    escritas são um único INSERT, então a espera é irrelevante na prática).

    Comita/rola a transação (`with connection`) e **fecha** a conexão ao sair —
    o `with sqlite3.connect(...)` sozinho só encerra a transação, o que no
    Windows deixaria o arquivo travado."""
    if db_path is None:
        db_path = AUDIT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=10)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db(db_path: Path | None = None) -> None:
    """Cria a tabela e o índice de auditoria se ainda não existirem.

    `id INTEGER PRIMARY KEY` (rowid) dá ordenação estável dos passos, já que
    `created_at` pode empatar."""
    with _connect(db_path) as connection:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                id INTEGER PRIMARY KEY,
                run_id TEXT NOT NULL,
                step TEXT NOT NULL,
                step_type TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms REAL,
                error TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{_TABLE_NAME}_run_id "
            f"ON {_TABLE_NAME} (run_id)"
        )


def record_audit_step(step: AuditStep, db_path: Path | None = None) -> None:
    """Grava (append) um passo na trilha, carimbando `created_at` com o horário
    atual em UTC.

    Função pura: **propaga** qualquer erro de I/O — a instrumentação usa
    `try_record`, que é quem degrada. Cria a tabela antes, para ser seguro
    chamar sem um `init_db` explícito."""
    init_db(db_path)
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with _connect(db_path) as connection:
        connection.execute(
            f"""
            INSERT INTO {_TABLE_NAME}
                (run_id, step, step_type, status, duration_ms, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                step.run_id,
                step.step,
                step.step_type,
                step.status,
                step.duration_ms,
                step.error,
                created_at,
            ),
        )


def load_audit_trail(run_id: str, db_path: Path | None = None) -> list[AuditStep]:
    """Todos os passos de um `run_id`, em ordem de execução (`id`). Lista vazia
    se não houver registro."""
    init_db(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT run_id, step, step_type, status, duration_ms, error, created_at
            FROM {_TABLE_NAME}
            WHERE run_id = ?
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()

    return [
        AuditStep(
            run_id=row[0],
            step=row[1],
            step_type=row[2],
            status=row[3],
            duration_ms=row[4],
            error=row[5],
            created_at=row[6],
        )
        for row in rows
    ]


def format_audit_trail(run_id: str, db_path: Path | None = None) -> str:
    """Texto legível da trilha de um turno: tabela de passos com latência, o
    passo mais lento (gargalo), o total do turno e um resumo de
    retries/fallbacks/erros. É o que `show_audit.py` imprime."""
    steps = load_audit_trail(run_id, db_path)
    if not steps:
        return f"Nenhum passo de auditoria encontrado para run_id {run_id}."

    header = f"{'#':>3}  {'passo':<24} {'tipo':<6} {'status':<9} {'ms':>10}"
    lines = [f"Trilha de auditoria — run_id {run_id}", "", header, "-" * len(header)]

    timed: list[tuple[str, float]] = []
    turn_ms: float | None = None
    retries = errors = fallbacks = 0

    for index, step in enumerate(steps, start=1):
        duration = "—" if step.duration_ms is None else f"{step.duration_ms:.1f}"
        note = f"  ({step.error})" if step.error else ""
        lines.append(
            f"{index:>3}  {step.step:<24} {step.step_type:<6} "
            f"{step.status:<9} {duration:>10}{note}"
        )
        if step.status == "retry":
            retries += 1
        elif step.status == "error":
            errors += 1
        elif step.status == "fallback":
            fallbacks += 1
        if step.step_type == "turn":
            turn_ms = step.duration_ms
        elif step.status == "ok" and step.duration_ms is not None:
            timed.append((step.step, step.duration_ms))

    lines.append("")
    if timed:
        slowest_step, slowest_ms = max(timed, key=lambda item: item[1])
        lines.append(f"Passo mais lento: {slowest_step} ({slowest_ms:.1f} ms)")
    if turn_ms is not None:
        lines.append(f"Total (turno): {turn_ms:.1f} ms")
    lines.append(
        f"{len(steps)} passos · {retries} retries · "
        f"{fallbacks} fallbacks · {errors} erros"
    )
    return "\n".join(lines)


def try_record(
    run_id: str,
    step: str,
    step_type: str,
    status: str,
    duration_ms: float | None = None,
    error: str | None = None,
) -> None:
    """Grava um passo de forma **best-effort**: monta o `AuditStep`, chama
    `record_audit_step` e **engole** qualquer exceção (só loga um
    `audit_write_failed`). É esta a função que a instrumentação de
    `nodes.py`/`tools.py`/`main.py` chama — uma falha ao auditar não pode
    derrubar um turno."""
    try:
        record_audit_step(
            AuditStep(
                run_id=run_id or "-",
                step=step,
                step_type=step_type,
                status=status,
                duration_ms=duration_ms,
                error=error,
            )
        )
    except Exception as exc:  # best-effort por design — auditar não pode falhar alto
        logger.warning(
            "audit_write_failed",
            extra={"step": step, "error": type(exc).__name__},
        )
