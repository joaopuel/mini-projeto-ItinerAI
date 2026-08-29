# ItinerAI

**Agente de IA, construído com LangGraph, que cria itinerários de viagem dia a
dia a partir de um destino e uma duração — tudo pelo terminal.** O agente
pesquisa pontos turísticos na Wikipédia, agrupa as atrações por proximidade e
gera um arquivo `.md` pronto para você levar na mala.

> Projeto do Mini-Projeto Avaliativo do Módulo 2 da disciplina *IA para
> Desenvolvedores*.

## Sumário

- [O problema](#o-problema)
- [Objetivo do agente](#objetivo-do-agente)
- [Stack técnica](#stack-técnica)
- [Fluxo com LangGraph](#fluxo-com-langgraph)
- [Ferramentas do agente](#ferramentas-do-agente)
- [Validação de entrada](#validação-de-entrada)
- [Memória persistente](#memória-persistente)
- [Como executar](#como-executar)
- [Exemplo de entrada e saída](#exemplo-de-entrada-e-saída)
- [Principais decisões tomadas](#principais-decisões-tomadas)
- [Limitações da solução](#limitações-da-solução)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Prompts e apresentação](#prompts-e-apresentação)

## O problema

Planejar um roteiro de viagem dá trabalho: é preciso pesquisar o que visitar no
destino, decidir quantas atrações cabem em cada dia e, idealmente, agrupar
lugares próximos para não perder tempo em deslocamento. É uma tarefa repetitiva,
manual e fácil de fazer mal.

O **ItinerAI** automatiza esse processo. O usuário informa apenas o destino e por
quantos dias vai viajar, e o agente cuida do resto: pesquisa os pontos
turísticos, organiza um roteiro dia a dia e entrega um arquivo pronto.

## Objetivo do agente

A partir de uma **entrada** simples, produzir uma **saída** útil e estruturada:

- **Entrada:** o destino e a duração da viagem em dias, coletados pela conversa
  no terminal — o agente pede **uma informação por vez**, na ordem (1º destino,
  2º duração).
- **Processamento:** pesquisa os pontos turísticos do destino na Wikipédia e
  monta um itinerário dia a dia, agrupando atrações próximas (no máximo 3 por
  dia) para reduzir o deslocamento.
- **Saída:** um arquivo Markdown em `output/`, no padrão
  `itinerario-<destino>-<n>-dias.md`. **O roteiro não é impresso no terminal** —
  o agente apenas informa o nome do arquivo criado.

### Por que é um agente?

O ItinerAI não é um script de etapas fixas: ele é um **agente de tool-calling no
estilo ReAct**, orquestrado como um grafo de estados no LangGraph. O modelo
**decide** quando pedir mais dados ao usuário, quando pesquisar atrações e quando
montar o roteiro, chamando ferramentas de forma autônoma e reagindo aos
resultados — mantendo o contexto da conversa em um estado compartilhado.

## Stack técnica

| Tecnologia | Uso |
| --- | --- |
| **Python 3.12.9** | Linguagem base |
| **LangGraph** | Orquestração do agente como grafo de estados (`StateGraph`) |
| **pydantic** | Estado do grafo e todos os modelos de dados |
| **Groq** — `openai/gpt-oss-120b` | LLM do agente e da extração (via `langchain-groq`) |
| **requests + beautifulsoup4** | Busca e parsing das páginas da Wikipédia |
| **sqlite3** (stdlib) | Memória persistente da última viagem |

A autenticação com a Groq é feita pela variável de ambiente `GROQ_API_KEY`,
carregada de um arquivo `.env` (nunca versionada).

## Fluxo com LangGraph

O agente é um `StateGraph` (`itinerai_agent/agent.py`) que segue um loop de
tool-calling — validação e memória rodam antes, e o LLM entra em loop com as
ferramentas até formular a resposta final:

```
                START
                  │
                  ▼
          ┌─────────────────┐
          │  validate_input │  valida a mensagem por regex (anti-injeção,
          └─────────────────┘  idioma, URL) — sem chamar o LLM
                  │
         route_after_validation
            ┌─────┴─────┐
        (inválida)   (válida)
            │             │
            ▼             ▼
           END   ┌─────────────────┐
                 │  persist_memory │  salva a viagem no SQLite (antes das
                 └─────────────────┘  buscas que podem falhar)
                           │
                           ▼
                 ┌─────────────────┐
              ┌─▶│    call_llm     │  invoca o LLM com as tools (bind_tools)
              │  └─────────────────┘
              │            │
              │     should_call_tools
              │       ┌────┴────┐
              │   (sem tool) (com tool)
              │       │         │
              │       ▼         ▼
              │      END  ┌─────────────┐
              └──────────│  call_tools │  executa as ferramentas pedidas
                         └─────────────┘
```

**Estado compartilhado** (`AgentState`, em `itinerai_agent/utils/state.py`):
`messages`, `destination`, `num_days`, `tourist_attractions` e `itinerary`.
Toda estrutura trocada entre nós é um modelo pydantic (nunca `dict` solto).

Os nós ficam em `itinerai_agent/utils/nodes.py`:

- **`validate_input`** — nó de entrada; valida a última mensagem do usuário.
- **`persist_memory`** — salva o que já se sabe da viagem, antes das buscas.
- **`call_llm`** — chama o LLM com as ferramentas vinculadas; também recupera
  chamadas de ferramenta que o modelo eventualmente "vaza" como texto.
- **`call_tools`** — executa as ferramentas e devolve o controle ao LLM.

## Ferramentas do agente

As ferramentas ficam em `itinerai_agent/utils/tools.py` e são vinculadas ao LLM
em `nodes.py`:

- **`search_tourist_attractions(destination)`** — busca pontos turísticos do
  destino na Wikipédia (tenta a página `Tourism in <destino>` e, se não existir,
  a página `<destino>`), retornando uma lista estruturada de atrações.
- **`build_itinerary(destination, num_days)`** — monta o roteiro e **grava o
  arquivo `.md`** em `output/`. Agrupa as atrações por proximidade e as
  distribui pelos dias (**no máximo 3 por dia**). Devolve apenas a mensagem de
  confirmação com o nome do arquivo — o roteiro completo vai para o estado, não
  para o terminal.

> A lista de atrações já encontradas é injetada em `build_itinerary` a partir do
> estado e fica **oculta do modelo** via `InjectedToolArg` — o schema exposto ao
> LLM tem só `destination` e `num_days`. Isso mantém a chamada de ferramenta
> pequena e estável para um modelo pequeno.

## Validação de entrada

Antes de a mensagem chegar ao LLM, o nó `validate_input` a inspeciona
(`itinerai_agent/utils/validation.py`) e bloqueia três tipos de entrada,
respondendo sempre com um aviso em português:

1. **Prompt injection** (ex.: *"ignore as instruções anteriores"*) — padrões nos
   6 idiomas mais falados (português, inglês, espanhol, francês, mandarim e
   híndi).
2. **Idioma não suportado** — mensagens em scripts não-latinos (mandarim/CJK e
   híndi/devanágari).
3. **URLs/links** enviados pelo usuário — o agente nunca os acessa (a fonte de
   dados é sempre a Wikipédia, via as ferramentas).

A detecção é **100% por regex, sem nenhuma chamada ao LLM** — determinística,
barata e previsível, para não sobrecarregar o modelo fraco.

## Memória persistente

O agente guarda em **SQLite** (`itinerai_memory.db`, na raiz do projeto) os dados
da **última** viagem — destino, duração e se o itinerário já foi gerado. A
persistência usa apenas o `sqlite3` da stdlib (sem dependência extra) e um
**registro único** (a viagem mais recente sobrescreve a anterior).

Na próxima execução, o `main.py` carrega essa memória e, se houver uma viagem
salva, **mostra-a** e oferece:

- **retomá-la**, se ficou incompleta (ex.: uma falha de rede na busca derrubou o
  processo); ou
- **refazê-la**, se o itinerário já havia sido concluído.

Ao aceitar, o estado é pré-preenchido e uma mensagem sintética reafirma a viagem,
para o agente refazer a busca e o roteiro sem o usuário redigitar nada.

## Como executar

### Pré-requisitos

- **Python 3.12.9**
- Uma **chave de API da Groq** (`GROQ_API_KEY`) — crie uma gratuitamente em
  [console.groq.com](https://console.groq.com).

### Passo a passo

1. **Clone o repositório e entre na pasta:**

   ```bash
   git clone https://github.com/joaopuel/mini-projeto-ItinerAI.git
   cd mini-projeto-ItinerAI
   ```

2. **Crie e ative um ambiente virtual:**

   ```powershell
   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   ```bash
   # Linux / macOS
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure a chave da Groq.** Copie o arquivo de exemplo e preencha o valor:

   ```bash
   cp .env.example .env
   ```

   Depois edite o `.env`:

   ```dotenv
   GROQ_API_KEY=coloque_sua_chave_aqui
   ```

   > O `.env` está no `.gitignore` e **nunca** deve ser versionado. O
   > `.env.example` traz apenas o nome da variável, sem valor.

5. **Rode o agente:**

   ```bash
   python main.py
   ```

   Converse pelo terminal e digite `sair` para encerrar. Os itinerários gerados
   ficam na pasta `output/`.

## Exemplo de entrada e saída

### Conversa no terminal

```text
ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem.
(digite 'sair' para encerrar)
ItinerAI: Qual o seu próximo destino?
Você: Quero viajar para Lisboa
ItinerAI: Boa escolha! Qual a duração (dias) da sua viagem?
Você: 3 dias
ItinerAI: Prontinho! O arquivo itinerario-lisboa-3-dias.md com o itinerário
para seu destino foi criado em output/. Boa viagem! ✈️
```

### Arquivo gerado (`output/itinerario-lisboa-3-dias.md`)

```markdown
# Roteiro de viagem — Lisboa

*3 dias de viagem*

## Dia 1 — Centro Histórico

- Castelo de São Jorge
- Sé de Lisboa
- Alfama

## Dia 2 — Belém

- Mosteiro dos Jerónimos
- Torre de Belém
- Padrão dos Descobrimentos

## Dia 3 — Baixa

- Praça do Comércio
- Elevador de Santa Justa
- Rossio
```

### Entrada bloqueada pela validação

```text
Você: https://meu-blog-de-viagens.com/roteiro-lisboa
ItinerAI: Por segurança, não acesso links ou URLs enviados por usuários. Se
quiser, me diga apenas o nome do destino (e por quantos dias você pretende
viajar) que eu pesquiso as informações para você.
```

## Principais decisões tomadas

- **Agente de tool-calling (ReAct), não um pipeline fixo.** O LLM decide quando
  pedir dados, pesquisar e montar o roteiro. Novas funcionalidades entram como
  **ferramentas**, não como novos nós rígidos.
- **Validação e memória determinísticas (regex + SQLite), sem LLM.** Tirar
  validação e persistência do caminho do modelo as torna baratas, previsíveis e
  testáveis, e não depende do julgamento (nem da disponibilidade) do LLM.
- **Schemas de ferramenta pequenos + `InjectedToolArg`.** Dados grandes (a lista
  de atrações) são injetados a partir do estado e escondidos do modelo, evitando
  falhas de tool-calling.
- **Recuperação de tool calls "vazadas" como texto.** O modelo às vezes emite a
  chamada no formato nativo do Llama como texto; `_repair_leaked_response` (em
  `nodes.py`) a reconstrói por regex, para o roteiro não se perder.
- **Persistir a viagem *antes* das buscas que podem falhar.** Uma falha de rede
  na Wikipédia pode derrubar o processo; salvar antes garante a retomada.
- **Saída em arquivo `.md`, não no terminal.** O roteiro fica em um artefato
  reutilizável; o terminal só informa o nome do arquivo.
- **Wikipédia como única fonte de dados.** Fonte pública e gratuita, alinhada ao
  bloqueio de URLs enviadas pelo usuário.

## Limitações da solução

- **Somente terminal** — não há interface gráfica.
- **Modelo pequeno e frágil** em tool-calling; daí as salvaguardas de robustez
  (extrações determinísticas, reparo de chamadas vazadas, schemas mínimos).
- **Fonte limitada à Wikipédia em inglês** — destinos sem uma página adequada
  podem não retornar atrações.
- **Filtro de idioma barra apenas scripts não-latinos** (mandarim/híndi). É um
  trade-off consciente: mensagens benignas em inglês/espanhol/francês passam
  (para não gerar falso positivo em português), mas tentativas de injeção nesses
  idiomas continuam sendo bloqueadas.
- **Agrupamento por proximidade é heurístico** — feito pelo LLM sobre o campo
  `location` de cada atração, sem distâncias reais nem mapas.
- **Memória guarda apenas a última viagem** (registro único), não um histórico.

## Estrutura do projeto

Baseada na organização recomendada pela documentação do LangGraph (variante
`requirements.txt`):

```
mini-projeto-ItinerAI/
├── itinerai_agent/         # todo o código do agente
│   ├── utils/
│   │   ├── tools.py        # ferramentas: busca de atrações, geração do .md
│   │   ├── validation.py   # validação de entrada (anti-injeção, idioma, URLs)
│   │   ├── memory.py       # memória persistente da última viagem (SQLite)
│   │   ├── prompts.py      # prompts do agente e das extrações
│   │   ├── nodes.py        # nós do grafo (validação, memória, LLM, tools)
│   │   └── state.py        # estado do grafo (modelos pydantic)
│   └── agent.py            # construção/compilação do StateGraph
├── docs/                   # requisitos, prompts e apresentação
├── output/                 # itinerários .md gerados (não versionado)
├── main.py                 # ponto de entrada: loop de chat no terminal
├── .env.example            # modelo das variáveis de ambiente (sem valores)
├── requirements.txt        # dependências do projeto
└── langgraph.json          # configuração do LangGraph
```

## Prompts e apresentação

- **Prompts** utilizados no planejamento, implementação e melhoria do agente:
  [docs/prompts.md](docs/prompts.md).
- **Apresentação** da ideia do projeto:
  [docs/apresentacao-itinerai.pptx](docs/apresentacao-itinerai.pptx)
  (versão web: [docs/apresentacao.html](docs/apresentacao.html)).
