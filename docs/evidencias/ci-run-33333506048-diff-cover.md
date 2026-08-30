# Diff Coverage
## Diff: origin/develop...HEAD, staged and unstaged changes

- itinerai_agent/agent&#46;py (100%)
- itinerai_agent/utils/config&#46;py (100%)
- itinerai_agent/utils/nodes&#46;py (41.2%): Missing lines 241-243,582-583,587,593,602,610-611
- itinerai_agent/utils/notifications&#46;py (44.1%): Missing lines 89-94,105-107,109-111,117-119,123-125,131,134,143,145,148-149,154-161,169,172,174-175,183-184
- itinerai_agent/utils/state&#46;py (100%)
- itinerai_agent/utils/validation&#46;py (75.0%): Missing lines 132

## Summary

- **Total**: 98 lines
- **Missing**: 49 lines
- **Coverage**: 50%



## itinerai_agent/utils/nodes&#46;py

Lines 237-247

```python
  237     # o desvio para `notify_recipient` só acontece quando `main.py` já obteve a
  238     # aprovação explícita do usuário e validou o e-mail, gravando-o no estado.
  239     # Como o envio não depende do LLM, esse turno pula o loop de tool-calling
  240     # inteiro.
! 241     if state.recipient_email and state.itinerary is not None and state.notification is None:
! 242         return "notify_recipient"
! 243     return "validate_input"
  244 
  245 
  246 @_logged_node
  247 def validate_input(state: AgentState) -> dict:
```


---


Lines 578-591

```python
  578     # Envia o roteiro por e-mail via webhook do n8n (T14/#25). Só é alcançado
  579     # pelo desvio de `route_entry`, isto é, depois da aprovação explícita do
  580     # usuário — o §4.5 exige aprovação humana para uma ação externa e
  581     # irreversível. Nenhuma chamada ao LLM acontece neste turno.
! 582     itinerary = state.itinerary
! 583     if itinerary is None or not state.recipient_email:
  584         # Defensivo: `route_entry` já garante ambos. Se algo mudar, o turno
  585         # termina com uma resposta amigável em vez de estourar — e o estado é
  586         # fechado igual ao caminho normal, para não reoferecer em loop.
! 587         return {
  588             "notification": NotificationResult(status="failed", detail="estado incompleto"),
  589             "recipient_email": None,
  590             "messages": [AIMessage(content=_NOTIFICATION_MESSAGES["failed"])],
  591         }
```


---


Lines 589-597

```python
  589             "recipient_email": None,
  590             "messages": [AIMessage(content=_NOTIFICATION_MESSAGES["failed"])],
  591         }
  592 
! 593     result = send_itinerary(
  594         ItineraryNotification(
  595             destination=itinerary.destination,
  596             num_days=itinerary.num_days,
  597             recipient=state.recipient_email,
```


---


Lines 598-606

```python
  598             markdown=render_itinerary_markdown(itinerary),
  599             run_id=state.run_id,
  600         )
  601     )
! 602     logger.info(
  603         "notification_dispatched",
  604         extra={
  605             "node": "notify_recipient",
  606             "recipient": mask_email(state.recipient_email),
```


---


Lines 606-615

```python
  606             "recipient": mask_email(state.recipient_email),
  607             "status": result.status,
  608         },
  609     )
! 610     reply = _NOTIFICATION_MESSAGES.get(result.status, _NOTIFICATION_MESSAGES["failed"])
! 611     return {
  612         "notification": result,
  613         # Zera o destinatário para o nó não rodar de novo no próximo turno.
  614         "recipient_email": None,
  615         "messages": [AIMessage(content=reply)],
```


---



## itinerai_agent/utils/notifications&#46;py

Lines 85-98

```python
  85 
  86     Preserva só a primeira letra do usuário e o domínio — o suficiente para
  87     correlacionar um envio numa investigação, sem registrar o dado pessoal.
  88     Entradas sem `@` são mascaradas por inteiro."""
! 89     if not email:
! 90         return ""
! 91     local, separator, domain = email.partition("@")
! 92     if not separator:
! 93         return "***"
! 94     return f"{local[:1]}***@{domain}"
  95 
  96 
  97 def _post_with_retry(payload: ItineraryNotification, masked: str) -> requests.Response:
  98     """POST no webhook com timeout explícito (`N8N_TIMEOUT`) e retry limitado
```


---


Lines 101-115

```python
  101     Repete no máximo `_MAX_RETRIES` vezes, apenas em erros de transporte
  102     transitórios. Erros de status HTTP são tratados pelo chamador
  103     (`raise_for_status`); o esgotamento das tentativas propaga a última
  104     exceção."""
! 105     headers = {"Content-Type": "application/json"}
! 106     if WEBHOOK_TOKEN:
! 107         headers[TOKEN_HEADER] = WEBHOOK_TOKEN
  108 
! 109     for attempt in range(_MAX_RETRIES + 1):
! 110         try:
! 111             return requests.post(
  112                 WEBHOOK_URL,
  113                 json=payload.model_dump(),
  114                 headers=headers,
  115                 timeout=N8N_TIMEOUT,
```


---


Lines 113-129

```python
  113                 json=payload.model_dump(),
  114                 headers=headers,
  115                 timeout=N8N_TIMEOUT,
  116             )
! 117         except _RETRYABLE_HTTP_ERRORS as exc:
! 118             if attempt >= _MAX_RETRIES:
! 119                 logger.warning(
  120                     "n8n webhook: %s — %d tentativas sem sucesso (destinatário %s)",
  121                     type(exc).__name__, attempt + 1, masked,
  122                 )
! 123                 raise
! 124             wait = _BACKOFF_BASE * (2**attempt)
! 125             logger.warning(
  126                 "n8n webhook: %s — nova tentativa %d/%d em %.1fs (destinatário %s)",
  127                 type(exc).__name__, attempt + 1, _MAX_RETRIES, wait, masked,
  128             )
  129             # Cada retry é uma linha pontual na trilha (T05); o resultado final
```


---


Lines 127-138

```python
  127                 type(exc).__name__, attempt + 1, _MAX_RETRIES, wait, masked,
  128             )
  129             # Cada retry é uma linha pontual na trilha (T05); o resultado final
  130             # (ok/erro + latência) é gravado por `send_itinerary`.
! 131             audit.try_record(
  132                 run_id_var.get(), _AUDIT_STEP, "tool", "retry", error=type(exc).__name__
  133             )
! 134             time.sleep(wait)
  135 
  136 
  137 def send_itinerary(payload: ItineraryNotification) -> NotificationResult:
  138     """Envia o roteiro ao webhook do n8n e devolve o desfecho.
```


---


Lines 139-165

```python
  139 
  140     Nunca levanta: uma falha de rede, um status HTTP de erro ou a ausência de
  141     configuração viram um `NotificationResult`. O `.md` gerado permanece em
  142     `output/` em qualquer cenário."""
! 143     masked = mask_email(payload.recipient)
  144 
! 145     if not WEBHOOK_URL:
  146         # Degradação silenciosa e documentada: sem a variável de ambiente, a
  147         # integração simplesmente não existe para esta execução.
! 148         logger.info("n8n_not_configured", extra={"recipient": masked})
! 149         return NotificationResult(
  150             status="not_configured",
  151             detail="N8N_WEBHOOK_URL não configurada.",
  152         )
  153 
! 154     run_id = run_id_var.get()
! 155     start = time.perf_counter()
! 156     try:
! 157         response = _post_with_retry(payload, masked)
! 158         response.raise_for_status()
! 159     except RequestException as exc:
! 160         duration_ms = (time.perf_counter() - start) * 1000
! 161         logger.warning(
  162             "n8n_webhook_failed",
  163             extra={
  164                 "recipient": masked,
  165                 "error": type(exc).__name__,
```


---


Lines 165-179

```python
  165                 "error": type(exc).__name__,
  166                 "duration_ms": round(duration_ms, 1),
  167             },
  168         )
! 169         audit.try_record(
  170             run_id, _AUDIT_STEP, "tool", "error", duration_ms, type(exc).__name__
  171         )
! 172         return NotificationResult(status="failed", detail=type(exc).__name__)
  173 
! 174     duration_ms = (time.perf_counter() - start) * 1000
! 175     logger.info(
  176         "n8n_webhook_sent",
  177         extra={
  178             "recipient": masked,
  179             "status_code": response.status_code,
```


---


Lines 179-185

```python
  179             "status_code": response.status_code,
  180             "duration_ms": round(duration_ms, 1),
  181         },
  182     )
! 183     audit.try_record(run_id, _AUDIT_STEP, "tool", "ok", duration_ms)
! 184     return NotificationResult(status="sent")
```


---



## itinerai_agent/utils/validation&#46;py

Lines 128-136

```python
  128 
  129     Determinístico e sem rede, no mesmo espírito das demais regras deste módulo:
  130     não verifica se a caixa existe, apenas se o formato justifica a chamada
  131     externa."""
! 132     return bool(_EMAIL_PATTERN.match(text.strip()))
  133 
  134 
  135 def contains_url(text: str) -> bool:
  136     """Indica se o texto contém uma URL ou link."""
```


---


