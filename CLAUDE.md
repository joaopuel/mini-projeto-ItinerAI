# ItinerAI

## Visão geral do produto

ItinerAI é um agente de IA capaz de criar itinerários de viagem. Toda a
interação com o agente acontece via terminal — **não há interface gráfica**.

Funcionalidades do agente:

- Pesquisar pontos turísticos do destino informado.
- Pesquisar eventos/shows no destino informado dentro do período de férias
  fornecido.
- Criar um itinerário da viagem, detalhando a viagem dia a dia.
- Gerar um arquivo `.md` com o itinerário criado.

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

Novas funcionalidades (busca de eventos/shows, montagem do itinerário,
geração do `.md`) devem seguir o mesmo padrão: implementar como tool pura em
`tools.py` e registrá-la na lista de tools vinculada ao LLM em `nodes.py`,
em vez de criar nós fixos por etapa.

## Estrutura do projeto

Estrutura baseada na organização recomendada pela documentação do LangGraph
(ver [docs/application-structure.md](docs/application-structure.md)), variante
`requirements.txt`:

```
mini-projeto-ItinerAI/
├── itinerai_agent/         # todo o código do agente
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── tools.py        # tools: busca de pontos turísticos, busca de eventos/shows, geração do .md
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
- `state.py` deve definir o estado do grafo com `pydantic.BaseModel`,
  incluindo ao menos: destino, período de férias, pontos turísticos
  encontrados, eventos encontrados e o itinerário dia a dia resultante.
  Também é o lugar para os modelos pydantic de dados de domínio usados pelas
  tools (ex.: `TouristAttraction`).
- `tools.py` concentra as ferramentas expostas ao agente (pesquisa de pontos
  turísticos, pesquisa de eventos/shows, geração do arquivo `.md`).
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
- Nomes de arquivos, pastas, funções e variáveis em inglês; mensagens
  voltadas ao usuário final (saída no terminal, conteúdo do `.md` gerado)
  em português.

## Regras obrigatórias

- **Priorize sempre as funcionalidades/ferramentas já disponibilizadas pelo
  harness do VSCode** (edição de arquivos, busca, etc.) em vez de comandos de
  terminal equivalentes, sempre que possível.
- **Antes de executar qualquer comando no terminal, é obrigatório, sem
  exceções, descrever exatamente o que o comando faz e qual o seu objetivo, e
  solicitar a aprovação do usuário antes de rodá-lo.** Isso vale mesmo para
  comandos aparentemente simples ou de baixo risco.
