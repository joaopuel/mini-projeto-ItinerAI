"""Pacote do agente ItinerAI."""

import logging

# Padrão de logging de biblioteca: um NullHandler no logger raiz do pacote
# "absorve" os registros quando a aplicação não configurou logging (conta como
# handler encontrado, então o logging.lastResort não escreve no stderr),
# mantendo o terminal limpo. A T04 (#15) pluga aqui o handler JSON + arquivo +
# run_id; as chamadas de log já feitas nas tools passam a fluir por ele.
logging.getLogger(__name__).addHandler(logging.NullHandler())
