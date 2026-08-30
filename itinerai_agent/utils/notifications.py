"""Cliente do webhook do n8n para envio do itinerário por e-mail (T14/#25).

Este módulo é o lado da aplicação da automação low-code exigida pelo §4.9: toda
a lógica principal (montagem do roteiro, aprovação humana, validação do e-mail)
permanece no agente, e o n8n atua apenas como camada de integração que dispara o
e-mail. O contrato — caminho, header de autenticação e campos do corpo — é o
definido pelo workflow versionado em `docs/low-code/n8n-workflow.json` (T13/#24).

Regras de design (não alterar sem alinhar):

- **Timeout configurável, mas SEM retry** (`N8N_TIMEOUT`). Diferença deliberada
  em relação a `_get_wikipedia` (`tools.py`), que repete com backoff: um GET da
  Wikipédia é idempotente, um POST que dispara e-mail **não é**. Um `Timeout` do
  lado do cliente não prova que o servidor deixou de processar — repetir enviaria
  uma segunda cópia do roteiro. Repetir automaticamente uma ação que o §4.5
  classifica como irreversível contradiz a própria exigência de aprovação humana.
- **Falha de rede não derruba o turno.** Ela vira um `NotificationResult` com
  `status="failed"`; o arquivo `.md` já gerado continua disponível em `output/`.
  A garantia de que **nenhuma** exceção derruba o turno é do nó
  `notify_recipient` (`nodes.py`), não deste módulo — aqui vale a regra geral do
  projeto: exceções específicas, para um bug fora de rede continuar falhando alto.
- **Degradação silenciosa:** sem `N8N_WEBHOOK_URL` configurada, nenhuma chamada
  externa é feita e o resultado é `not_configured`.
- **O e-mail do destinatário nunca aparece em log nem na auditoria** — só
  mascarado por `mask_email`.
"""

import logging
import time
from typing import Literal

import requests
from pydantic import BaseModel, Field
from requests.exceptions import RequestException

from itinerai_agent.utils import audit
from itinerai_agent.utils.config import N8N_TIMEOUT, N8N_WEBHOOK_TOKEN, N8N_WEBHOOK_URL
from itinerai_agent.utils.logging_config import run_id_var

logger = logging.getLogger(__name__)

# Lidos como atributos do módulo (e não direto de `config`) para que possam ser
# trocados em tempo de chamada — mesmo padrão de `tools.OUTPUT_DIR`.
WEBHOOK_URL = N8N_WEBHOOK_URL
WEBHOOK_TOKEN = N8N_WEBHOOK_TOKEN

# Header de autenticação esperado pelo nó Webhook do workflow do n8n; o valor é
# a credencial "ItinerAI Webhook Token" criada lá dentro.
TOKEN_HEADER = "X-ItinerAI-Token"

# Passo registrado na trilha de auditoria (T05/#16).
_AUDIT_STEP = "n8n_webhook"


class ItineraryNotification(BaseModel):
    """Payload enviado ao webhook do n8n.

    Os campos são exatamente os que o nó `Validar payload` do workflow exige;
    mudar qualquer nome aqui quebra o fluxo do n8n."""

    destination: str
    num_days: int
    recipient: str
    markdown: str
    run_id: str = ""


class NotificationResult(BaseModel):
    """Desfecho da oferta de envio do roteiro por e-mail.

    Além dos desfechos do próprio envio (`sent` / `failed` / `not_configured`),
    cobre as três decisões tomadas no terminal antes de qualquer chamada
    externa: `declined` (o usuário respondeu "n"), `cancelled` (interrompeu a
    coleta com Ctrl+C) e `invalid_email` (o endereço informado não passou na
    validação por regex). Guardado em `AgentState.notification`, é ele que impede
    a pergunta de se repetir a cada turno."""

    status: Literal[
        "sent", "declined", "cancelled", "invalid_email", "not_configured", "failed"
    ]
    detail: str = Field(default="", description="Motivo, quando houver.")


def mask_email(email: str) -> str:
    """Mascara o endereço para log/auditoria: `joao@exemplo.com` →
    `j***@exemplo.com`.

    Preserva só a primeira letra do usuário e o domínio — o suficiente para
    correlacionar um envio numa investigação, sem registrar o dado pessoal.
    Entradas sem `@` são mascaradas por inteiro."""
    if not email:
        return ""
    local, separator, domain = email.partition("@")
    if not separator:
        return "***"
    return f"{local[:1]}***@{domain}"


def _post(payload: ItineraryNotification) -> requests.Response:
    """POST no webhook, com timeout explícito (`N8N_TIMEOUT`) e **uma única
    tentativa**.

    A ausência de retry é deliberada: enviar e-mail não é idempotente, e um
    `Timeout` do lado do cliente não prova que o n8n deixou de processar a
    requisição — repetir arriscaria uma segunda cópia do roteiro na caixa do
    usuário. Ver o docstring do módulo.

    Erros de transporte e de status HTTP são tratados pelo chamador."""
    headers = {"Content-Type": "application/json"}
    if WEBHOOK_TOKEN:
        headers[TOKEN_HEADER] = WEBHOOK_TOKEN

    return requests.post(
        WEBHOOK_URL,
        json=payload.model_dump(),
        headers=headers,
        timeout=N8N_TIMEOUT,
    )


def send_itinerary(payload: ItineraryNotification) -> NotificationResult:
    """Envia o roteiro ao webhook do n8n e devolve o desfecho.

    **Não levanta em falha de rede, status HTTP de erro ou ausência de
    configuração** — os três viram um `NotificationResult`, e o `.md` gerado
    permanece em `output/`. Um erro fora dessas famílias (um bug de serialização,
    por exemplo) **propaga de propósito**, seguindo a regra do projeto de falhar
    alto em bug e degradar em rede; quem garante que isso não derruba o turno é o
    nó `notify_recipient`."""
    masked = mask_email(payload.recipient)

    if not WEBHOOK_URL:
        # Degradação silenciosa e documentada: sem a variável de ambiente, a
        # integração simplesmente não existe para esta execução.
        logger.info("n8n_not_configured", extra={"recipient": masked})
        return NotificationResult(
            status="not_configured",
            detail="N8N_WEBHOOK_URL não configurada.",
        )

    run_id = run_id_var.get()
    start = time.perf_counter()
    try:
        response = _post(payload)
        response.raise_for_status()
    except RequestException as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "n8n_webhook_failed",
            extra={
                "recipient": masked,
                "error": type(exc).__name__,
                "duration_ms": round(duration_ms, 1),
            },
        )
        audit.try_record(
            run_id, _AUDIT_STEP, "tool", "error", duration_ms, type(exc).__name__
        )
        return NotificationResult(status="failed", detail=type(exc).__name__)

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "n8n_webhook_sent",
        extra={
            "recipient": masked,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 1),
        },
    )
    audit.try_record(run_id, _AUDIT_STEP, "tool", "ok", duration_ms)
    return NotificationResult(status="sent")
