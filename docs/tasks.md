# Tarefas — Projeto Avaliativo M2.2 (ItinerAI)

Backlog das implementações necessárias para atender aos requisitos ainda não
cobertos pelo estado atual do projeto (ver [requisitos.md](requisitos.md)).

Cada tarefa abaixo segue o formato de um dos templates de issue em
[issues-templates/](issues-templates/) e deve virar um card no GitHub Project:

| Template | Prefixo | Quando usar |
| --- | --- | --- |
| `epic_template.yml` | `[EPIC]` | Agrupador de um bloco inteiro de tarefas |
| `user_story_template.yml` | `[STORY]` | Funcionalidade percebida pelo usuário final |
| `tech_template.yml` | `[TECH]` | Tarefa técnica, infraestrutura, refatoração |
| `docs_template.yml` | `[DOCS]` | Documentação e evidências |

As tarefas estão organizadas em **6 epics**, um por bloco. Cada epic deve virar
uma issue própria no GitHub, e as tarefas do bloco devem ser vinculadas a ela
(por sub-issues ou por referência ao número da issue do epic na descrição).

## Índice dos epics

| Epic | Issue | Título | Bloco | Tarefas | Critérios do §6 |
| --- | --- | --- | --- | --- | --- |
| E01 | [#6](https://github.com/joaopuel/mini-projeto-ItinerAI/issues/6) | Arquitetura agêntica e resiliência | A | T01–T03 | 7, 8 |
| E02 | [#7](https://github.com/joaopuel/mini-projeto-ItinerAI/issues/7) | Observabilidade e investigação de execuções | B | T04–T06 | 11 |
| E03 | [#8](https://github.com/joaopuel/mini-projeto-ItinerAI/issues/8) | QA e testes inteligentes | C | T07–T09 | 12 |
| E04 | [#9](https://github.com/joaopuel/mini-projeto-ItinerAI/issues/9) | DevOps inteligente e detecção de falhas | D | T10–T11 | 13 |
| E05 | [#10](https://github.com/joaopuel/mini-projeto-ItinerAI/issues/10) | Low-code e limites de autonomia | E | T12–T14 | 14, 10 |
| E06 | [#11](https://github.com/joaopuel/mini-projeto-ItinerAI/issues/11) | Documentação, evidências e entrega | F | T15–T19 | 1, 2, 3, 4, 5, 15 |

## Índice das tarefas

| # | Issue | Tarefa | Epic | Tipo | Critério do §6 | Branch sugerida |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | #12 | Paralelizar a busca de páginas da Wikipédia no grafo | E01 (#6) | TECH | 7 | `feature/langgraph-paralelizacao` |
| T02 | #13 | Timeout, retry limitado e fallback nas integrações externas | E01 (#6) | TECH | 8, 11 | `feature/resiliencia-integracoes` |
| T03 | #14 | Configurar o modelo do LLM por variável de ambiente | E01 (#6) | TECH | 15 (§4.10) | `feature/config-modelo-env` |
| T04 | #15 | Logs estruturados em JSON com correlação por `run_id` | E02 (#7) | TECH | 11 | `feature/observabilidade` |
| T05 | #16 | Registro de auditoria e métricas de latência por nó e tool | E02 (#7) | TECH | 11 | `feature/observabilidade` |
| T06 | #17 | Investigar uma execução real com os dois sinais | E02 (#7) | DOCS | 11 | `docs/evidencias-observabilidade` |
| T07 | #18 | Suíte de testes unitários com pytest e cobertura mínima de 70% | E03 (#8) | TECH | 12 | `feature/qa-testes-unitarios` |
| T08 | #19 | Teste E2E do fluxo principal e do cenário adversarial | E03 (#8) | TECH | 12 | `feature/qa-teste-e2e` |
| T09 | #20 | Code review com IA de uma alteração real e priorização por risco | E03 (#8) | DOCS | 12 | `docs/qa-code-review-ia` |
| T10 | #21 | Pipeline de CI com lint, testes e cobertura mínima de 70% | E04 (#9) | TECH | 13 | `feature/devops-pipeline-ci` |
| T11 | #22 | Análise de logs de CI com IA, anomalia e estimativa de risco | E04 (#9) | DOCS | 13 | `docs/devops-anomalias` |
| T12 | #23 | Receber o itinerário por e-mail ao final do processo | E05 (#10) | STORY | 14, 10 | `feature/low-code-n8n` |
| T13 | #24 | Webhook de integração com o n8n | E05 (#10) | TECH | 14, 8 | `feature/low-code-n8n` |
| T14 | #25 | Documentar o fluxo n8n e as instruções de reprodução | E05 (#10) | DOCS | 14, 5 | `docs/low-code-n8n` |
| T15 | #26 | Reescrever o README.md conforme o item 5.2 | E06 (#11) | DOCS | 5 | `docs/readme-video` |
| T16 | #27 | Organizar `/docs` e registrar o ciclo de refinamento | E06 (#11) | DOCS | 15 | `docs/evidencias` |
| T17 | #28 | Gravar e publicar o vídeo de demonstração | E06 (#11) | DOCS | 1 | `docs/readme-video` |
| T18 | #29 | Criar e manter o quadro Kanban no GitHub Project | E06 (#11) | TECH | 2, 3 | — |
| T19 | #30 | Versionar o planejamento do M2.2 (templates, requisitos e tasks.md) | E06 (#11) | DOCS | 4, 5 | `docs/planejamento-m2-2` |

> Todas as issues estão criadas no repositório, atribuídas a `@joaopuel` e
> adicionadas ao [quadro do projeto](https://github.com/users/joaopuel/projects/1/views/1).

---

## Bloco A — Arquitetura agêntica e resiliência

### E01 — [EPIC] Arquitetura agêntica e resiliência

- **Tarefas:** T01, T02, T03
- **Critérios atendidos:** 7, 8 — §4.2, §4.3, §4.6, §4.10

**Visão**

Evoluir o grafo do ItinerAI para atender integralmente ao §4.2, acrescentando a
paralelização hoje ausente, e tornar as integrações externas resilientes a
falhas de rede e de geração estruturada. Ao final deste epic, o agente deve
percorrer um fluxo com execução sequencial, ramificação condicional,
paralelização simples e condição de parada explícita, sem que uma falha da
Wikipédia ou do LLM derrube o processo, e com toda a configuração do modelo
externalizada para variáveis de ambiente.

**Escopo do Epic**

- Transformar a busca encadeada de páginas da Wikipédia em um fan-out/fan-in
  paralelo no grafo, com consolidação determinística dos resultados.
- Implementar política de resiliência nas chamadas externas: timeout explícito,
  retry limitado com backoff e fallback com mensagem amigável em português.
- Substituir o tratamento genérico de exceções por tratamento de exceções
  específicas, com registro das tentativas e fallbacks.
- Externalizar o modelo e a temperatura do LLM para variáveis de ambiente,
  mantendo segredos fora do código.
- Manter a separação entre decisões do modelo e regras determinísticas da
  aplicação, princípio já adotado na validação e na memória.

---

### T01 — [TECH] Paralelizar a busca de páginas da Wikipédia no grafo

- **Critério atendido:** 7 (grafo com paralelização simples) — §4.2
- **Branch sugerida:** `feature/langgraph-paralelizacao`

**Descrição**

O grafo atual é 100% sequencial (`validate_input → persist_memory → call_llm ⇄
call_tools`), e o §4.2 exige explicitamente "ao menos uma paralelização
simples". Hoje `_fetch_wikipedia_page` tenta `Tourism in <destino>` e, só se
falhar, tenta `<destino>` — duas requisições encadeadas que podem rodar em
paralelo. Transformar essa busca em um fan-out/fan-in no grafo (dois nós de
busca disparados em paralelo a partir do mesmo nó, convergindo em um nó de
consolidação) atende ao requisito e ainda reduz a latência da etapa mais lenta
do fluxo. Manter a lógica determinística de escolha da melhor página fora do
LLM.

**Checklist técnico**

- [x] Extrair a busca de cada página da Wikipédia em nós distintos do grafo
      (`fetch_tourism_page` e `fetch_destination_page`)
- [x] Configurar o fan-out a partir de um nó de busca dedicado (`dispatch_search`)
      para os dois nós em paralelo
- [x] Criar o nó de fan-in (`merge_pages`) que consolida os resultados de forma
      determinística (sem LLM), priorizando a página `Tourism in <destino>` quando válida
- [x] Garantir que o estado suporte escrita concorrente dos dois ramos
      (`page_results: Annotated[dict[str, WikipediaPageResult], _merge_page_results]`)
- [x] Preservar o comportamento atual quando apenas uma das páginas existir
- [x] Atualizar o diagrama do fluxo no `README.md` e no `CLAUDE.md`

---

### T02 — [TECH] Timeout, retry limitado e fallback nas integrações externas

- **Critério atendido:** 8 (tratamento de falhas na tool), 11 (resiliência) — §4.3, §4.6
- **Branch sugerida:** `feature/resiliencia-integracoes`

**Descrição**

Hoje `tools.py` tem apenas `timeout=10` na chamada à Wikipédia e um
`except Exception` genérico; uma falha de rede propaga e derruba o processo do
agente. O §4.6 exige tratamento básico de falhas nas integrações externas com
timeout, retry limitado ou fallback. Implementar uma política de resiliência
explícita e determinística nas chamadas HTTP e na geração estruturada do LLM,
sem mascarar erros: toda tentativa e todo fallback devem ser registrados nos
logs estruturados (T04).

**Checklist técnico**

- [x] Definir política de retry limitado (máximo de 2 novas tentativas) com
      backoff exponencial para as chamadas HTTP da Wikipédia (`_get_wikipedia`)
- [x] Manter timeout explícito e configurável por variável de ambiente
      (`WIKIPEDIA_TIMEOUT`, padrão 10s)
- [x] Tratar apenas exceções específicas (`RequestException` /
      `Timeout` / `ConnectionError`) em vez de `except Exception` no caminho HTTP
- [x] Implementar fallback: falha de rede após os retries → `unavailable=True`,
      `merge_pages` + `AGENT_SYSTEM_PROMPT` produzem mensagem amigável, sem
      propagar a exceção
- [x] Aplicar o mesmo tratamento a `_invoke_structured` — `max_retries=2`
      explícito no `_extraction_llm` (retry do SDK da Groq) + logging do fallback
- [x] Registrar tentativa, erro e fallback via `logging` (`NullHandler` no
      pacote; os handlers JSON/arquivo/`run_id` foram plugados na T04/#15)
- [x] Cobrir a política com testes unitários que simulem timeout e erro HTTP
      — **T07/#18** (`tests/utils/test_tools_resilience.py`)

---

### T03 — [TECH] Configurar o modelo do LLM por variável de ambiente

- **Critério atendido:** 15 — §4.10
- **Branch sugerida:** `feature/config-modelo-env`

**Descrição**

O §4.10 exige que o modelo utilizado seja configurado por variável de ambiente.
Hoje `itinerai_agent/utils/nodes.py:32` fixa o modelo no código
(`ChatGroq(model="openai/gpt-oss-120b")`, duplicado em `tools.py`); apenas a
`GROQ_API_KEY` vem do ambiente. Externalizar o nome do modelo (e a temperatura)
para variáveis de ambiente, com valores padrão seguros, e documentá-las no
`.env.example`.

**Checklist técnico**

- [x] Criar as variáveis `GROQ_MODEL` e `GROQ_TEMPERATURE` com leitura via
      `os.getenv` e valores padrão iguais aos atuais (novo `utils/config.py`,
      que também absorve o `WIKIPEDIA_TIMEOUT` da T02)
- [x] Aplicar as variáveis ao `_llm` e ao `_extraction_llm` (mantendo
      `temperature=0` no LLM de extração)
- [x] Atualizar o `.env.example` com as novas variáveis, sem valores sensíveis
- [x] Documentar as variáveis na seção de instalação do `README.md`
- [x] Garantir que nenhuma credencial ou chave permaneça no código-fonte
      (`.env` no `.gitignore`; `os.getenv` só em `config.py`; `.env.example` só
      com nomes)

---

## Bloco B — Observabilidade

### E02 — [EPIC] Observabilidade e investigação de execuções

- **Tarefas:** T04, T05, T06
- **Critérios atendidos:** 11 — §4.6

**Visão**

Dotar o ItinerAI de observabilidade real, hoje inexistente: o projeto não possui
uma única chamada de `logging`. Ao final deste epic, toda execução do agente
deve produzir dois sinais correlacionados — logs estruturados em JSON e uma
trilha de auditoria com latência — unidos por um `run_id` único por execução,
permitindo reconstruir qualquer turno da conversa, identificar as decisões de
roteamento, localizar erros e medir o gargalo do fluxo, sem poluir a interação
do usuário no terminal nem expor dados sensíveis.

**Escopo do Epic**

- Implementar logging estruturado em JSON, com nível configurável e saída para
  arquivo, instrumentando todos os nós do grafo e todas as tools.
- Implementar trilha de auditoria persistida em SQLite, reaproveitando a
  infraestrutura de `memory.py`, com medição de latência por passo.
- Adotar o `run_id` como chave de correlação entre os dois sinais e propagá-lo
  pelo `AgentState`.
- Garantir que segredos, o e-mail do usuário e o conteúdo integral das mensagens
  nunca sejam registrados.
- Produzir a evidência de investigação de uma execução real, incluindo um caso
  de erro, exigida pelo §4.6.

---

### T04 — [TECH] Logs estruturados em JSON com correlação por `run_id`

- **Critério atendido:** 11 (primeiro sinal de observabilidade) — §4.6
- **Branch sugerida:** `feature/observabilidade`

**Descrição**

O projeto não possui nenhuma chamada de `logging` hoje, e o §4.6 exige logs
estruturados como sinal obrigatório. Implementar um módulo de logging que emita
eventos em JSON (uma linha por evento) para `stderr` e para arquivo em
`logs/`, com um `run_id` gerado por execução que permita correlacionar todos os
eventos de um mesmo turno da conversa. Os logs não devem poluir a interação do
terminal (que permanece limpa para o usuário) nem registrar dados sensíveis
como a `GROQ_API_KEY`.

**Checklist técnico**

- [x] Criar `itinerai_agent/utils/logging_config.py` com formatter JSON próprio
      (sem novas dependências) e nível configurável por `LOG_LEVEL`
- [x] Gerar um `run_id` (UUID) por execução e propagá-lo no `AgentState`
      (gerado por turno em `main._run_turn`; também publicado num `ContextVar`
      para as chamadas profundas de `tools.py` o herdarem)
- [x] Instrumentar a entrada e a saída de cada nó do grafo (`validate_input`,
      `persist_memory`, `call_llm`, `call_tools` e os nós do fan-out) com evento,
      `run_id`, timestamp e resultado da decisão de roteamento (decorators
      `_logged_node` / `_logged_router` em `nodes.py`)
- [x] Instrumentar cada tool com nome, argumentos resumidos e status
      (evento `tool_executed` em `call_tools`; `search_dispatched` / `page_fetched`
      / `search_merged` para a busca; os 6 logs de `tools.py` da T02 seguem)
- [x] Registrar bloqueios da validação com o motivo (injeção, idioma ou URL)
      (evento `validation_blocked`, motivo mapeado da mensagem de recusa sem
      alterar `validation.py`)
- [x] Direcionar os logs para arquivo em `logs/` e adicionar `logs/` ao
      `.gitignore` (`RotatingFileHandler`, `logs/itinerai.log`)
- [x] Garantir que segredos e o conteúdo integral das mensagens não sejam logados
      (só metadados nos eventos; `JsonFormatter` ainda redige `GROQ_API_KEY` e
      trunca strings longas, como defesa em profundidade)

> **Decisão de escopo:** a descrição cita saída "para `stderr` e para arquivo",
> mas o checklist e o requisito de "terminal limpo" priorizam o arquivo — a
> implementação grava **só em `logs/` por padrão** e expõe `LOG_TO_STDERR=1`
> (padrão desligado) para espelhar no stderr durante depuração.

---

### T05 — [TECH] Registro de auditoria e métricas de latência por nó e tool

- **Critério atendido:** 11 (segundo sinal, correlacionado) — §4.6
- **Branch sugerida:** `feature/observabilidade`

**Descrição**

O §4.6 exige dois sinais correlacionados: logs estruturados e um segundo sinal
entre trace, métrica ou auditoria. Implementar uma trilha de auditoria
persistida em SQLite (reaproveitando a infraestrutura já existente em
`memory.py`, sem nova dependência) contendo uma linha por passo executado, com
latência medida. O `run_id` de T04 é a chave de correlação entre os dois sinais.

**Checklist técnico**

- [x] Criar a tabela `execution_audit` com `run_id`, `step`, `step_type`
      (nó ou tool), `status`, `duration_ms`, `error` e `created_at`
      (+ `id` rowid p/ ordenação e índice em `run_id`; `step_type` também aceita
      `turn`; `status` ∈ `ok`/`error`/`retry`/`fallback`)
- [x] Criar funções puras de escrita e leitura da auditoria, no mesmo padrão
      testável de `memory.py` (`itinerai_agent/utils/audit.py`: `init_db`,
      `record_audit_step`, `load_audit_trail`, `format_audit_trail`, `db_path`
      injetável; + `try_record` best-effort para a instrumentação)
- [x] Medir a latência de cada nó do grafo e de cada chamada de tool
      (`perf_counter` no decorator `_logged_node`; `build_itinerary` em
      `call_tools`; `wikipedia_fetch` e `llm_extraction` em `tools.py`; a linha
      `turn` do `graph_invoke` em `main._run_turn`)
- [x] Registrar falhas, retries e fallbacks de T02 na auditoria
      (`retry` em `_get_wikipedia`, `error` em `fetch_page_attractions`,
      `fallback` em `_invoke_structured` e no `llm_exception_fallback`)
- [x] Garantir que o `run_id` seja idêntico ao dos logs estruturados
      (mesmo `run_id_var` / `state.run_id` da T04; `created_at` em UTC como os logs)
- [x] Criar um comando ou script simples que exiba a trilha de um `run_id`
      (`python show_audit.py <run_id>` → `audit.format_audit_trail`)
- [x] Cobrir as funções de auditoria com testes unitários
      — **T07/#18** (`tests/utils/test_audit.py`)

> **Notas de escopo:** (1) a trilha usa **banco próprio** `itinerai_audit.db`
> (append-only, cresce a cada turno), separado do `itinerai_memory.db` de
> registro único — `.gitignore` ajustado (o checklist não mencionava). (2) a
> auditoria é **best-effort**: `try_record` engole erros de I/O — auditar nunca
> derruba um turno.

---

### T06 — [DOCS] Investigar uma execução real com os dois sinais

- **Critério atendido:** 11 (uso dos sinais para investigar uma execução) — §4.6
- **Branch sugerida:** `docs/evidencias-observabilidade`

**Descrição**

Não basta produzir os sinais: o §4.6 exige utilizá-los para investigar pelo
menos uma execução real, identificando fluxo, decisões relevantes, erros e
latência. Produzir um documento em `docs/evidencias/observabilidade.md` que
reconstrua uma execução ponta a ponta a partir do `run_id`, cruzando os logs
estruturados (T04) com a trilha de auditoria (T05).

**Conteúdo mínimo**

- [ ] Descrição dos dois sinais implementados e da chave de correlação
      (`run_id`)
- [ ] Trecho real de log estruturado de uma execução, com dados sensíveis
      omitidos
- [ ] Trecho real da trilha de auditoria do mesmo `run_id`
- [ ] Reconstrução narrativa do fluxo: nós percorridos, decisão de roteamento,
      tools chamadas e resultado final
- [ ] Tabela de latência por passo, apontando o gargalo da execução
- [ ] Investigação de pelo menos uma execução com erro (ex.: falha de rede na
      Wikipédia), mostrando como os sinais permitiram identificar a causa

---

## Bloco C — QA e testes inteligentes

### E03 — [EPIC] QA e testes inteligentes

- **Tarefas:** T07, T08, T09
- **Critérios atendidos:** 12 — §4.7

**Visão**

Estabelecer a malha de qualidade do projeto, hoje totalmente ausente — não
existe nenhum teste automatizado. Ao final deste epic, o ItinerAI deve possuir
uma suíte de testes com cobertura mínima de 70% verificada automaticamente,
testes E2E cobrindo o fluxo principal e o cenário adversarial, uma justificativa
explícita de priorização por risco e a evidência de uso de IA na revisão de uma
alteração real do projeto.

**Escopo do Epic**

- Configurar `pytest` e `pytest-cov` com meta de cobertura de 70% aplicada como
  gate.
- Cobrir com testes unitários a lógica determinística de maior risco:
  `validation.py`, `memory.py` e as funções puras de `tools.py`.
- Implementar testes E2E sobre o grafo compilado, com LLM e rede simulados,
  cobrindo fluxo principal, prompt injection, falha de rede e retomada da
  memória.
- Garantir que nenhum teste dependa de rede ou da `GROQ_API_KEY`, viabilizando a
  execução no CI.
- Documentar a priorização por risco, impacto e criticidade e registrar o code
  review assistido por IA de um Pull Request real.

---

### T07 — [TECH] Suíte de testes unitários com pytest e cobertura mínima de 70%

- **Critério atendido:** 12 — §4.7
- **Branch sugerida:** `feature/qa-testes-unitarios`

**Descrição**

O projeto não possui nenhum teste automatizado hoje. Criar a estrutura de testes
com `pytest` e `pytest-cov`, cobrindo prioritariamente os módulos de lógica
determinística e pura, que são os de maior risco e mais fáceis de cobrir:
`validation.py`, `memory.py` e as funções puras de `tools.py` (agrupamento por
proximidade, distribuição por dias, slug e resolução de nome de arquivo). A meta
de cobertura é de no mínimo **70%**, verificada automaticamente no CI (T10).

**Checklist técnico**

- [x] Adicionar `pytest` e `pytest-cov` ao `requirements.txt` (ou a um
      `requirements-dev.txt`) — feito em `requirements-dev.txt` (`-r
      requirements.txt` + `pytest` + `pytest-cov` + `coverage[toml]`)
- [x] Criar a pasta `tests/` espelhando a estrutura de `itinerai_agent/`
      (`tests/utils/`; `conftest.py` com o shim de `GROQ_API_KEY` e a fixture
      `autouse` que isola disco)
- [x] Configurar `pytest.ini` (ou `pyproject.toml`) com `--cov=itinerai_agent`
      e `--cov-fail-under=70` — `pyproject.toml` (primeiro do projeto)
- [x] Testar `validation.py`: injeção nos 6 idiomas, scripts não-latinos, URLs,
      ordem de precedência das regras e entradas benignas (sem falso positivo)
- [x] Testar `memory.py` com banco temporário: `init_db`, upsert de registro
      único, `load_trip_memory` sem registro e restrição `CHECK (id = 1)`
- [x] Testar as funções puras de `tools.py`: agrupamento por proximidade,
      máximo de 3 atrações por dia, poucas atrações para muitos dias
      (observação e revisitas), slug e sufixo sequencial de arquivo
- [x] Usar mocks/fixtures para as chamadas HTTP e ao LLM (nenhum teste pode
      depender de rede ou de `GROQ_API_KEY`)
- [x] Atingir e comprovar cobertura ≥ 70% *(≈90% estimada; `pyproject.toml`
      falha o build abaixo de 70%)*

> **Extra (necessário para o gate de 70%):** também cobertos `audit.py` (T05),
> `state._merge_page_results`, os helpers puros e nós determinísticos de
> `nodes.py`, `logging_config.py` e `agent.build_graph()`. O grafo compilado
> ponta a ponta continua sendo a **T08**.

---

### T08 — [TECH] Teste E2E do fluxo principal e do cenário adversarial

- **Critério atendido:** 12 (teste de integração/aceitação/E2E) — §4.7
- **Branch sugerida:** `feature/qa-teste-e2e`

**Descrição**

O §4.7 exige pelo menos um teste de integração, aceitação ou E2E cobrindo
cenários relevantes, além da justificativa de um cenário prioritário por risco.
Implementar testes E2E que exercitem o grafo compilado de ponta a ponta com o
LLM e a rede simulados (fake LLM devolvendo tool calls determinísticas e
resposta HTTP fixa da Wikipédia), cobrindo os dois cenários exigidos pelo §4.1:
o fluxo principal e o cenário de risco.

**Checklist técnico**

- [ ] Criar fixtures de fake LLM e de resposta HTTP da Wikipédia
- [ ] Teste E2E do fluxo principal: destino + duração → busca → itinerário →
      arquivo `.md` gerado em diretório temporário com o conteúdo esperado
- [ ] Teste E2E do cenário adversarial: prompt injection bloqueado em
      `validate_input`, com o grafo indo direto para `END`, nenhuma tool
      executada e mensagem de recusa em português
- [ ] Teste E2E do cenário de falha: erro de rede na Wikipédia resultando em
      mensagem amigável, sem derrubar o processo (depende de T02)
- [ ] Teste E2E da retomada: memória com viagem incompleta pré-carregada
- [ ] Documentar em `docs/qa/priorizacao-testes.md` a justificativa do cenário
      considerado prioritário por risco, impacto e criticidade
- [ ] Garantir que os testes E2E rodem no CI sem rede e sem credenciais

---

### T09 — [DOCS] Code review com IA de uma alteração real e priorização por risco

- **Critério atendido:** 12 (IA em revisão de código) — §4.7
- **Branch sugerida:** `docs/qa-code-review-ia`

**Descrição**

O §4.7 exige o uso de IA para analisar pelo menos uma alteração real do projeto
(diff, trecho de código ou Pull Request) identificando problemas ou
oportunidades de melhoria. Executar uma revisão assistida por IA sobre um PR
real deste projeto (por exemplo, o PR da observabilidade ou o do n8n) e
registrar o resultado como evidência em `docs/qa/code-review-ia.md`, indicando
o que foi aceito, o que foi recusado e por quê.

**Conteúdo mínimo**

- [ ] Identificação do PR/diff revisado, com link e escopo da alteração
- [ ] Prompt utilizado na revisão, reproduzido na íntegra
- [ ] Saída da IA com os achados, classificados por severidade
- [ ] Decisão para cada achado: aceito, recusado ou adiado, com justificativa
- [ ] Evidência da correção aplicada (commit ou trecho de código antes/depois)
- [ ] Priorização dos achados por risco e impacto no domínio da aplicação

---

## Bloco D — DevOps inteligente

### E04 — [EPIC] DevOps inteligente e detecção de falhas

- **Tarefas:** T10, T11
- **Critérios atendidos:** 13 — §4.8

**Visão**

Automatizar a verificação de qualidade do projeto e transformar a saída do
pipeline em insumo de análise. Ao final deste epic, todo push e pull request
para `develop` e `main` deve executar lint, testes e validação de build, falhando
quando a cobertura ficar abaixo de 70%; e o projeto deve apresentar a análise
assistida por IA dos logs de duas etapas distintas do CI, com pelo menos uma
anomalia identificada e explicada e uma estimativa fundamentada de tendência ou
risco de falha.

**Escopo do Epic**

- Criar o workflow de CI no GitHub Actions com etapas separadas de lint, testes,
  cobertura e validação de build.
- Adotar o Ruff como ferramenta de lint (equivalente Python do ESLint, que não
  analisa código Python) e configurar suas regras no projeto.
- Aplicar o gate de cobertura mínima de 70% e publicar o relatório como
  artefato do workflow.
- Analisar com IA os logs de duas etapas distintas do pipeline, registrando
  prompts e saídas.
- Detectar e explicar uma anomalia real do projeto e produzir uma estimativa
  simples de tendência ou probabilidade de falha, com método e origem dos dados
  documentados.

---

### T10 — [TECH] Pipeline de CI com lint, testes e cobertura mínima de 70%

- **Critério atendido:** 13 — §4.8
- **Branch sugerida:** `feature/devops-pipeline-ci`

**Descrição**

O §4.8 exige um pipeline que execute lint, testes e build ou validação
equivalente; o deploy não é obrigatório. Criar um workflow do GitHub Actions
executado em push e pull request para `develop` e `main`, com etapas separadas e
logs legíveis (a separação em etapas é o que viabiliza a análise de logs de duas
etapas distintas exigida por T11).

> **Nota sobre a ferramenta de lint:** o ESLint é um linter de
> JavaScript/TypeScript e não analisa código Python — o ItinerAI é 100% Python.
> A ferramenta equivalente adotada é o **Ruff**, que cumpre o mesmo papel de
> validação de qualidade de código (lint + formatação). Caso a avaliação exija
> literalmente o ESLint, ele só faria sentido sobre arquivos JS/JSON auxiliares.

**Checklist técnico**

- [ ] Criar `.github/workflows/ci.yml` disparado em `push` e `pull_request`
      para `develop` e `main`
- [ ] Configurar Python 3.12.9 e cache de dependências
- [ ] Etapa de **lint**: adicionar o Ruff ao projeto, configurar as regras em
      `pyproject.toml` e executar `ruff check .` e `ruff format --check .`
- [ ] Etapa de **testes**: executar `pytest` com relatório de cobertura
- [ ] Etapa de **cobertura**: falhar o build quando a cobertura for inferior a
      **70%** (`--cov-fail-under=70`)
- [ ] Etapa de **build/validação**: validar a importação do grafo
      (`build_graph()`) e a integridade do `langgraph.json`
- [ ] Publicar o relatório de cobertura como artefato do workflow
- [ ] Garantir que o pipeline rode sem `GROQ_API_KEY` e sem acesso à rede
- [ ] Adicionar o badge de status do CI ao `README.md`

---

### T11 — [DOCS] Análise de logs de CI com IA, anomalia e estimativa de risco

- **Critério atendido:** 13 — §4.8
- **Branch sugerida:** `docs/devops-anomalias`

**Descrição**

Além de configurar o pipeline, o §4.8 exige usar IA para explicar os logs de
pelo menos duas etapas, detectar e explicar pelo menos uma anomalia e produzir
uma estimativa simples de tendência, risco ou probabilidade de falha, com dados
reais ou simulados e devidamente documentados. Registrar tudo em
`docs/evidencias/devops-analise-logs.md`, aproveitando execuções reais do CI
(inclusive as que falharam) e a trilha de auditoria de T05.

**Conteúdo mínimo**

- [ ] Log real de duas etapas distintas do CI (ex.: lint e testes), com a
      explicação produzida pela IA e o prompt utilizado
- [ ] Descrição de pelo menos uma anomalia detectada (ex.: falha recorrente de
      tool, latência alta na Wikipédia, aumento da taxa de erro do
      `tool_use_failed` do `llama-3.1-8b-instant`)
- [ ] Evidências que sustentam a anomalia: logs, métricas de latência da
      auditoria ou histórico de execuções do workflow
- [ ] Estimativa simples de tendência ou probabilidade de falha, com o método
      de cálculo explicitado e a origem dos dados (reais ou simulados)
- [ ] Conclusão justificada e ação de mitigação proposta ou aplicada

---

## Bloco E — Low-code e limites de autonomia

### E05 — [EPIC] Low-code e limites de autonomia

- **Tarefas:** T12, T13, T14
- **Critérios atendidos:** 14, 10 — §4.9, §4.5, §4.3

**Visão**

Entregar o itinerário fora do terminal por meio de uma automação low-code e, no
mesmo movimento, demonstrar os limites de autonomia do agente. Ao final deste
epic, o ItinerAI deve oferecer o envio do roteiro por e-mail através de um fluxo
no n8n acionado por webhook, sempre condicionado à **aprovação humana
explícita** — por ser uma ação externa e irreversível —, com a lógica principal
permanecendo na aplicação e o n8n atuando apenas como camada de integração,
conforme exige o §4.9.

**Escopo do Epic**

- Implementar a pergunta determinística de aprovação e a coleta validada do
  e-mail do destinatário, sem passar pelo LLM.
- Implementar o cliente do webhook do n8n, com payload tipado em pydantic,
  autenticação por token vindo do ambiente, timeout, retry limitado e fallback.
- Montar o fluxo no n8n com gatilho de webhook e saída observável (o e-mail com
  o roteiro).
- Garantir degradação silenciosa quando a integração não estiver configurada e
  mascaramento do e-mail nos logs e na auditoria.
- Exportar o workflow, documentar as instruções de reprodução no `README.md` e
  registrar as evidências de execução.

---

### T12 — [STORY] Receber o itinerário por e-mail ao final do processo

- **Critério atendido:** 14 (low-code), 10 (aprovação humana) — §4.9, §4.5
- **Branch sugerida:** `feature/low-code-n8n`

**User Story**

Como viajante que acabou de gerar um roteiro,
quero receber o itinerário por e-mail ao final do processo,
para ter o roteiro acessível fora do terminal e poder compartilhá-lo.

**Critérios de aceitação — BDD**

```
Cenário 1 — Envio aprovado pelo usuário

Dado que o agente concluiu a geração do arquivo do itinerário
Quando o agente perguntar se desejo receber o roteiro por e-mail
E eu responder "s" e informar um endereço de e-mail válido
Então a aplicação deve acionar o webhook do n8n com o itinerário
E o n8n deve enviar o e-mail com o roteiro
E o terminal deve confirmar o envio sem exibir o roteiro completo

Cenário 2 — Envio recusado pelo usuário

Dado que o agente concluiu a geração do arquivo do itinerário
Quando o agente perguntar se desejo receber o roteiro por e-mail
E eu responder "n"
Então nenhuma chamada externa deve ser realizada
E o fluxo deve encerrar normalmente informando apenas o arquivo criado

Cenário 3 — E-mail inválido

Dado que eu aceitei receber o roteiro por e-mail
Quando eu informar um endereço em formato inválido
Então a aplicação deve recusar o envio com uma mensagem em português
E não deve acionar o webhook

Cenário 4 — Falha na integração

Dado que eu aceitei receber o roteiro por e-mail
Quando o webhook do n8n estiver indisponível
Então a aplicação deve informar a falha de forma amigável
E o arquivo .md gerado deve permanecer disponível em output/
E o processo não deve ser encerrado com erro
```

**Objetivo**

- Entregar o itinerário em um canal externo ao terminal, sem mover a lógica
  principal para a ferramenta low-code
- Demonstrar a automação low-code exigida pelo §4.9, com gatilho, integração
  com a aplicação e saída observável (o e-mail)
- Demonstrar o limite de autonomia exigido pelo §4.5: o envio para um serviço
  externo é uma ação irreversível e só ocorre mediante **aprovação humana
  explícita**

**Escopo**

- `main.py` — pergunta determinística de aprovação (s/n) e coleta do e-mail ao
  final do turno em que o itinerário foi concluído
- Novo módulo de integração com o webhook do n8n (ver T13)
- `itinerai_agent/utils/validation.py` — validação do formato do e-mail por
  regex, no mesmo padrão determinístico já adotado
- `AgentState` — campo para o e-mail do destinatário, quando informado
- Fluxo n8n externo (gatilho webhook → nó de envio de e-mail)

**Resultado esperado**

- [ ] O agente pergunta sobre o envio apenas quando o itinerário foi realmente
      gerado
- [ ] Nenhum envio ocorre sem aprovação explícita do usuário
- [ ] O e-mail chega com o roteiro do arquivo `.md` gerado
- [ ] O e-mail do usuário nunca é registrado em log em texto puro
- [ ] A falha da integração não derruba a aplicação
- [ ] O comportamento está coberto por teste automatizado

---

### T13 — [TECH] Webhook de integração com o n8n

- **Critério atendido:** 14 (integração), 8 (validação e tratamento de falhas) — §4.9, §4.3
- **Branch sugerida:** `feature/low-code-n8n`

**Descrição**

Implementar o lado da aplicação da automação low-code: um cliente HTTP que envia
o payload do itinerário para um webhook do n8n, mantendo **toda a lógica
principal na aplicação** (o n8n atua apenas como orquestrador do envio do
e-mail, conforme o §4.9). A URL do webhook e eventuais credenciais devem vir de
variáveis de ambiente, nunca do código.

**Checklist técnico**

- [ ] Criar `itinerai_agent/utils/notifications.py` com a função de envio ao
      webhook, tipada e testável
- [ ] Definir o payload como modelo pydantic (`destino`, `num_days`,
      `destinatário`, `markdown` do roteiro, `run_id`)
- [ ] Ler `N8N_WEBHOOK_URL` e `N8N_WEBHOOK_TOKEN` do ambiente e documentá-las no
      `.env.example` sem valores reais
- [ ] Autenticar a chamada por header/token e nunca versionar o segredo
- [ ] Aplicar timeout, retry limitado e fallback, no mesmo padrão de T02
- [ ] Registrar o envio na trilha de auditoria e nos logs estruturados,
      mascarando o e-mail do destinatário
- [ ] Não executar nenhuma chamada quando a variável de ambiente não estiver
      configurada (degradação silenciosa e documentada)
- [ ] Cobrir com testes unitários: payload válido, ausência de configuração,
      timeout e resposta de erro do webhook

---

### T14 — [DOCS] Documentar o fluxo n8n e as instruções de reprodução

- **Critério atendido:** 14 (instruções de reprodução no README), 5 — §4.9, §5.2
- **Branch sugerida:** `docs/low-code-n8n`

**Descrição**

O §4.9 exige que o fluxo low-code possua instruções resumidas de reprodução no
`README.md`. Documentar o fluxo do n8n (gatilho, nós, saída), exportar o JSON do
workflow para o repositório e registrar as evidências de execução, de forma que
o avaliador consiga reproduzir a automação sem acesso à conta do estudante.

**Conteúdo mínimo**

- [ ] Exportação do workflow do n8n em `docs/low-code/n8n-workflow.json`, sem
      credenciais
- [ ] Descrição do gatilho (webhook), dos nós do fluxo e da saída produzida
      (e-mail)
- [ ] Diagrama ou captura de tela do fluxo montado no n8n
- [ ] Instruções resumidas de reprodução no `README.md`: importar o workflow,
      configurar a credencial de e-mail e apontar a `N8N_WEBHOOK_URL`
- [ ] Evidência de execução: captura do log do n8n e do e-mail recebido, com
      dados pessoais omitidos
- [ ] Explicação de por que a lógica principal permanece na aplicação e o n8n
      atua apenas como camada de integração

---

## Bloco F — Documentação, evidências e entrega

### E06 — [EPIC] Documentação, evidências e entrega

- **Tarefas:** T15, T16, T17, T18
- **Critérios atendidos:** 1, 2, 3, 5, 15 — §5.2, §5.3, §5.4, §5.5, §4.10

**Visão**

Tornar o projeto compreensível, reproduzível e avaliável por terceiros, e
concluir a entrega formal da avaliação. Ao final deste epic, o repositório deve
apresentar um `README.md` que cubra todas as seções obrigatórias do §5.2, a
documentação e as evidências organizadas em subpastas de `/docs`, ao menos um
ciclo de refinamento documentado no formato problema → alteração → resultado, um
quadro Kanban que reflita o processo real de desenvolvimento e o vídeo de
demonstração publicado. Este epic concentra 2,75 pontos da avaliação, dos quais
1,00 não exige nenhuma linha de código.

**Escopo do Epic**

- Reescrever o `README.md` acrescentando classificação da solução, diagrama de
  arquitetura atualizado, seções de QA, observabilidade, DevOps e low-code, os
  dois cenários de uso e o link do vídeo.
- Reorganizar `/docs` em `prompts/`, `qa/`, `evidencias/` e `low-code/`, com
  índice de navegação.
- Documentar as instruções de sistema do agente e os ciclos de refinamento já
  vividos no projeto, como a recuperação de tool calls vazadas como texto.
- Criar o GitHub Project com as seis colunas exigidas, os epics e as issues, e
  mantê-lo atualizado durante todo o desenvolvimento.
- Gravar, publicar como não listado e referenciar o vídeo de demonstração.

---

### T15 — [DOCS] Reescrever o README.md conforme o item 5.2

- **Critério atendido:** 5 — §5.2
- **Branch sugerida:** `docs/readme-video`

**Descrição**

O `README.md` atual documenta bem o mini-projeto, mas não cobre as seções
obrigatórias do §5.2 desta avaliação. Reescrevê-lo mantendo o que já está bom
(problema, fluxo, ferramentas, validação, memória, execução) e acrescentando as
seções ausentes, deixando explícito o que foi mantido, refatorado e evoluído em
relação ao mini-projeto.

**Conteúdo mínimo**

- [ ] Descrição da solução, incluindo o que foi mantido e o que evoluiu em
      relação ao mini-projeto
- [ ] Classificação explícita da solução (agente, workflow determinístico ou
      híbrido) com justificativa
- [ ] Diagrama de arquitetura atualizado, destacando nodes, rotas, a
      paralelização de T01 e os componentes envolvidos
- [ ] Seção de tool e integração, incluindo a integração externa via webhook
- [ ] Seção de contexto e memória (SQLite, retomada e uso das informações)
- [ ] Seção de segurança e autonomia: proteção de credenciais, validações,
      limites de autonomia, aprovação humana e comportamento diante de prompt
      injection
- [ ] Instalação e execução completas, com todas as variáveis do `.env.example`
      e o comando de execução dos testes
- [ ] Seção de QA, observabilidade e DevOps com as evidências e links para
      `/docs`
- [ ] Seção de automação low-code com gatilho, relação com a aplicação e saída
- [ ] Dois cenários de uso documentados: fluxo principal e cenário de risco,
      com entrada, comportamento esperado e resultado
- [ ] Seção de análise crítica, limitações, evoluções futuras e link do vídeo
- [ ] Badge do pipeline de CI

---

### T16 — [DOCS] Organizar `/docs` e registrar o ciclo de refinamento

- **Critério atendido:** 15 — §5.4, §4.10
- **Branch sugerida:** `docs/evidencias`

**Descrição**

O §5.4 pede que a documentação e as evidências fiquem organizadas em `/docs`
com subpastas como `/docs/prompts`, `/docs/qa` e `/docs/evidencias`; hoje a
pasta é plana. Além disso, o §4.10 e o critério 15 exigem pelo menos um ciclo
documentado de refinamento de prompt ou comportamento do agente no formato
problema observado → alteração realizada → resultado obtido. O projeto já possui
um caso forte e real para isso: a recuperação de tool calls "vazadas" como texto
pelo `llama-3.1-8b-instant` (`_repair_leaked_response`).

**Conteúdo mínimo**

- [ ] Reorganização de `/docs` em `prompts/`, `qa/`, `evidencias/` e
      `low-code/`, com os arquivos atuais movidos e os links atualizados
- [ ] `docs/prompts/system-prompts.md` com as instruções de sistema do agente
      (`AGENT_SYSTEM_PROMPT` e prompts de extração) e sua finalidade
- [ ] Ciclo de refinamento nº 1 — tool calls vazadas como texto: problema
      observado, alteração aplicada (`_repair_leaked_response` + ajuste do
      system prompt) e resultado obtido, com evidência antes/depois
- [ ] Ciclo de refinamento nº 2 — redução do escopo de ferramentas para não
      sobrecarregar o modelo fraco, com a justificativa da decisão
- [ ] Índice em `docs/README.md` apontando para todas as evidências produzidas
      (observabilidade, QA, DevOps, low-code, prompts)

---

### T17 — [DOCS] Gravar e publicar o vídeo de demonstração

- **Critério atendido:** 1 — §5.5
- **Branch sugerida:** `docs/readme-video`

**Descrição**

Gravar o vídeo de demonstração com duração recomendada de até 10 minutos e
limite máximo de 12, publicá-lo no YouTube como **não listado**, inserir o link
no `README.md` e submetê-lo no AVA. Este é o item de maior peso individual da
avaliação (1,00 ponto) e depende da conclusão das demais tarefas, portanto deve
ser a última a ser executada.

**Conteúdo mínimo**

- [ ] Roteiro escrito seguindo a sugestão de tempos do §5.5, salvo em
      `docs/evidencias/roteiro-video.md`
- [ ] Demonstração do problema, objetivo e classificação da solução
- [ ] Visão resumida da arquitetura e das integrações
- [ ] Dois cenários ao vivo: fluxo principal e cenário de risco/falha
- [ ] Evidência de segurança e de aprovação humana antes do envio do e-mail
- [ ] Uma evidência de QA (execução dos testes e cobertura)
- [ ] Pipeline, análise de logs, anomalia e estimativa de risco
- [ ] Demonstração resumida do fluxo n8n e do e-mail recebido
- [ ] Limitações e melhorias futuras
- [ ] Vídeo publicado como não listado, com o link inserido no `README.md`

---

### T18 — [TECH] Criar e manter o quadro Kanban no GitHub Project

- **Critério atendido:** 2 e 3 (1,00 ponto somado) — §5.3
- **Branch sugerida:** — (tarefa de processo, sem branch)

**Descrição**

O §5.3 exige um GitHub Project com as colunas Backlog, A Fazer, Em Andamento,
Bloqueado, Em Revisão e Concluído, com cards que reflitam o processo real de
desenvolvimento. O critério 3 penaliza explicitamente cards criados apenas ao
final, portanto o quadro precisa ser criado **antes** do início das
implementações e movimentado ao longo do trabalho. Esta é a primeira tarefa a
ser executada.

**Checklist técnico**

- [ ] Criar o GitHub Project no formato Kanban com as seis colunas exigidas
- [ ] Criar as 6 issues de epic (E01 a E06) com o `epic_template.yml`, antes das
      tarefas
- [ ] Criar uma issue por tarefa deste documento (T01 a T17), usando o template
      correspondente ao tipo de cada uma
- [ ] Vincular cada tarefa ao seu epic (sub-issues ou referência ao número da
      issue do epic na descrição), conforme o índice dos epics
- [ ] Vincular cada card à branch e ao pull request correspondentes
- [ ] Movimentar os cards ao longo do desenvolvimento, refletindo o andamento
      real
- [ ] Adicionar o professor como colaborador do repositório e conceder acesso ao
      quadro
- [ ] Garantir a coerência entre cards, branches, commits e PRs

---

### T19 — [DOCS] Versionar o planejamento do M2.2

- **Critérios atendidos:** 4 e 5 — §5.4
- **Branch sugerida:** `docs/planejamento-m2-2`

**Descrição**

Os artefatos de planejamento do M2.2 já estão na árvore de trabalho, mas ainda
não foram versionados. Enquanto isso não acontecer, o backlog não é rastreável,
os links para `docs/tasks.md` nas issues do board ficam quebrados e o histórico
não registra o início do M2.2. As alterações estão hoje na `main`, mas o §5.4
exige o fluxo `develop → feature/* → develop → main` e proíbe concentrar o
desenvolvimento diretamente na `main` — portanto o trabalho deve ser levado para
uma branch criada a partir da `develop` antes de qualquer commit.

Arquivos envolvidos: os 4 templates em `docs/issues-templates/` e o
`docs/tasks.md` (novos, não rastreados), além de `docs/requisitos.md`
(atualizado com o enunciado do M2.2) e `docs/prompts.md`.

**Conteúdo mínimo**

- [ ] Criar a branch `docs/planejamento-m2-2` a partir da `develop`, levando as
      alterações atualmente na `main`
- [ ] Versionar os 4 templates de issue em `docs/issues-templates/` (epic, docs,
      tech e user story)
- [ ] Versionar `docs/tasks.md` com o backlog completo do M2.2
- [ ] Commitar a atualização de `docs/requisitos.md` com o enunciado do M2.2
- [ ] Commitar a atualização de `docs/prompts.md`
- [ ] Usar mensagens de commit semânticas, separando os commits por assunto
- [ ] Confirmar que `.env`, `itinerai_memory.db`, `output/` e qualquer
      credencial permanecem fora do versionamento
- [ ] Abrir Pull Request para a `develop`, vinculando este card
- [ ] Validar que os links para `docs/tasks.md` nas issues do board passam a
      resolver após o merge

---

## Ordem de execução sugerida

1. **T18** (E06) — quadro, epics e issues criados primeiro, para que a
   movimentação dos cards seja real
2. **T19** (E06) — versionar o planejamento, inaugurando o fluxo
   `develop → feature/* → develop → main` do §5.4
3. **T03, T07, T10** (E01, E03, E04) — base de qualidade: configuração por
   ambiente, testes e CI
4. **T01, T02** (E01) — evolução do grafo e resiliência
5. **T04, T05** (E02) — observabilidade (depende de T02 para registrar retries)
6. **T13, T12** (E05) — integração com o n8n e a experiência de envio por e-mail
7. **T08** (E03) — testes E2E cobrindo os fluxos já finalizados
8. **T06, T09, T11, T14** (E02, E03, E04, E05) — evidências, que exigem execuções
   reais já disponíveis
9. **T16, T15** (E06) — organização da documentação e README final
10. **T17** (E06) — vídeo, por último

Os epics E01 a E05 são concluídos quando todas as suas tarefas são fechadas; o
E06 permanece aberto até o final do projeto, pois T18 (quadro) e T17 (vídeo)
acompanham todo o ciclo de desenvolvimento.
