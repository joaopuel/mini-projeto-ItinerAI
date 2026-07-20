# ItinerAI

## Visão geral do produto

ItinerAI é um agente de IA capaz de criar itinerários de viagem. Toda a
interação com o agente acontece via terminal — **não há interface gráfica**.

Funcionalidades do agente:

- Pesquisar pontos turísticos do destino informado (via Wikipédia).
- Pesquisar eventos e festivais tradicionais do destino (via Wikipédia).
  Como a Wikipédia é um texto estático, esses eventos são tratados como
  **sugestões sem data exata**, sempre acompanhados de um aviso para o usuário
  confirmar dia/horário no site oficial de cada evento.
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

## Ferramentas do agente (`tools.py`)

Todas já implementadas e registradas em `nodes.py`:

- `search_tourist_attractions(destination)` — busca na Wikipédia
  (`Tourism in <destino>` → `<destino>`).
- `search_events_and_festivals(destination, period=None)` — busca na Wikipédia
  (`Festivals in <destino>` → `Culture of <destino>` → `<destino>`). Retorna
  eventos como sugestões sem data + um `disclaimer` obrigatório.
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
│   │   ├── nodes.py        # funções de nó do grafo
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
  obtém na conversa e passa direto para `build_itinerary`. Também é o lugar dos
  modelos de domínio usados pelas tools (`TouristAttraction`,
  `TraditionalEvent`, `Itinerary`/`ItineraryDay`/`ItinerarySlot`). Atrações e
  eventos têm um campo `location` (exato ou provável) usado no agrupamento por
  proximidade.
- `tools.py` concentra as ferramentas expostas ao agente (pesquisa de pontos
  turísticos, pesquisa de eventos/festivais, geração do arquivo `.md`) — ver
  "Ferramentas do agente" acima.
- `nodes.py` concentra os nós do grafo — ver "Arquitetura do grafo
  (tool-calling)" acima para o padrão atual de roteamento.
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
