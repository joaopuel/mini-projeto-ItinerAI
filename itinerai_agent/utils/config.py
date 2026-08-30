"""Configuração do ItinerAI lida de variáveis de ambiente.

Lida no import — depende de `load_dotenv()` (`main.py`), ou do `"env"` do
`langgraph.json`, ter populado o ambiente antes. Os valores padrão preservam o
comportamento anterior à externalização, então rodar sem `.env` (além da
`GROQ_API_KEY`) não muda nada.
"""

import os

# --- LLM (Groq) — T03/#14 ---
# Nome do modelo, usado tanto pelo agente (`_llm` em nodes.py) quanto pela
# extração (`_extraction_llm` em tools.py).
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# Temperatura do LLM do agente. 0.7 é o default da langchain-groq (valor efetivo
# antes da externalização); use 0 para respostas mais determinísticas. O LLM de
# extração usa `temperature=0` fixo, à parte desta variável.
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))

# --- Integrações externas (Wikipédia) — T02/#13 ---
# Timeout (em segundos) das requisições HTTP à Wikipédia.
WIKIPEDIA_TIMEOUT = float(os.getenv("WIKIPEDIA_TIMEOUT", "10"))

# --- Integração low-code (n8n) — T14/#25 ---
# URL do webhook do n8n que dispara o e-mail com o roteiro (ver o workflow em
# `docs/low-code/n8n-workflow.json`). **Vazia por padrão**: sem ela, a aplicação
# não faz nenhuma chamada externa e a oferta de envio degrada silenciosamente.
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()
# Valor do header `X-ItinerAI-Token`, correspondente à credencial "ItinerAI
# Webhook Token" (Header Auth) criada dentro do n8n. Nunca versionado.
N8N_WEBHOOK_TOKEN=iO7UmNF0WJUWSnDvxI7nBhHPDx3DHVzc4sDSgEj0yk8
# Timeout (em segundos) da requisição ao webhook, espelhando WIKIPEDIA_TIMEOUT.
N8N_TIMEOUT = float(os.getenv("N8N_TIMEOUT", "10"))

# --- Observabilidade (logging) — T04/#15 ---
# Nível dos logs estruturados em `logs/itinerai.log`: DEBUG / INFO / WARNING /
# ERROR. Valor inválido cai para INFO. Padrão INFO.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
# Espelhar os logs no stderr além do arquivo (para depuração). Padrão desligado,
# para manter o terminal 100% limpo para o usuário. Aceita 1/true/yes/on.
LOG_TO_STDERR = os.getenv("LOG_TO_STDERR", "").strip().lower() in {"1", "true", "yes", "on"}
