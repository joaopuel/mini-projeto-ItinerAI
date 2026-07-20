# ItinerAI

## Visão geral do produto

ItinerAI é um agente de IA capaz de criar itinerários de viagem. Toda a
interação com o agente acontece via terminal — **não há interface gráfica**.

Funcionalidades do agente:

- Validar a mensagem do usuário antes de processá-la: bloquear tentativas de
  prompt injection, mensagens em scripts não-latinos (mandarim/híndi) e
  URLs/links enviados pelo usuário, respondendo com um aviso em português.
- Pesquisar pontos turísticos do destino informado (via Wikipédia).
- Pesquisar eventos e festivais tradicionais do destino (via Wikipédia).
  Como a Wikipédia é um texto estático, esses eventos são tratados como
  **sugestões sem data exata**, sempre acompanhados de um aviso para o usuário
  confirmar dia/horário no site oficial de cada evento.
- Descobrir a duração da viagem: quando o usuário informa as datas de ida e
  volta em vez do número de dias, validar as datas (futuras e na ordem correta)
  e calcular a quantidade de dias (contagem inclusiva) usada na montagem do
  roteiro.
- Montar um itinerário dia a dia (manhã/tarde/noite), agrupando atrações
  próximas para reduzir deslocamento.
- Gerar um arquivo `.md` com o itinerário em `output/`. **O roteiro não é
  exibido no terminal** — o agente apenas informa o nome do arquivo criado.

Não introduza funcionalidades, integrações ou tecnologias além das descritas
neste documento sem alinhar antes com o usuário.

## Stack técnica

- **Python 3.12.9**
- **LangGraph** — orquestração do agente como um grafo de estados.
- **pydantic** — definição do estado do grafo e de todos os modelos de dados
  (ex.: pontos turísticos, eventos, dias do itinerário).
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
  (`route_after_validation`), segue para `call_llm` quando a entrada é válida
  ou vai direto para `END` (com a mensagem de recusa já inserida) quando viola
  uma regra. Ver "Validação de entrada" abaixo.
- `call_llm` invoca o LLM com as tools de `tools.py` vinculadas via
  `bind_tools`.
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

## Ferramentas do agente (`tools.py`)

Todas já implementadas e registradas em `nodes.py`:

- `search_tourist_attractions(destination)` — busca na Wikipédia
  (`Tourism in <destino>` → `<destino>`).
- `search_events_and_festivals(destination, period=None)` — busca na Wikipédia
  (`Festivals in <destino>` → `Culture of <destino>` → `<destino>`). Retorna
  eventos como sugestões sem data + um `disclaimer` obrigatório.
- `calculate_trip_days(start_date, end_date)` — valida as datas de ida/volta e
  calcula a duração da viagem. Usada quando o usuário informa as datas em vez do
  número de dias. Validação **100% determinística** (stdlib `datetime`, sem LLM):
  aceita datas em ISO (`AAAA-MM-DD`) e formatos BR (`DD/MM/AAAA`), exige que
  ambas sejam posteriores à data atual e que a ida seja anterior ou igual à
  volta. Em caso de falha, retorna `valid=False` + `message` de recusa em
  português; em caso de sucesso, retorna `num_days` (contagem **inclusiva**:
  conta o dia de chegada e o de saída) para alimentar o `build_itinerary`. É uma
  tool pura, não altera o estado.
- `build_itinerary(destination, num_days)` — monta o roteiro e **grava o `.md`**
  em `output/`. As atrações/eventos vêm do estado, injetados em `call_tools`, e
  ficam **ocultos do modelo via `InjectedToolArg`** — o schema exposto ao LLM tem
  só `destination` e `num_days`. A tool devolve apenas o aviso do arquivo criado
  (o roteiro completo vai para `state.itinerary`, não para o terminal).

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

## Estrutura do projeto

Estrutura baseada na organização recomendada pela documentação do LangGraph
(ver [docs/application-structure.md](docs/application-structure.md)), variante
`requirements.txt`:

```
mini-projeto-ItinerAI/
├── itinerai_agent/         # todo o código do agente
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── tools.py        # tools: busca de pontos turísticos, busca de eventos/festivais, geração do .md
│   │   ├── validation.py   # validação de entrada do usuário (anti prompt injection, idioma, URLs)
│   │   ├── prompts.py      # prompts do agente e das extrações
│   │   ├── nodes.py        # funções de nó do grafo (validação, chamada ao LLM, execução de tools)
│   │   └── state.py        # definição do estado do grafo (modelos pydantic)
│   ├── __init__.py
│   └── agent.py            # construção/compilação do StateGraph
├── docs/
│   └── application-structure.md
├── output/                 # itinerários .md gerados pelo agente (não versionado)
├── main.py                 # ponto de entrada: loop de chat via terminal
├── .env                    # variáveis de ambiente locais (não versionado)
├── requirements.txt        # dependências do projeto
└── langgraph.json          # arquivo de configuração do LangGraph
```

- Todo o código do agente fica dentro de `itinerai_agent/`, seguindo o padrão
  `my_agent` da documentação do LangGraph.
- `state.py` define o estado do grafo (`AgentState`) com `pydantic.BaseModel`:
  `messages`, `destination`, `tourist_attractions`, `traditional_events` e
  `itinerary`. A duração da viagem (`num_days`) não fica no estado — o agente a
  obtém na conversa (diretamente ou via `calculate_trip_days`, a partir das
  datas de ida/volta) e passa direto para `build_itinerary`. Também é o lugar dos
  modelos de domínio usados pelas tools (`TouristAttraction`,
  `TraditionalEvent`, `Itinerary`/`ItineraryDay`/`ItinerarySlot`). Atrações e
  eventos têm um campo `location` (exato ou provável) usado no agrupamento por
  proximidade.
- `tools.py` concentra as ferramentas expostas ao agente (pesquisa de pontos
  turísticos, pesquisa de eventos/festivais, geração do arquivo `.md`) — ver
  "Ferramentas do agente" acima.
- `nodes.py` concentra os nós do grafo — ver "Arquitetura do grafo
  (tool-calling)" acima para o padrão atual de roteamento.
- `validation.py` concentra a validação de entrada do usuário (funções puras de
  regex + mensagens de recusa) — ver "Validação de entrada" acima.
- Itinerários gerados são salvos como arquivo `.md` em `output/`.

## Configuração de ambiente

- Requer Python 3.12.9.
- Variável de ambiente obrigatória: `GROQ_API_KEY` (carregada via `.env` em
  desenvolvimento local, nunca commitada).
- `.env` e `output/` devem estar no `.gitignore`.

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
