# ItinerAI

## Visão geral do produto

ItinerAI é um agente de IA capaz de criar itinerários de viagem. Toda a
interação com o agente acontece via terminal — **não há interface gráfica**.

Funcionalidades do agente:

- Validar a mensagem do usuário antes de processá-la: bloquear tentativas de
  prompt injection, mensagens em scripts não-latinos (mandarim/híndi) e
  URLs/links enviados pelo usuário, respondendo com um aviso em português.
- Coletar os campos obrigatórios para montar a viagem, verificando-os em
  sequência — 1º o destino, 2º a duração da viagem em dias — e pedindo ao
  usuário **uma informação por vez**, na ordem, quando alguma faltar, antes de
  pesquisar ou montar o roteiro. Essa coleta é conduzida pelo
  `AGENT_SYSTEM_PROMPT` (não faz parte da validação de segurança por regex de
  `validation.py`).
- Pesquisar pontos turísticos do destino informado (via Wikipédia).
- Montar um itinerário dia a dia, agrupando atrações próximas para reduzir
  deslocamento.
- Gerar um arquivo `.md` com o itinerário em `output/`. **O roteiro não é
  exibido no terminal** — o agente apenas informa o nome do arquivo criado.
- Manter uma memória persistente da última viagem (destino e duração em dias)
  em SQLite, salva logo após a validação. Numa nova execução, o agente
  **mostra** a última viagem salva e oferece **retomá-la** (se ficou incompleta,
  ex.: após uma falha na busca/geração) ou **refazê-la** (se já concluída).

Não introduza funcionalidades, integrações ou tecnologias além das descritas
neste documento sem alinhar antes com o usuário.

## Stack técnica

- **Python 3.12.9**
- **LangGraph** — orquestração do agente como um grafo de estados.
- **pydantic** — definição do estado do grafo e de todos os modelos de dados
  (ex.: pontos turísticos, dias do itinerário).
- **Groq** — LLM do agente e da extração via `langchain-groq`. Modelo e
  temperatura do agente são configuráveis por `GROQ_MODEL` / `GROQ_TEMPERATURE`
  (T03/#14; ver "Configuração de ambiente"), com padrão `openai/gpt-oss-120b` /
  `0.7`. O `llama-3.1-8b-instant` original foi desligado pela Groq em
  16/08/2026; `openai/gpt-oss-120b` está na camada gratuita (limites: 30
  req/min, 8K tokens/min, 1K req/dia, 200K tokens/dia).
- Autenticação com a Groq via variável de ambiente `GROQ_API_KEY` (nunca
  hardcode a chave; carregue de `.env`/ambiente).
- **requests + beautifulsoup4** — busca e parsing de páginas da Wikipédia,
  usadas como fonte de dados pelas tools (ex.: busca de pontos turísticos).

## Arquitetura do grafo (tool-calling)

O agente segue um loop de tool-calling estilo ReAct, não um pipeline fixo de
nós por etapa:

- `validate_input` é o nó de entrada do grafo (`START → validate_input`):
  valida a última mensagem do usuário e, via aresta condicional
  (`route_after_validation`), segue para `persist_memory` quando a entrada é
  válida ou vai direto para `END` (com a mensagem de recusa já inserida) quando
  viola uma regra. Ver "Validação de entrada" abaixo.
- `persist_memory` roda logo após a validação (só no caminho válido) e salva os
  dados da viagem coletados até aqui na memória persistente, antes das buscas
  que podem falhar; em seguida segue para `call_llm`. Ver "Memória persistente"
  abaixo.
- `call_llm` invoca o LLM com as tools de `tools.py` vinculadas via
  `bind_tools`; também recupera as tool calls que o modelo eventualmente
  "vaza" como texto (ver "Robustez em tool-calling" abaixo).
- Uma aresta condicional (`route_after_llm`) tem **3 saídas**: sem tool call →
  `END` (condição de parada); tool call `search_tourist_attractions` → o
  fan-out da busca (`dispatch_search`); qualquer outra tool (hoje só
  `build_itinerary`) → `call_tools`.
- `call_tools` executa `build_itinerary` (e outras tools que venham a existir) e
  volta para `call_llm`. **A busca de atrações não passa por `call_tools`** — é
  sempre roteada para o fan-out.
- `dispatch_search → (fetch_tourism_page ∥ fetch_destination_page) →
  merge_pages` é a **paralelização simples** exigida pelo §4.2 (ver
  "Paralelização da busca da Wikipédia" abaixo). `merge_pages` volta para
  `call_llm`, que formula a resposta final (inclusive "não encontrado").

Para novas *ferramentas*, siga o padrão: implementar como tool em `tools.py` e
registrá-la na lista vinculada ao LLM em `nodes.py`, roteando por `call_tools`
— sem criar nós fixos por etapa. A **exceção deliberada** é a paralelização do
§4.2: a busca da Wikipédia foi quebrada em nós fixos de fan-out/fan-in
justamente porque o requisito é sobre a *topologia do grafo*, não sobre a
ferramenta. `search_tourist_attractions` continua registrada (é o que o
`bind_tools` inspeciona) e existe como especificação sequencial em `tools.py`.

## Validação de entrada (`validation.py`)

Antes de a mensagem do usuário chegar ao LLM, o nó `validate_input` a inspeciona
e bloqueia três tipos de entrada, sempre respondendo com uma mensagem
informativa em português (e sem acionar nenhuma tool):

1. **Prompt injection** (ex.: "ignore as instruções anteriores").
2. **Idioma não suportado** — mensagens em scripts não-latinos: mandarim (CJK) e
   híndi (devanágari).
3. **URLs/links** enviados pelo usuário — o agente nunca os acessa (a fonte de
   dados é sempre a Wikipédia, via as tools).

Regras de design (não remover sem alinhar):

- **Detecção 100% por regex, sem nenhuma chamada ao LLM.** A validação precisa
  ser determinística, barata e previsível, sem sobrecarregar o modelo nem
  depender do julgamento dele.
- Os padrões de **prompt injection** cobrem os 6 idiomas mais falados:
  português, inglês, espanhol, francês, mandarim e híndi.
- O **filtro de idioma** barra apenas scripts não-latinos (mandarim/híndi), que
  são 100% confiáveis por regex. Inglês, espanhol e francês **não** são barrados
  pelo filtro de idioma (compartilham palavras com o português → risco de falso
  positivo), mas tentativas de injeção nesses idiomas continuam pegas pela regra
  de injeção. Trade-off consciente: mensagens benignas nesses idiomas passam e
  chegam ao LLM.
- A ordem de checagem é injeção → idioma → URL: uma injeção em mandarim/híndi
  recebe a mensagem específica de injeção, não a de idioma.
- Toda a lógica fica em `validation.py` como funções puras
  (`contains_prompt_injection`, `contains_non_latin_script`, `contains_url` e o
  agregador `validate_user_input`); o nó `validate_input` e o roteamento
  (`route_after_validation`) ficam em `nodes.py`. O roteamento não usa novo
  campo de estado: quando reprova, o nó insere uma `AIMessage` e o router a
  detecta para ir a `END`. `AgentState` permanece inalterado.

## Memória persistente (`memory.py`)

O agente guarda em **SQLite** os dados da última viagem, para poder retomá-la
numa nova execução caso a geração do roteiro falhe. Falhas de rede na Wikipédia
não derrubam mais o processo (ver "Resiliência das integrações" abaixo), mas a
gravação do `.md` e outros erros fora de rede ainda podem — a memória é a rede
de segurança.

Regras de design (não alterar sem alinhar):

- **SQLite via `sqlite3` da stdlib** — sem nova dependência no
  `requirements.txt` e sem LLM/rede. A persistência é determinística, barata e
  previsível, no mesmo espírito da validação por regex.
- **Registro único** ("apenas a última viagem"): a tabela `trip_memory` tem uma
  linha fixa (`id = 1`, garantida por `CHECK (id = 1)`) sobrescrita a cada
  salvamento (upsert). Não é um histórico de várias viagens.
- O que é salvo: `destination`, `num_days`, `completed` (itinerário já gerado?)
  e `updated_at`. Modelado como o pydantic `TripMemory`.
- **Quando salvar:** o nó `persist_memory` salva logo após a validação, no
  início do turno, com os dados acumulados até ali (garante que, antes das
  buscas/roteiro que podem falhar, a viagem já está persistida). `main.py`
  também salva ao fim de cada turno, para capturar o que foi descoberto no
  próprio turno (duração e a conclusão do itinerário). Ambos **só salvam
  quando já há um destino** — do contrário, uma conversa nova (estado ainda
  vazio) sobrescreveria a última viagem com um registro nulo.
- **Retomada/exibição no início:** `main.py` chama `load_trip_memory` na
  abertura e, se houver uma viagem salva com destino, **mostra-a** de forma
  determinística (sem passar pelo LLM) e oferece continuá-la: se estiver
  incompleta (`completed=False`), oferece **retomá-la**; se concluída, oferece
  **refazer** o roteiro. Ao aceitar, pré-preenche o `AgentState`
  (destino/dias) e injeta uma mensagem sintética que reafirma a viagem,
  para o agente refazer a busca e o roteiro sem o usuário redigitar nada. A
  memória não é exposta ao LLM durante a conversa (mantém o modelo fraco leve).
- Funções puras e testáveis (`init_db`, `save_trip_memory`, `load_trip_memory`),
  todas com um `db_path` opcional que cai para `MEMORY_DB_PATH` em tempo de
  chamada. O banco fica na raiz do projeto (`itinerai_memory.db`) e **não é
  versionado**.

## Ferramentas do agente (`tools.py`)

Todas já implementadas e registradas em `nodes.py`:

- `search_tourist_attractions(destination)` — busca na Wikipédia
  (`Tourism in <destino>` → `<destino>`). No grafo roda como fan-out/fan-in
  paralelo (ver "Paralelização da busca da Wikipédia"); a função em `tools.py` é
  a especificação sequencial e o que o `bind_tools` inspeciona. A unidade por
  ramo é `fetch_page_attractions(title, destination, kind)` (fetch com
  timeout/retry + extração; captura só `RequestException` → `found=False`, e
  `unavailable=True` em falha de rede — ver "Resiliência das integrações").
- `build_itinerary(destination, num_days)` — monta o roteiro e **grava o `.md`**
  em `output/`. Agrupa as atrações por proximidade e as distribui pelos
  `num_days` dias (**no máximo 3 atrações por dia**, sem divisão por período do
  dia — cada dia é uma lista simples de atrações); quando há poucas atrações para
  a duração, sinaliza com uma observação e, em último caso, repete lugares
  (revisitas) para não deixar dias vazios. As atrações vêm do estado, injetadas
  em `call_tools`, e ficam **ocultas do modelo via `InjectedToolArg`** — o schema
  exposto ao LLM tem só `destination` e `num_days`. A tool devolve apenas o aviso
  do arquivo criado (o roteiro completo vai para `state.itinerary`, não para o
  terminal).

O nome do arquivo gerado segue o padrão `itinerario-<destino>-<n>-dias.md`; se
já existir, ganha sufixo sequencial no padrão Windows (` (2)`, ` (3)`, …).

## Paralelização da busca da Wikipédia (`nodes.py`)

A busca sequencial de páginas da Wikipédia (`Tourism in <destino>` e, no
fallback, `<destino>`) é modelada como um **fan-out/fan-in no grafo** — a
"paralelização simples" exigida pelo §4.2. Regras de design (não alterar sem
alinhar):

- **`dispatch_search`** é a origem única do fan-out. Extrai `destination` e
  `tool_call_id` da tool call `search_tourist_attractions` e os guarda no
  pydantic `AgentState.pending_search`, para os nós seguintes não reprocessarem
  `messages`.
- **`fetch_tourism_page`** e **`fetch_destination_page`** rodam em paralelo (o
  LangGraph executa nós de um mesmo superstep num `ThreadPoolExecutor`; a I/O de
  rede e a chamada Groq liberam o GIL). Cada um faz fetch + extração via
  `fetch_page_attractions` e escreve **uma chave** (`tourism` / `destination`)
  em `AgentState.page_results`.
- **`page_results`** é `Annotated[dict[str, WikipediaPageResult],
  _merge_page_results]`: o reducer mescla por chave (`{**existing, **new}`).
  Como os dois ramos sempre reescrevem sua própria chave a cada busca, um retry
  do ReAct ou um novo turno sobrescreve tudo — resultados antigos nunca vazam,
  sem precisar de nó de reset.
- **`merge_pages`** é o fan-in e é **100% determinístico, sem LLM**: escolhe a
  página que rendeu atrações, priorizando `Tourism in <destino>`; senão
  `<destino>`; senão `found=False`. Devolve o **mesmo** `TouristAttractionSearchResult`
  (e o mesmo formato de `ToolMessage`, com o `tool_call_id` da busca) que
  `call_tools` produzia antes. A extração (que usa o LLM) fica nos ramos,
  **fora** do nó de consolidação — mantém a "escolha da melhor página"
  determinística.
- Comportamento observável idêntico ao da busca sequencial: mesmas atrações,
  mesmo `source_url`, mesma mensagem de "não encontrado". O custo é 1 chamada a
  mais ao LLM de extração por busca (as duas páginas são sempre extraídas), mas
  em paralelo (sem custo de latência).
- A resiliência de rede (timeout/retry/backoff/log/`unavailable`) fica em
  `fetch_page_attractions` e `_get_wikipedia` — ver "Resiliência das
  integrações" abaixo (T02/#13).
- `main.py` passa `recursion_limit=50` no `graph.invoke` — o fan-out consome
  alguns supersteps a mais por busca.

## Resiliência das integrações (`tools.py`)

Política explícita e determinística de falhas nas integrações externas (T02/#13,
§4.6). Regras de design (não alterar sem alinhar):

- **HTTP da Wikipédia** (`_get_wikipedia`): timeout **configurável** por
  `WIKIPEDIA_TIMEOUT` (em `config.py`, padrão 10s) + **retry limitado** (máx. 2
  tentativas adicionais) com **backoff exponencial** (0,5s → 1,0s). Repete
  **só** em erros de transporte transitórios (`Timeout`, `ConnectionError`);
  erros de status HTTP (incl. 5xx) e o esgotamento das tentativas propagam a
  exceção.
- **Exceções específicas, não `except Exception`**: `fetch_page_attractions`
  captura só `requests.exceptions.RequestException`. Um bug fora de rede volta a
  propagar (falha alto em bug, degrada em rede).
- **`unavailable`**: falha de rede após os retries → `WikipediaPageResult(
  found=False, unavailable=True)`. `merge_pages` propaga para o
  `TouristAttractionSearchResult`, e o `AGENT_SYSTEM_PROMPT` orienta o LLM a
  dizer "problema técnico ao acessar a Wikipédia, tente de novo" — diferente de
  "não encontrei informações do destino" (`found=False` sem `unavailable`).
- **Extração do LLM** (`_invoke_structured`): `_extraction_llm` usa
  `max_retries=2` (retry limitado que o SDK da Groq já faz internamente em erros
  transitórios). O `except Exception` continua (o SDK trata as exceções
  específicas; estreitar exigiria um import de `groq.*` frágil), mas agora
  **registra** cada fallback via `logging` em vez de mascarar.
- **Logging**: `logging.getLogger(__name__)` em `tools.py`; cada tentativa, erro
  e fallback vira `logger.warning`/`logger.info`. Desde a **T04/#15**, esses
  registros fluem pelo handler JSON + arquivo (`logs/itinerai.log`) plugado por
  `logging_config.py` e ganham o `run_id` do turno — ver "Observabilidade /
  logging" abaixo. `itinerai_agent/__init__.py` mantém só o `NullHandler` (a
  aplicação é quem configura o logging).
- **Trilha de auditoria (T05/#16)**: os retries de `_get_wikipedia`, a
  indisponibilidade em `fetch_page_attractions` e os fallbacks de
  `_invoke_structured` também viram linhas em `execution_audit`
  (`status` `retry`/`error`/`fallback`) — ver "Trilha de auditoria" abaixo. Os
  testes unitários da política continuam adiados para a T07/#18. Retry de 5xx
  também não entra (Wikipédia raramente devolve 5xx).

## Observabilidade / logging (`logging_config.py`)

Logs estruturados em JSON, um evento por linha, para arquivo em `logs/`, com um
`run_id` por turno da conversa correlacionando todos os eventos daquele turno
(T04/#15, §4.6 — primeiro dos dois sinais do épico E02; a trilha de auditoria em
SQLite com latência é a T05). Regras de design (não alterar sem alinhar):

- **Somente stdlib** — nenhuma dependência nova no `requirements.txt`. O
  `JsonFormatter` é escrito à mão (mesmo espírito da validação por regex e da
  memória por `sqlite3`): determinístico, barato, previsível.
- **A aplicação configura, a biblioteca não.** `main.py` chama
  `configure_logging()` logo após `load_dotenv()` e **antes** de importar o
  grafo. `itinerai_agent/__init__.py` continua só com o `NullHandler` — quando o
  agente roda pela LangGraph platform (que não passa por `main.py`), os logs são
  absorvidos e o terminal fica limpo (o `run_id` fica `""`).
- **Só arquivo por padrão** (`logs/itinerai.log`, via `RotatingFileHandler`, 1 MB
  × 3 backups). `LOG_TO_STDERR=1` espelha os eventos no stderr para depuração; o
  padrão desligado mantém o terminal do usuário 100% limpo. `configure_logging()`
  é idempotente e põe `propagate = False` no logger do pacote.
- **`run_id` por turno**, gerado em `main.py` (`_run_turn`) a cada `graph.invoke`
  e propagado de duas formas: no `AgentState.run_id` (lido pelos decorators de
  nó) e num `contextvars.ContextVar` publicado por `_run_turn` e re-setado pelos
  decorators — assim o `copy_context()` do fan-out da busca já o carrega e até as
  chamadas profundas em `tools.py` (retries da Wikipédia, extração) saem com o
  `run_id` correto. O filtro que injeta o `run_id` fica nos **handlers**, não no
  logger (um filtro de logger não roda para records propagados dos loggers
  filhos).
- **Instrumentação** em `nodes.py`: os decorators `_logged_node` (nos 8 nós) e
  `_logged_router` (nos 2 roteadores) emitem `node_start`/`node_end`/`node_error`
  e `routing_decision`; o `_logged_node` também mede a latência do nó
  (`perf_counter`) — o `duration_ms` entra nos eventos `node_end`/`node_error` e
  numa linha da trilha de auditoria (T05). Eventos semânticos pontuais:
  `validation_blocked` (com o motivo: `prompt_injection` / `non_latin_script` /
  `url`, mapeado da mensagem de recusa sem tocar em `validation.py`),
  `memory_persisted`, `llm_decision`, `llm_exception_fallback`,
  `leaked_tool_calls_recovered`/`_unrecoverable`, `tool_executed` (nome, args
  resumidos, status, `duration_ms`), `search_dispatched`, `page_fetched`,
  `search_merged`. `main.py` emite `run_start`/`run_end`/`run_error`.
- **Nada de segredos nem conteúdo de mensagens.** Os nós logam só metadados
  (contagens, nomes de tools, decisões, booleanos, o destino) — nunca o texto do
  usuário, a resposta do LLM, a lista de atrações ou o itinerário. Como defesa em
  profundidade, o `JsonFormatter` ainda redige o valor de `GROQ_API_KEY` da
  string final e trunca valores string longos (500 chars).
- **Nível** configurável por `LOG_LEVEL` (padrão `INFO`; valor inválido cai para
  `INFO`). Timestamps em **UTC** ISO-8601 (`…Z`); a trilha de auditoria (T05)
  usa **o mesmo formato UTC** para casar com os logs. Só a `memory.py` fica em
  hora local (dado de produto, não correlacionado com os sinais).

## Trilha de auditoria (`audit.py`)

Segundo sinal de observabilidade do §4.6 (T05/#16): uma tabela SQLite
`execution_audit`, **uma linha por passo executado** (nó do grafo ou tool) com a
**latência medida**, correlacionada aos logs (T04) pelo **mesmo `run_id`**. A
T06/#17 cruza os dois para reconstruir uma execução real, achar o gargalo e
investigar um erro. Regras de design (não alterar sem alinhar):

- **Espelha o padrão de `memory.py`**: `sqlite3` da stdlib (sem dependência
  nova), `_connect` que abre/commita/fecha por chamada (fecha explícito por
  causa do lock de arquivo no Windows), funções puras com `db_path` opcional que
  cai para `AUDIT_DB_PATH` em tempo de chamada (testável na T07).
- **Banco próprio** `itinerai_audit.db` (raiz do projeto, **não versionado**),
  separado do `itinerai_memory.db`: a trilha é *append-only* e cresce a cada
  turno; apagar o arquivo reseta. `_connect` usa `timeout=10` porque os dois
  ramos do fan-out da busca escrevem de threads diferentes.
- **Colunas** (do checklist da T05): `run_id`, `step`, `step_type`
  (`node` | `tool` | `turn`), `status` (`ok` | `error` | `retry` | `fallback`),
  `duration_ms` (REAL, `NULL` em linhas de `retry`), `error` (tipo da exceção /
  motivo do fallback), `created_at` (UTC ISO-8601 `…Z`). Mais um `id` rowid para
  ordenação estável e um índice em `run_id`.
- **Best-effort**: a instrumentação chama `audit.try_record(...)`, que monta o
  `AuditStep`, chama a função pura `record_audit_step` e **engole** qualquer erro
  (só loga `audit_write_failed`). Auditar **nunca** derruba um turno. As funções
  puras (`record_audit_step`, `load_audit_trail`, `format_audit_trail`, `init_db`)
  propagam erros — quem degrada é o `try_record`.
- **Onde as linhas nascem**: `_logged_node` (latência de cada nó, `ok`/`error`);
  `call_tools` (a tool `build_itinerary`); `fetch_page_attractions` (o passo
  `wikipedia_fetch`, só a parte de rede); `_get_wikipedia` (linhas `retry`);
  `_invoke_structured` (o passo `llm_extraction`, `ok`/`fallback` com o motivo);
  `call_llm` (linha `fallback` do `llm_agent`); `_run_turn` em `main.py` (a linha
  `turn` `graph_invoke` com a latência ponta a ponta). Todos leem o `run_id` de
  `run_id_var.get()` (fundo de `tools.py`) ou de `state.run_id`.
- **Exibir uma trilha**: `python show_audit.py <run_id>` (script na raiz; a
  lógica fica na função pura `audit.format_audit_trail`, que mostra a tabela de
  passos, o passo mais lento e o total do turno). Pegue o `run_id` de qualquer
  linha de `logs/itinerai.log`.
- **Fora de escopo (T05)**: testes unitários das funções de auditoria →
  **T07/#18** (bootstrap do `pytest`); o documento de evidências cruzando os
  dois sinais → **T06/#17**; poda/retenção do `itinerai_audit.db`.

## Robustez em tool-calling

Estas regras nasceram com o `llama-3.1-8b-instant` (modelo pequeno e frágil,
hoje substituído por `openai/gpt-oss-120b`). O `gpt-oss-120b` erra muito menos,
mas as proteções continuam — cada uma corrige um `tool_use_failed`/crash real e
o custo delas é baixo (não remover sem motivo):

- O LLM de extração (`_extraction_llm`) usa `temperature=0`; os prompts de
  extração pedem no máximo ~15 itens e proíbem repetição (evita loops que
  truncam o JSON).
- **A extração NÃO usa `ChatGroq.with_structured_output`.** Com o
  `openai/gpt-oss-120b` esse método força `tool_choice` e o modelo devolve o
  JSON como **texto** (não como tool call), o que a Groq rejeita com
  `tool_use_failed` ("model did not call a tool"). Em vez disso,
  `_invoke_structured` (em `tools.py`) pede o formato do JSON no próprio prompt
  de extração e faz o parse do texto da resposta (`_extract_json_payload`
  tolera cercas ` ```json ` e texto ao redor; lista "solta" é embrulhada no
  campo único do schema), validando com `schema.model_validate`.
- Falhas de extração são tratadas: `_invoke_structured` devolve `None` em
  qualquer erro, as extrações caem para vazio e `call_llm` responde com
  mensagem amigável, em vez de derrubar o agente.
- Mantenha os schemas das tools **pequenos**; para dados grandes vindos do
  estado, use `InjectedToolArg` (nunca exponha listas aninhadas ao modelo).
- **Recuperação de tool calls "vazadas" como texto:** o modelo às vezes emite a
  chamada no formato nativo do Llama (`<function=nome>{json}</function>`) como
  **texto** da resposta, em vez de `tool_calls` estruturados (a Groq não parseia
  e o campo `tool_calls` fica vazio). Sem tratamento, o texto cru apareceria no
  terminal e o roteiro nunca seria montado. `_repair_leaked_response` (em
  `nodes.py`, aplicado no fim de `call_llm`) detecta o padrão, reconstrói as
  chamadas em `tool_calls` reais por regex determinístico e **descarta um
  `build_itinerary` prematuro** quando há uma busca no mesmo lote (a busca
  precisa rodar antes); se nada for recuperável (JSON truncado, ferramenta
  desconhecida), troca o texto cru por um aviso amigável. Esse descarte do
  `build_itinerary` prematuro (helper `_drop_premature_build_itinerary`) vale
  também para tool calls **estruturados** — `call_llm` o aplica antes de
  `route_after_llm`, para que `merge_pages` responda sempre a exatamente um
  `tool_call_id`.
- Para reduzir o gatilho na origem, o `AGENT_SYSTEM_PROMPT` orienta o modelo a
  chamar **uma ferramenta por vez**, a nunca escrever a chamada como texto e a
  sempre usar `search_tourist_attractions` **antes** de `build_itinerary`.

## Estrutura do projeto

Estrutura baseada na organização recomendada pela documentação do LangGraph
(ver [docs/application-structure.md](docs/application-structure.md)), variante
`requirements.txt`:

```
mini-projeto-ItinerAI/
├── itinerai_agent/         # todo o código do agente
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py       # variáveis de ambiente (GROQ_MODEL, GROQ_TEMPERATURE, WIKIPEDIA_TIMEOUT, LOG_LEVEL)
│   │   ├── tools.py        # tools: busca de pontos turísticos, geração do .md
│   │   ├── validation.py   # validação de entrada do usuário (anti prompt injection, idioma, URLs)
│   │   ├── memory.py       # memória persistente da última viagem em SQLite (retomada)
│   │   ├── logging_config.py  # bootstrap do logging estruturado em JSON + run_id (T04/#15)
│   │   ├── audit.py        # trilha de auditoria + latência por passo em SQLite (T05/#16)
│   │   ├── prompts.py      # prompts do agente e das extrações
│   │   ├── nodes.py        # funções de nó do grafo (validação, persistência, LLM, tools, fan-out da busca)
│   │   └── state.py        # definição do estado do grafo (modelos pydantic)
│   ├── __init__.py
│   └── agent.py            # construção/compilação do StateGraph
├── docs/
│   └── application-structure.md
├── output/                 # itinerários .md gerados pelo agente (não versionado)
├── logs/                   # logs estruturados em JSON (itinerai.log; não versionado)
├── main.py                 # ponto de entrada: loop de chat via terminal
├── show_audit.py           # exibe a trilha de auditoria de um run_id (T05/#16)
├── .env                    # variáveis de ambiente locais (não versionado)
├── itinerai_memory.db      # memória persistente SQLite da última viagem (não versionado)
├── itinerai_audit.db       # trilha de auditoria SQLite (não versionado)
├── requirements.txt        # dependências do projeto
└── langgraph.json          # arquivo de configuração do LangGraph
```

- Todo o código do agente fica dentro de `itinerai_agent/`, seguindo o padrão
  `my_agent` da documentação do LangGraph.
- `state.py` define o estado do grafo (`AgentState`) com `pydantic.BaseModel`:
  `messages`, `run_id`, `destination`, `num_days`, `tourist_attractions`,
  `itinerary`, `pending_search` e `page_results`. O `run_id` (T04/#15) é gerado
  por turno em `main.py` e propagado para correlacionar os logs estruturados e a
  trilha de auditoria — ver "Observabilidade / logging" e "Trilha de auditoria".
  A duração (`num_days`) fica no estado —
  além de ser passada a `build_itinerary` — para poder ser persistida pela
  memória e permitir a retomada da conversa (populada em `call_tools` a partir
  de `build_itinerary`). `pending_search` (modelo `PendingSearch`) e
  `page_results` (`dict[str, WikipediaPageResult]` com o reducer
  `_merge_page_results`) suportam o fan-out/fan-in da busca — ver
  "Paralelização da busca da Wikipédia". Também é o lugar dos modelos de domínio
  usados pelas tools (`TouristAttraction`, `Itinerary`/`ItineraryDay`,
  `WikipediaPageResult`). As atrações têm um campo `location` (exato ou
  provável) usado no agrupamento por proximidade.
- `tools.py` concentra as ferramentas expostas ao agente (pesquisa de pontos
  turísticos, geração do arquivo `.md`) — ver "Ferramentas do agente" acima.
- `nodes.py` concentra os nós do grafo — ver "Arquitetura do grafo
  (tool-calling)" acima para o padrão atual de roteamento.
- `validation.py` concentra a validação de entrada do usuário (funções puras de
  regex + mensagens de recusa) — ver "Validação de entrada" acima.
- `config.py` concentra a leitura das variáveis de ambiente (constantes
  `GROQ_MODEL`, `GROQ_TEMPERATURE`, `WIKIPEDIA_TIMEOUT`, `LOG_LEVEL`,
  `LOG_TO_STDERR` lidas no import) — ver "Configuração de ambiente" abaixo.
- `logging_config.py` concentra o bootstrap do logging estruturado em JSON
  (formatter, `ContextVar` do `run_id`, `configure_logging()` idempotente) — ver
  "Observabilidade / logging" acima.
- `memory.py` concentra a memória persistente em SQLite (funções puras
  `init_db`/`save_trip_memory`/`load_trip_memory` + o modelo `TripMemory`) —
  ver "Memória persistente" acima.
- `audit.py` concentra a trilha de auditoria em SQLite (funções puras
  `init_db`/`record_audit_step`/`load_audit_trail`/`format_audit_trail` + o
  wrapper best-effort `try_record` + o modelo `AuditStep`) — ver "Trilha de
  auditoria" acima. `show_audit.py` (raiz) é o comando de exibição.
- Itinerários gerados são salvos como arquivo `.md` em `output/`.

## Configuração de ambiente

- Requer Python 3.12.9.
- **Todas as variáveis são lidas em `itinerai_agent/utils/config.py`** (no
  import, após `load_dotenv()` do `main.py`), com padrões que preservam o
  comportamento anterior — rodar só com `GROQ_API_KEY` não muda nada.
- Variável obrigatória: `GROQ_API_KEY` (nunca commitada; consumida direto pela
  `langchain-groq`, não passa por `config.py`; `logging_config.py` a lê só para
  redigir seu valor dos logs, como defesa em profundidade).
- Variáveis opcionais:
  - `GROQ_MODEL` (padrão `openai/gpt-oss-120b`) — modelo do agente **e** da
    extração. T03/#14.
  - `GROQ_TEMPERATURE` (padrão `0.7`) — temperatura só do LLM do agente (`_llm`);
    a extração (`_extraction_llm`) usa `temperature=0` fixo, à parte.
  - `WIKIPEDIA_TIMEOUT` (segundos; padrão `10`) — timeout das requisições HTTP à
    Wikipédia. Ver "Resiliência das integrações".
  - `LOG_LEVEL` (padrão `INFO`) — nível dos logs estruturados; valor inválido
    cai para `INFO`. Ver "Observabilidade / logging". T04/#15.
  - `LOG_TO_STDERR` (padrão desligado) — quando ligado (`1`/`true`/`yes`/`on`),
    espelha os logs no stderr além do arquivo, para depuração.
- `.env`, `output/`, `logs/` e os bancos `itinerai_memory.db` /
  `itinerai_audit.db` devem estar no `.gitignore`.
- A memória persistente, a trilha de auditoria e o logging estruturado usam só a
  stdlib (`sqlite3`, `logging`) — nenhuma dependência extra no
  `requirements.txt`. Os testes (`pytest`) entram na T07/#18.

## Convenções de código

- Use type hints em todas as funções públicas.
- Toda estrutura de dados trocada entre nós do grafo deve ser um modelo
  `pydantic`, não `dict` solto. (`AgentState.page_results` é `dict[str,
  WikipediaPageResult]` — um canal de reducer tipado com valores pydantic, no
  mesmo espírito de `messages: Annotated[list[BaseMessage], add_messages]`, não
  um `dict` solto.)
- Mantenha as tools em `tools.py` puras e testáveis (sem lógica de
  orquestração do grafo dentro delas).
- Nomes de arquivos-fonte, pastas, funções e variáveis em inglês; mensagens
  voltadas ao usuário final (saída no terminal, conteúdo do `.md` gerado)
  em português. Exceção: os `.md` gerados em `output/` são artefatos do
  usuário e seguem o esquema `itinerario-<destino>-<n>-dias.md`.

## Regras obrigatórias

- **Priorize sempre as funcionalidades/ferramentas já disponibilizadas pelo
  harness do VSCode** (edição de arquivos, busca, etc.) em vez de comandos de
  terminal equivalentes, sempre que possível.
- **Antes de executar qualquer comando no terminal, é obrigatório, sem
  exceções, descrever exatamente o que o comando faz e qual o seu objetivo, e
  solicitar a aprovação do usuário antes de rodá-lo.** Isso vale mesmo para
  comandos aparentemente simples ou de baixo risco.
