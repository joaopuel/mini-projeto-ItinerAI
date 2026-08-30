"""Pacote do agente ItinerAI."""

import logging

# Padrão de logging de biblioteca: um NullHandler no logger raiz do pacote
# "absorve" os registros quando a aplicação não configurou logging (conta como
# handler encontrado, então o logging.lastResort não escreve no stderr),
# mantendo o terminal limpo. Quem pluga o handler JSON + arquivo + run_id é a
# APLICAÇÃO: `main.py` chama `utils/logging_config.configure_logging()` no
# startup (T04/#15). Rodando pela LangGraph platform (sem `main.py`), fica só
# este NullHandler e o terminal permanece limpo.
logging.getLogger(__name__).addHandler(logging.NullHandler())
