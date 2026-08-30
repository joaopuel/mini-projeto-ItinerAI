"""Exibe a trilha de auditoria de um turno da conversa (T05/#16).

Uso:

    python show_audit.py <run_id>

O `run_id` aparece em toda linha de `logs/itinerai.log` do turno (e no evento
`run_start`/`run_end`). A trilha vem de `itinerai_audit.db`, gravada durante a
execução do agente.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")  # acentos/traços da tabela no console do Windows

from itinerai_agent.utils.audit import format_audit_trail


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python show_audit.py <run_id>")
        raise SystemExit(2)
    print(format_audit_trail(sys.argv[1]))


if __name__ == "__main__":
    main()
