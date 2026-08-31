# Automação low-code — envio do roteiro por e-mail (n8n)

Documentação do fluxo low-code do ItinerAI (§4.9): gatilho, nós, saída
observável e evidências de execução. As **instruções resumidas de reprodução**
ficam no [`README.md`](../../README.md#automação-low-code-n8n) da raiz, como o
enunciado exige; aqui está o detalhe.

| Arquivo | O que é |
| --- | --- |
| [`n8n-workflow.json`](n8n-workflow.json) | O workflow, pronto para importar. Sem credenciais. |
| [`payload-exemplo.json`](payload-exemplo.json) | Payload de exemplo para testar o webhook com `curl`. |

---

## Por que a lógica principal permanece na aplicação

O §4.9 é explícito: a ferramenta visual deve atuar como **apoio à orquestração
ou integração**, não como a aplicação. Aqui a divisão é literal.

| Fica no agente (Python) | Fica no n8n |
| --- | --- |
| Busca das atrações na Wikipédia (fan-out paralelo, retry, fallback) | — |
| Agrupamento por proximidade e distribuição pelos dias | — |
| Geração do arquivo `.md` em `output/` | — |
| Pergunta de aprovação (s/n) e validação do e-mail por regex | — |
| Timeout, retry com backoff e fallback da chamada | — |
| Logs estruturados, `run_id` e trilha de auditoria | — |
| — | Receber o POST, conferir o token e o formato do payload |
| — | Converter o markdown em HTML e despachar o e-mail |

O n8n não conhece a Wikipédia, não decide nada sobre a viagem e não guarda
estado. Ele recebe um payload pronto e faz uma única coisa: mandar o e-mail. Se
o fluxo for removido, o agente continua funcionando por inteiro — apenas deixa
de oferecer o envio.

---

## O fluxo

### Gatilho

Nó **`Webhook`**, `POST /webhook/itinerai-email`, autenticado por *Header Auth*
(credencial `ItinerAI Webhook Token`, header `X-ItinerAI-Token`). O n8n valida o
token **antes** de o fluxo começar: uma chamada sem token recebe `403` e não
gera execução nenhuma.

`responseMode` é `responseNode`, o que permite ao fluxo escolher explicitamente
o status e o corpo da resposta.

### Payload aceito

Espelha o modelo pydantic `ItineraryNotification`
(`itinerai_agent/utils/notifications.py`):

| Campo | Tipo | Uso no fluxo |
| --- | --- | --- |
| `destination` | string | assunto do e-mail |
| `num_days` | int | assunto do e-mail |
| `recipient` | string | destinatário |
| `markdown` | string | corpo do e-mail (convertido para HTML) |
| `run_id` | string | devolvido na resposta, correlaciona com os logs do agente |

### Nós

| # | Nó | O que faz |
| --- | --- | --- |
| 1 | `Webhook` | Gatilho autenticado; recebe o POST |
| 2 | `Validar payload` | IF: os quatro campos obrigatórios presentes e `recipient` com formato de e-mail |
| 3 | `Markdown para HTML` | Converte o roteiro para HTML, para o e-mail chegar formatado |
| 4 | `Enviar email` | SMTP (credencial `ItinerAI SMTP`); saída de erro separada |
| 5 | `Responder OK` | `200` + `{"status":"sent","run_id":…}` |
| 6 | `Responder payload invalido` | `400` + motivo |
| 7 | `Responder falha de envio` | `502` + motivo |

```
Webhook → Validar payload ─┬─(true)→ Markdown para HTML → Enviar email ─┬─(ok)→ Responder OK          200
                           │                                            └─(erro)→ Responder falha    502
                           └─(false)──────────────────────────────────────────→ Responder invalido   400
```

### Saída observável

O **e-mail com o roteiro**, formatado a partir do markdown. Cada disparo também
aparece na aba *Executions* do n8n.

### Respostas

| Situação | HTTP | Quem responde |
| --- | --- | --- |
| E-mail enviado | `200` | nó `Responder OK` |
| Payload inválido | `400` | nó `Responder payload invalido` |
| Falha no SMTP | `502` | nó `Responder falha de envio` |
| Token ausente ou errado | `403` | o próprio n8n, antes do fluxo |

Do lado da aplicação, qualquer resposta diferente de `2xx` vira
`NotificationResult(status="failed")` — o turno não quebra e o `.md` segue em
`output/`.

---

## Como testar o webhook isoladamente

Com o workflow **ativo**, usando o payload versionado:

```bash
read -s ITINERAI_TOKEN          # cola o token; não fica na tela nem no histórico
export ITINERAI_TOKEN

curl -i -X POST "https://<sua-instancia>/webhook/itinerai-email" \
  -H "Content-Type: application/json" \
  -H "X-ItinerAI-Token: $ITINERAI_TOKEN" \
  --data-binary @docs/low-code/payload-exemplo.json
```

> A *Production URL* (`/webhook/…`) exige o workflow ativo e responde sempre. A
> *Test URL* (`/webhook-test/…`) só responde enquanto *Listen for test event*
> está ligado, e a uma única requisição.

---

## Segurança

- O `n8n-workflow.json` versionado **não contém segredo algum**: as duas
  credenciais entram por referência de *nome* e são criadas dentro do n8n.
- O token do webhook fica no `.env` local (que está no `.gitignore`) e na
  credencial do n8n — nunca no repositório.
- **O e-mail do destinatário nunca é registrado em texto puro.** Logs e trilha
  de auditoria recebem só a versão mascarada (`j***@exemplo.com`), via
  `mask_email` em `notifications.py`.

---

## Evidências de execução

> **A preencher com as capturas de tela** (dados pessoais omitidos):
>
> - `fluxo-n8n.png` — o workflow montado no editor do n8n, com os 7 nós
>   conectados.
> - `execucao-n8n.png` — uma execução bem-sucedida na aba *Executions*, com o
>   caminho verde até o `Responder OK`.
> - `email-recebido.png` — o e-mail na caixa de entrada, com o roteiro
>   formatado.
>
> Depois de adicionar as imagens nesta pasta, referencie-as aqui com
> `![descrição](nome-do-arquivo.png)`.
