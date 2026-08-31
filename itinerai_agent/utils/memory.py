"""Memória persistente do ItinerAI em SQLite.

Guarda os dados da viagem em andamento (destino e duração em dias) para
permitir a **retomada** de uma conversa depois que o programa é reiniciado
— por exemplo, quando a gravação do itinerário ou outra falha fora de rede
derruba o processo (falhas de rede na Wikipédia são tratadas em `tools.py` e
não derrubam mais). Assim o usuário não precisa redigitar tudo do zero.

Design (não alterar sem alinhar):

- **SQLite via `sqlite3` da stdlib**, sem nova dependência e sem LLM/rede: a
  persistência é determinística, barata e previsível, no mesmo espírito da
  validação por regex do projeto.
- **Registro único** ("apenas a última viagem"): a tabela tem uma linha fixa
  (`id = 1`) que é sobrescrita a cada salvamento (upsert). Não é um histórico
  de várias viagens.
- Funções puras e testáveis (padrão de `tools.py`/`validation.py`): todas
  aceitam um `db_path` opcional, que cai para `MEMORY_DB_PATH` em tempo de
  chamada — o que facilita os testes com um banco temporário.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

# Banco na raiz do projeto (não versionado — ver .gitignore). Resolvido a partir
# do arquivo, não do cwd, para funcionar de qualquer diretório de execução —
# mesma estratégia do OUTPUT_DIR em tools.py.
MEMORY_DB_PATH = Path(__file__).resolve().parents[2] / "itinerai_memory.db"

_TABLE_NAME = "trip_memory"


class TripMemory(BaseModel):
    """Dados persistidos da última viagem.

    Todos os campos de conteúdo são opcionais porque a memória é salva de forma
    incremental, logo após a validação, quando parte das informações ainda pode
    não ter sido coletada. `completed` indica se o itinerário já foi gerado
    (usado para decidir se vale oferecer a retomada no próximo início)."""

    destination: str | None = None
    num_days: int | None = None
    completed: bool = False
    updated_at: str | None = None


@contextmanager
def _connect(db_path: Path | None) -> Iterator[sqlite3.Connection]:
    """Abre uma conexão com o banco, resolvendo `db_path` em tempo de chamada e
    garantindo que a pasta do arquivo exista.

    Comita/rola a transação (`with connection`) e **fecha** a conexão ao sair —
    o `with sqlite3.connect(...)` sozinho só encerra a transação, não fecha o
    handle, o que no Windows deixaria o arquivo travado."""
    if db_path is None:
        db_path = MEMORY_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db(db_path: Path | None = None) -> None:
    """Cria a tabela de memória se ela ainda não existir.

    A restrição `CHECK (id = 1)` garante a semântica de registro único: só pode
    existir a linha da última viagem."""
    with _connect(db_path) as connection:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                destination TEXT,
                num_days INTEGER,
                completed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            )
            """
        )


def save_trip_memory(memory: TripMemory, db_path: Path | None = None) -> None:
    """Salva (upsert) a última viagem na linha única `id = 1`.

    Sobrescreve o registro anterior e carimba `updated_at` com o horário atual.
    Cria a tabela antes, para ser seguro chamar sem um `init_db` explícito."""
    init_db(db_path)
    updated_at = datetime.now().isoformat(timespec="seconds")
    with _connect(db_path) as connection:
        connection.execute(
            f"""
            INSERT INTO {_TABLE_NAME}
                (id, destination, num_days, completed, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                destination = excluded.destination,
                num_days    = excluded.num_days,
                completed   = excluded.completed,
                updated_at  = excluded.updated_at
            """,
            (
                memory.destination,
                memory.num_days,
                int(memory.completed),
                updated_at,
            ),
        )


def load_trip_memory(db_path: Path | None = None) -> TripMemory | None:
    """Carrega a última viagem salva, ou `None` se não houver registro.

    É resiliente a um banco ainda inexistente (retorna `None` em vez de falhar),
    para poder ser chamada logo no início do programa."""
    init_db(db_path)
    with _connect(db_path) as connection:
        cursor = connection.execute(
            f"""
            SELECT destination, num_days, completed, updated_at
            FROM {_TABLE_NAME}
            WHERE id = 1
            """
        )
        row = cursor.fetchone()

    if row is None:
        return None

    destination, num_days, completed, updated_at = row
    return TripMemory(
        destination=destination,
        num_days=num_days,
        completed=bool(completed),
        updated_at=updated_at,
    )
