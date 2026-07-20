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
- **Groq** — modelo `llama-3.1-8b-instant` como LLM do agente.
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
  `bind_tools`; também recupera as tool calls que o modelo fraco eventualmente
  "vaza" como texto (ver "Robustez com o `llama-3.1-8b-instant`" abaixo).
- Uma aresta condicional (`should_call_tools`) verifica se a resposta do LLM
  pediu alguma tool: se sim, roteia para `call_tools`; se não, vai para
  `END`.
- `call_tools` executa a(s) tool(s) pedidas e volta para `call_llm`, que
  formula a resposta final ao usuário (inclusive mensagens de "não
  encontrado").

Qualquer nova funcionalidade deve seguir o mesmo padrão: implementar como
tool em `tools.py` e registrá-la na lista de tools vinculada ao LLM em
`nodes.py`, em vez de criar nós fixos por etapa.

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

- **Detecção 100% por regex, sem nenhuma chamada ao LLM.** O
  `llama-3.1-8b-instant` é fraco; a validação precisa ser determinística,
  barata e previsível, sem sobrecarregar o modelo.
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
numa nova execução caso a busca de atrações ou a geração do roteiro falhe (e
falham de fato: uma falha de rede em `tools.py` propaga e derruba o processo).

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
  (`Tourism in <destino>` → `<destino>`).
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

## Robustez com o `llama-3.1-8b-instant`

O modelo é pequeno e frágil em tool-calling. Regras aprendidas (não remover sem
motivo — cada uma corrige um `tool_use_failed`/crash real):

- O LLM de extração (`_extraction_llm`) usa `temperature=0`; os prompts de
  extração pedem no máximo ~15 itens e proíbem repetição (evita loops que
  truncam o JSON).
- Falhas de geração estruturada são tratadas: as extrações caem para vazio e
  `call_llm` responde com mensagem amigável, em vez de derrubar o agente.
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
  desconhecida), troca o texto cru por um aviso amigável.
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
│   │   ├── tools.py        # tools: busca de pontos turísticos, geração do .md
│   │   ├── validation.py   # validação de entrada do usuário (anti prompt injection, idioma, URLs)
│   │   ├── memory.py       # memória persistente da última viagem em SQLite (retomada)
│   │   ├── prompts.py      # prompts do agente e das extrações
│   │   ├── nodes.py        # funções de nó do grafo (validação, persistência, chamada ao LLM, execução de tools)
│   │   └── state.py        # definição do estado do grafo (modelos pydantic)
│   ├── __init__.py
│   └── agent.py            # construção/compilação do StateGraph
├── docs/
│   └── application-structure.md
├── output/                 # itinerários .md gerados pelo agente (não versionado)
├── main.py                 # ponto de entrada: loop de chat via terminal
├── .env                    # variáveis de ambiente locais (não versionado)
├── itinerai_memory.db      # memória persistente SQLite da última viagem (não versionado)
├── requirements.txt        # dependências do projeto
└── langgraph.json          # arquivo de configuração do LangGraph
```

- Todo o código do agente fica dentro de `itinerai_agent/`, seguindo o padrão
  `my_agent` da documentação do LangGraph.
- `state.py` define o estado do grafo (`AgentState`) com `pydantic.BaseModel`:
  `messages`, `destination`, `num_days`, `tourist_attractions` e `itinerary`. A
  duração (`num_days`) fica no estado — além de ser passada a `build_itinerary`
  — para poder ser persistida pela memória e permitir a retomada da conversa
  (populada em `call_tools` a partir de `build_itinerary`). Também é o lugar dos
  modelos de domínio usados pelas tools (`TouristAttraction`,
  `Itinerary`/`ItineraryDay`). As atrações têm um campo `location` (exato ou
  provável) usado no agrupamento por proximidade.
- `tools.py` concentra as ferramentas expostas ao agente (pesquisa de pontos
  turísticos, geração do arquivo `.md`) — ver "Ferramentas do agente" acima.
- `nodes.py` concentra os nós do grafo — ver "Arquitetura do grafo
  (tool-calling)" acima para o padrão atual de roteamento.
- `validation.py` concentra a validação de entrada do usuário (funções puras de
  regex + mensagens de recusa) — ver "Validação de entrada" acima.
- `memory.py` concentra a memória persistente em SQLite (funções puras
  `init_db`/`save_trip_memory`/`load_trip_memory` + o modelo `TripMemory`) —
  ver "Memória persistente" acima.
- Itinerários gerados são salvos como arquivo `.md` em `output/`.

## Configuração de ambiente

- Requer Python 3.12.9.
- Variável de ambiente obrigatória: `GROQ_API_KEY` (carregada via `.env` em
  desenvolvimento local, nunca commitada).
- `.env`, `output/` e o banco `itinerai_memory.db` devem estar no `.gitignore`.
- A memória persistente usa `sqlite3` da stdlib — nenhuma dependência extra no
  `requirements.txt`.

## Convenções de código

- Use type hints em todas as funções públicas.
- Toda estrutura de dados trocada entre nós do grafo deve ser um modelo
  `pydantic`, não `dict` solto.
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
