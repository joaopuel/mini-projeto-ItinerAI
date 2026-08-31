# Investigação de execuções reais com os dois sinais

Reconstrução de execuções reais do ItinerAI cruzando os **logs estruturados**
(T04/#15) com a **trilha de auditoria** (T05/#16), conforme o §4.6. Produzida na
T06/#17.

| | |
| --- | --- |
| **Execuções analisadas** | 3 turnos reais, 2 conversas |
| **Data** | 2026-08-31, 05:29–05:33 UTC |
| **Ambiente** | Windows 11, Python 3.12.9, `openai/gpt-oss-120b` na Groq |
| **Chave de correlação** | `run_id` (UUID por turno) |

| Turno | `run_id` | Desfecho | Total |
| --- | --- | --- | --- |
| **T1 — busca** | `81579be0` | 12 atrações encontradas, agente pede a duração | 9883,4 ms |
| **T2 — roteiro** | `9ec40ebb` | `.md` gravado, envio por e-mail recusado | 15059,7 ms |
| **T3 — erro** | `c5f84813` | falha de rede na Wikipédia, degradação amigável | 2898,5 ms |

**Origem dos dados: todos reais.** T1 e T2 são uma conversa comum. T3 é uma falha
**induzida de forma declarada** — ver §6.1. Nenhum número foi estimado: todos vêm
dos arquivos de evidência abaixo.

### Arquivos de evidência

Os dois sinais vivem em arquivos **não versionados** (`logs/itinerai.log`,
`itinerai_audit.db`), então as cópias abaixo tornam a análise conferível linha a
linha:

| Arquivo | Conteúdo |
| --- | --- |
| [`evidencias/run-81579be0-log.jsonl`](evidencias/run-81579be0-log.jsonl) | log estruturado do T1 |
| [`evidencias/run-81579be0-audit.txt`](evidencias/run-81579be0-audit.txt) | trilha de auditoria do T1 |
| [`evidencias/run-9ec40ebb-log.jsonl`](evidencias/run-9ec40ebb-log.jsonl) | log estruturado do T2 |
| [`evidencias/run-9ec40ebb-audit.txt`](evidencias/run-9ec40ebb-audit.txt) | trilha de auditoria do T2 |
| [`evidencias/run-c5f84813-log.jsonl`](evidencias/run-c5f84813-log.jsonl) | log estruturado do T3 |
| [`evidencias/run-c5f84813-audit.txt`](evidencias/run-c5f84813-audit.txt) | trilha de auditoria do T3 |

Os `.jsonl` saíram de `grep <run_id> logs/itinerai.log`; os `.txt`, de
`python show_audit.py <run_id>`.

---

## 1. Os dois sinais e a chave de correlação

| | Sinal 1 — logs estruturados (T04) | Sinal 2 — trilha de auditoria (T05) |
| --- | --- | --- |
| Onde | `logs/itinerai.log` (JSON, 1 evento por linha) | `itinerai_audit.db`, tabela `execution_audit` |
| Responde | **o que aconteceu, e em que ordem** | **quanto custou cada passo** |
| Granularidade | evento (`node_start`, `routing_decision`, `llm_decision`, `page_fetched`…) | passo executado (nó, tool ou turno) |
| Campos-chave | `event`, `node`, `router`, `decision`, `duration_ms` | `step`, `step_type`, `status`, `duration_ms`, `error` |
| Escrita | `logging` da stdlib, handler JSON | `sqlite3` da stdlib, `INSERT` best-effort |

A chave que os une é o **`run_id`**: um UUID gerado por turno em `_run_turn`
(`main.py:126`) e propagado por dois caminhos complementares:

1. **`AgentState.run_id`** — lido pelos decorators `_logged_node` e
   `_logged_router` em `nodes.py`;
2. **um `contextvars.ContextVar`** (`run_id_var`) — necessário porque o fan-out
   da busca roda os dois ramos em threads de um `ThreadPoolExecutor`. O
   `copy_context()` do LangGraph leva o `ContextVar` junto, então até as chamadas
   profundas em `tools.py` (retries da Wikipédia, extração via LLM) saem
   carimbadas com o `run_id` correto.

Sem o segundo caminho, os passos mais interessantes desta análise — os
`wikipedia_fetch` e os `llm_extraction` — apareceriam órfãos.

---

## 2. Trecho real do log estruturado (T1 — `81579be0`)

```json
{"timestamp": "2026-08-31T05:29:34.506082Z", "event": "run_start", "run_id": "81579be0-…", "messages": 1, "has_destination": false}
{"timestamp": "2026-08-31T05:29:34.513077Z", "event": "routing_decision", "router": "route_entry", "decision": "validate_input"}
{"timestamp": "2026-08-31T05:29:34.515036Z", "event": "node_end", "node": "validate_input", "duration_ms": 0.2}
{"timestamp": "2026-08-31T05:29:34.529036Z", "event": "routing_decision", "router": "route_after_validation", "decision": "persist_memory"}
{"timestamp": "2026-08-31T05:29:36.094082Z", "event": "llm_decision", "node": "call_llm", "outcome": "tool_calls", "tools": ["search_tourist_attractions"]}
{"timestamp": "2026-08-31T05:29:36.159091Z", "event": "search_dispatched", "node": "dispatch_search", "destination": "Lisboa"}
{"timestamp": "2026-08-31T05:29:36.171081Z", "event": "node_start", "node": "fetch_destination_page"}
{"timestamp": "2026-08-31T05:29:36.172081Z", "event": "node_start", "node": "fetch_tourism_page"}
{"timestamp": "2026-08-31T05:29:37.102914Z", "event": "page_fetched", "node": "fetch_tourism_page", "kind": "tourism", "found": false, "unavailable": false, "attraction_count": 0}
{"timestamp": "2026-08-31T05:29:43.865667Z", "event": "page_fetched", "node": "fetch_destination_page", "kind": "destination", "found": true, "unavailable": false, "attraction_count": 12}
{"timestamp": "2026-08-31T05:29:43.878694Z", "event": "search_merged", "node": "merge_pages", "chosen": "destination", "found": true, "unavailable": false, "attraction_count": 12}
{"timestamp": "2026-08-31T05:29:44.378834Z", "event": "llm_decision", "node": "call_llm", "outcome": "plain_answer"}
{"timestamp": "2026-08-31T05:29:44.402671Z", "event": "run_end", "run_id": "81579be0-…", "last_message_type": "AIMessage", "itinerary_ready": false, "duration_ms": 9883.4}
```

> Trecho abreviado para leitura: os campos `level` e `logger` e os `node_start`
> de nós já representados foram omitidos, e o `run_id` aparece truncado. O
> arquivo de evidência tem as linhas **íntegras**.

### Sobre dados sensíveis

**Nenhuma omissão foi necessária.** Os nós registram apenas metadados —
contagens, nomes de tools, decisões, booleanos e o destino. Nunca entram no log:
o texto do usuário, a resposta do LLM, a lista de atrações ou o itinerário. Como
defesa em profundidade, o `JsonFormatter` ainda redige o valor de `GROQ_API_KEY`
da string final e trunca strings acima de 500 caracteres; e-mails de
destinatário passam por `mask_email` antes de chegar ao log.

O único dado de produto presente é o destino (`"Lisboa"`), deliberadamente
mantido: sem ele seria impossível correlacionar uma busca ao seu resultado.

---

## 3. Trecho real da trilha de auditoria (mesmo `run_id`)

Saída literal de `python show_audit.py 81579be0-957f-49f8-ab8e-12abdf6e917e`:

```text
Trilha de auditoria — run_id 81579be0-957f-49f8-ab8e-12abdf6e917e

  #  passo                    tipo   status            ms
---------------------------------------------------------
  1  validate_input           node   ok               0.2
  2  persist_memory           node   ok               0.2
  3  call_llm                 node   ok            1552.3
  4  dispatch_search          node   ok               0.2
  5  wikipedia_fetch          tool   ok             918.4
  6  fetch_tourism_page       node   ok             930.7
  7  wikipedia_fetch          tool   ok            1947.4
  8  llm_extraction           tool   ok            5726.4
  9  fetch_destination_page   node   ok            7695.1
 10  merge_pages              node   ok               0.8
 11  call_llm                 node   ok             489.2
 12  graph_invoke             turn   ok            9883.4

Passo mais lento: fetch_destination_page (7695.1 ms)
Total (turno): 9883.4 ms
12 passos · 0 retries · 0 fallbacks · 0 erros
```

---

## 4. Reconstrução do fluxo

### 4.1 T1 (`81579be0`) — a busca

O `run_start` diz `messages: 1, has_destination: false`: conversa nova, usuário
digitou apenas `Lisboa`.

1. **`route_entry` → `validate_input`** — o caminho normal; não havia
   `recipient_email` no estado, então o desvio para `notify_recipient` não se
   aplicou. Validação em **0,2 ms**, sem bloqueio.
2. **`route_after_validation` → `persist_memory`** (0,2 ms). Repare que **não há
   evento `memory_persisted`**: o nó rodou, mas o destino ainda não estava no
   estado e a gravação foi pulada — é a proteção que impede uma conversa nova de
   sobrescrever a última viagem com um registro vazio.
3. **`call_llm`** (1552,3 ms) decide chamar `search_tourist_attractions`
   (`llm_decision.outcome = "tool_calls"`).
4. **`route_after_llm` → `dispatch_search`** — a saída do roteador que desvia a
   busca do `call_tools` para o fan-out. `search_dispatched` confirma o destino
   extraído: `"Lisboa"`.
5. **Fan-out.** `fetch_destination_page` inicia em `36.171081` e
   `fetch_tourism_page` em `36.172081` — **1 ms de diferença**, prova de que
   rodam no mesmo superstep, não em sequência.
   - `Tourism in Lisboa` **não existe** → `found: false`, 0 atrações, 930,7 ms;
   - `Lisboa` → `found: true`, **12 atrações**, 7695,1 ms.
6. **`merge_pages`** (0,8 ms) escolhe `destination`, já que o ramo prioritário
   veio vazio — decisão 100% determinística, sem LLM.
7. **`call_llm`** (489,2 ms) responde em texto (`plain_answer`): pede a duração
   da viagem, porque `num_days` ainda era desconhecido.
8. **`route_after_llm` → `__end__`**, com `itinerary_ready: false`.

### 4.2 T2 (`9ec40ebb`) — o roteiro

O usuário respondeu `3 dias`. Agora `persist_memory` **grava**
(`memory_persisted` com `has_num_days: false, completed: false` — a duração
ainda não estava no estado nesse instante do turno). `call_llm` (493,7 ms) chama
`build_itinerary` com `{"destination": "Lisboa", "num_days": 3}`, `call_tools`
executa a tool em 1789,8 ms, o `.md` é gravado, e o `call_llm` final (12687,7 ms)
anuncia o arquivo. `run_end` traz `itinerary_ready: true`.

**Fora do grafo**, 27 segundos depois, o usuário recusou o envio por e-mail. O
desfecho virou o evento `notification_declined` e uma linha de auditoria de
mesmo nome — **carimbados com o `run_id` do turno que gerou o roteiro**. Sem
esse registro, "o usuário recusou" seria indistinguível de "o agente nunca
perguntou", e é justamente a recusa que evidencia o limite de autonomia do §4.5.

---

## 5. Latência: onde o tempo foi

### 5.1 O que o cruzamento revela que nenhum sinal isolado revela

O log encerra o T1 dizendo que `fetch_destination_page` levou **7695,1 ms** — 78%
do turno. É a resposta certa para "qual nó foi o gargalo", e é onde a
investigação pararia com apenas o sinal 1.

A trilha de auditoria **decompõe esse nó**, porque `tools.py` audita os passos
internos:

| Passo dentro de `fetch_destination_page` | ms | Fatia do nó |
| --- | ---: | ---: |
| `wikipedia_fetch` (rede: GET + parsing) | 1947,4 | 25,3% |
| `llm_extraction` (extração das atrações pelo LLM) | 5726,4 | **74,4%** |
| restante do nó | 21,3 | 0,3% |
| **total** | **7695,1** | 100% |

**O gargalo não é a Wikipédia — é a extração pelo LLM.** Sozinhos, os 5726,4 ms
representam **58% do turno inteiro**. Essa conclusão é impossível de alcançar só
com os logs, que não instrumentam o interior do nó, e impossível só com a
auditoria, que não diz qual foi o fluxo nem por que aquele ramo foi escolhido.

O mesmo padrão aparece no T2: `build_itinerary` custou 1789,8 ms, dos quais
**1776,1 ms são o `llm_extraction`** do agrupamento por proximidade. Sobram
13,7 ms para agrupar, distribuir pelos dias e **gravar o arquivo `.md`** — 0,8%
do tempo da tool.

### 5.2 O paralelismo do fan-out, medido

| | ms |
| --- | ---: |
| `fetch_tourism_page` | 930,7 |
| `fetch_destination_page` | 7695,1 |
| Soma (se fosse sequencial) | 8625,8 |
| Relógio de parede real (`36.171081` → `43.865667`) | **7694,6** |
| **Economia medida** | **931,2** |

A economia equivale, dentro de 0,5 ms, ao ramo mais curto inteiro — exatamente o
que se espera de dois ramos sobrepostos. É a evidência empírica de que a
paralelização do §4.2 funciona.

### 5.3 A anomalia do T2 — 12,7 s para anunciar um arquivo

| Passo do T2 | ms | Fatia do turno |
| --- | ---: | ---: |
| `validate_input` + `persist_memory` | 8,9 | 0,1% |
| `call_llm` (decide chamar a tool) | 493,7 | 3,3% |
| `call_tools` (monta o roteiro e grava o `.md`) | 1799,7 | 12,0% |
| **`call_llm` (mensagem final)** | **12687,7** | **84,2%** |
| **total** | **15059,7** | 100% |

O agente gasta **7 vezes mais tempo anunciando o arquivo do que criando-o**. E o
conteúdo dessa mensagem é, por design do projeto, apenas o nome do arquivo
gerado — o roteiro **não** é exibido no terminal.

A causa provável está na entrada, não na saída: nesse ponto o histórico já
carrega a `ToolMessage` da busca com as 12 atrações e o resultado do
`build_itinerary`, então o modelo processa um contexto grande para produzir uma
frase curta. É o passo mais caro das três execuções analisadas.

---

## 6. Investigação da execução com erro (T3 — `c5f84813`)

### 6.1 Como a falha foi induzida

Nenhuma das execuções reais anteriores havia falhado: os 354 eventos anteriores
do log não continham um único `node_error`, `run_error`, `retry` ou
`unavailable: true`. A falha foi então **provocada de forma declarada**,
reduzindo o timeout das requisições à Wikipédia:

```powershell
$env:WIKIPEDIA_TIMEOUT = '0.001'
python main.py
```

`WIKIPEDIA_TIMEOUT` é uma variável de configuração já existente
(`config.py:22`, padrão 10 s). **Nenhuma linha de código foi alterada** para
produzir esta falha — o que também significa que o caminho exercitado é o
caminho real de produção, não um desvio de teste.

O turno usou o fluxo de **retomada da memória**: `messages: 1`,
`has_destination: true`, `memory_persisted` com `has_num_days: true`.

### 6.2 O caminho da investigação

**Sintoma observável:** o agente respondeu que houve um problema técnico ao
acessar a Wikipédia. Nada mais — nenhum traceback, nenhum erro no terminal.

**Passo 1 — o log diz *o que* houve.** Procurando pela marca de indisponibilidade:

```json
{"event": "page_fetched", "node": "fetch_destination_page", "found": false, "unavailable": true, "attraction_count": 0}
{"event": "page_fetched", "node": "fetch_tourism_page",     "found": false, "unavailable": true, "attraction_count": 0}
{"event": "search_merged", "node": "merge_pages", "chosen": "none", "found": false, "unavailable": true}
```

`unavailable: true` distingue **"a Wikipédia não respondeu"** de **"o destino não
foi encontrado"** — dois desfechos com a mesma aparência para o usuário e causas
opostas. É essa flag que o `AGENT_SYSTEM_PROMPT` usa para escolher entre "tente
de novo" e "não encontrei informações desse destino".

**Passo 2 — o log diz *por quê*.** Os `WARNING` de `tools.py`, carimbados com o
mesmo `run_id` graças ao `ContextVar`:

```text
05:33:18.240993  Wikipédia .../Tourism_in_Lisboa: ConnectTimeout — nova tentativa 1/2 em 0.5s
05:33:18.241820  Wikipédia .../Lisboa:            ConnectTimeout — nova tentativa 1/2 em 0.5s
05:33:18.770701  Wikipédia .../Lisboa:            ConnectTimeout — nova tentativa 2/2 em 1.0s
05:33:18.771447  Wikipédia .../Tourism_in_Lisboa: ConnectTimeout — nova tentativa 2/2 em 1.0s
05:33:19.800111  Wikipédia .../Tourism_in_Lisboa: ConnectTimeout — 3 tentativas sem sucesso
05:33:19.801111  Wikipédia .../Lisboa:            ConnectTimeout — 3 tentativas sem sucesso
```

**Causa identificada:** `ConnectTimeout`, nos dois ramos, com a política de retry
da T02 esgotada (1 tentativa + 2 repetições, backoff 0,5 s → 1,0 s).

**Passo 3 — a trilha diz *quanto custou*:**

```text
  5  wikipedia_fetch          tool   retry              —  (ConnectTimeout)
  6  wikipedia_fetch          tool   retry              —  (ConnectTimeout)
  7  wikipedia_fetch          tool   retry              —  (ConnectTimeout)
  8  wikipedia_fetch          tool   retry              —  (ConnectTimeout)
  9  wikipedia_fetch          tool   error         1580.4  (ConnectTimeout)
 10  fetch_destination_page   node   ok            1595.8
 11  wikipedia_fetch          tool   error         1578.8  (ConnectTimeout)
 12  fetch_tourism_page       node   ok            1620.6
```

4 retries (2 por ramo) e 2 erros — exatamente o que a política prevê.

### 6.3 O que a investigação concluiu

**A conclusão central: nenhum nó falhou.** Os dois `fetch_*` terminaram
**`ok`**, `graph_invoke` terminou **`ok`**, e o turno fechou normalmente em
2898,5 ms. Isso não é um defeito — é a resiliência da T02 funcionando:
`fetch_page_attractions` captura `RequestException` e degrada para
`unavailable=True` em vez de propagar.

O efeito colateral é que **um incidente de rede completo — 6 requisições
falhadas — é invisível para qualquer observador que olhe só o desfecho.** O
usuário viu uma mensagem educada; o processo não caiu; nenhum alarme disparou.
Os dois sinais são o **único** lugar onde esse incidente existe.

**O custo da falha é quase todo espera deliberada:**

| | ms |
| --- | ---: |
| `wikipedia_fetch` (erro, ramo destino) | 1580,4 |
| Backoff imposto pela política (0,5 s + 1,0 s) | 1500,0 |
| **Rede real, somando as 3 tentativas** | **≈ 80,4** |

Ou seja: **95% do tempo de uma falha de rede é o `sleep` do backoff**, não espera
de rede. Com `WIKIPEDIA_TIMEOUT=0.001` a rede desiste quase instantaneamente,
então o número isola bem a política.

**Falhar é mais barato que funcionar:** 2898,5 ms contra 9883,4 ms do T1 — o
turno com erro foi **3,4× mais rápido** que o equivalente bem-sucedido, porque
não pagou os 5726,4 ms de extração pelo LLM.

### 6.4 Contraste: `found: false` sem `unavailable`

O log guarda um turno mais antigo (`c29555a4`, 2026-08-30) em que
`merge_pages` também registrou `chosen: "none"` e `found: false` — mas com
`unavailable: false`. Mesmo desfecho aparente, causa oposta: ali a Wikipédia
respondeu e não havia conteúdo; aqui ela não respondeu. Distinguir os dois casos
depende inteiramente de o sinal carregar a flag.

---

## 7. O que a investigação revelou sobre os próprios sinais

Usar os sinais a sério expôs três limitações deles:

### 7.1 O `run_id` é por turno, não por conversa

A viagem a Lisboa está espalhada por **três identificadores**: `81579be0` (busca),
`9ec40ebb` (roteiro) e a linha `notification_declined`. Não existe chave que os
una — reconstruí a conversa ordenando por timestamp e lendo `messages` e
`has_destination` do `run_start`. Para uma conversa longa, ou com execuções
concorrentes, isso não escala.

### 7.2 `format_audit_trail` perde o total quando há notificação

O T2 é o único dos três cuja saída **não** traz a linha `Total (turno)`. A causa
está em `audit.py:199-200`: `turn_ms` é reatribuído a cada linha de
`step_type == "turn"`, e a última do T2 é `notification_declined`, cujo
`duration_ms` é `NULL`. Ela sobrescreve os 15059,7 ms do `graph_invoke`, e o
guard `if turn_ms is not None` suprime a linha.

Verificável nos três arquivos: T1 e T3 mostram o total, T2 não.

### 7.3 O "passo mais lento" ignora passos que falharam

`format_audit_trail` só considera linhas com `status == "ok"` no cálculo do
gargalo (`audit.py:201-202`). No T3 o passo reportado é `fetch_tourism_page`
(1620,6 ms), enquanto os `wikipedia_fetch` em `error` (1580,4 e 1578,8 ms) ficam
de fora. Aqui os números quase coincidem, mas numa execução em que o passo
falhado dominar o tempo, o gargalo será reportado errado — justamente na
investigação em que mais importa.

---

## 8. Conclusão e ações

### Conclusão

Os dois sinais cumprem o §4.6, e o valor real está no **cruzamento**, não em cada
um. O log responde *o que aconteceu e em que ordem*; a auditoria responde *quanto
custou*. Duas conclusões desta investigação seriam inalcançáveis com um só:

1. O gargalo do fluxo de busca **não é a rede** — é a extração pelo LLM (5726,4 de
   7695,1 ms do nó; 58% do turno). O log aponta o nó; só a auditoria abre o nó.
2. Um incidente de rede completo pode terminar com **todos os passos `ok`**. Sem
   os dois sinais, as 6 requisições falhadas do T3 não teriam deixado rastro
   algum.

### Ações

| # | Ação | Estado |
| --- | --- | --- |
| 1 | Corrigir o `turn_ms` de `format_audit_trail` para ignorar linhas `turn` sem duração (§7.2) | **Proposta.** Defeito real, de 1 linha; merece tarefa própria com teste, por ser código e não documentação. |
| 2 | Incluir passos `error` no cálculo do gargalo, ou exibi-los à parte (§7.3) | **Proposta.** Hoje o número engana exatamente na investigação de falhas. |
| 3 | Adicionar um `conversation_id` ao lado do `run_id` (§7.1) | **Proposta.** Sem ele, reconstruir uma conversa depende de ordenar por timestamp na mão. |
| 4 | Atacar a latência da extração pelo LLM — cache por página, ou extração só do ramo escolhido | **Proposta.** Hoje as duas páginas são sempre extraídas; o ramo descartado custou 5726,4 ms em um turno cujo total foi 9883,4 ms. |
| 5 | Instrumentar os passos internos das tools, não só os nós | **Aplicada** (T05/#16) — foi o que permitiu a conclusão 1. |

---

## Anexo — comandos usados

Coleta das execuções:

```powershell
python main.py                             # T1 e T2 (conversa normal)
$env:WIKIPEDIA_TIMEOUT = '0.001'           # T3 (falha induzida)
python main.py
```

Extração das evidências (Git Bash, com o `.venv`):

```bash
grep <run_id> logs/itinerai.log > docs/evidencias/run-<run_id>-log.jsonl
.venv/Scripts/python.exe show_audit.py <run_id> > docs/evidencias/run-<run_id>-audit.txt
```

Os `run_id` saem de qualquer linha do log; os eventos `run_start` e `run_end`
delimitam cada turno.
