"""Cliente do webhook do n8n para envio do itinerário por e-mail (T14/#25).

Este módulo é o lado da aplicação da automação low-code exigida pelo §4.9: toda
a lógica principal (montagem do roteiro, aprovação humana, validação do e-mail)
permanece no agente, e o n8n atua apenas como camada de integração que dispara o
e-mail. O contrato — caminho, header de autenticação e campos do corpo — é o
definido pelo workflow versionado em `docs/low-code/n8n-workflow.json` (T13/#24).

Regras de design (não alterar sem alinhar):

- **Resiliência no mesmo padrão da Wikipédia** (`_get_wikipedia` em `tools.py`):
  timeout configurável, retry limitado com backoff exponencial e repetição
  apenas em erros de transporte transitórios (`Timeout`, `ConnectionError`).
- **Nunca derruba o turno.** Qualquer falha vira um `NotificationResult` com
  `status="failed"`; o arquivo `.md` já gerado continua disponível em `output/`.
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
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

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

# --- Resiliência (espelha `_get_wikipedia` em tools.py) ---------------------
_MAX_RETRIES = 2  # tentativas ADICIONAIS após a primeira
_BACKOFF_BASE = 0.5  # s → espera 0.5s, depois 1.0s (0.5 * 2**attempt)
_RETRYABLE_HTTP_ERRORS = (Timeout, RequestsConnectionError)

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
    cobre as duas decisões tomadas no terminal antes de qualquer chamada
    externa: `declined` (o usuário respondeu "n") e `invalid_email` (o endereço
    informado não passou na validação por regex). Guardado em
    `AgentState.notification`, é ele que impede a pergunta de se repetir a cada
    turno."""

    status: Literal["sent", "declined", "invalid_email", "not_configured", "failed"]
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


def _post_with_retry(payload: ItineraryNotification, masked: str) -> requests.Response:
    """POST no webhook com timeout explícito (`N8N_TIMEOUT`) e retry limitado
    com backoff exponencial.

    Repete no máximo `_MAX_RETRIES` vezes, apenas em erros de transporte
    transitórios. Erros de status HTTP são tratados pelo chamador
    (`raise_for_status`); o esgotamento das tentativas propaga a última
    exceção."""
    headers = {"Content-Type": "application/json"}
    if WEBHOOK_TOKEN:
        headers[TOKEN_HEADER] = WEBHOOK_TOKEN

    for attempt in range(_MAX_RETRIES + 1):
        try:
            return requests.post(
                WEBHOOK_URL,
                json=payload.model_dump(),
                headers=headers,
                timeout=N8N_TIMEOUT,
            )
        except _RETRYABLE_HTTP_ERRORS as exc:
            if attempt >= _MAX_RETRIES:
                logger.warning(
                    "n8n webhook: %s — %d tentativas sem sucesso (destinatário %s)",
                    type(exc).__name__, attempt + 1, masked,
                )
                raise
            wait = _BACKOFF_BASE * (2**attempt)
            logger.warning(
                "n8n webhook: %s — nova tentativa %d/%d em %.1fs (destinatário %s)",
                type(exc).__name__, attempt + 1, _MAX_RETRIES, wait, masked,
            )
            # Cada retry é uma linha pontual na trilha (T05); o resultado final
            # (ok/erro + latência) é gravado por `send_itinerary`.
            audit.try_record(
                run_id_var.get(), _AUDIT_STEP, "tool", "retry", error=type(exc).__name__
            )
            time.sleep(wait)


def send_itinerary(payload: ItineraryNotification) -> NotificationResult:
    """Envia o roteiro ao webhook do n8n e devolve o desfecho.

    Nunca levanta: uma falha de rede, um status HTTP de erro ou a ausência de
    configuração viram um `NotificationResult`. O `.md` gerado permanece em
    `output/` em qualquer cenário."""
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
        response = _post_with_retry(payload, masked)
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
