# ItinerAI

[![CI](https://github.com/joaopuel/mini-projeto-ItinerAI/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/joaopuel/mini-projeto-ItinerAI/actions/workflows/ci.yml)

**Agente de IA, construído com LangGraph, que cria itinerários de viagem dia a
dia a partir de um destino e uma duração — tudo pelo terminal.** O agente
pesquisa pontos turísticos na Wikipédia, agrupa as atrações por proximidade,
gera um arquivo `.md` pronto para levar na mala e, com sua aprovação explícita,
envia o roteiro por e-mail.

## Sumário

- [Vídeo de demonstração](#vídeo-de-demonstração)
- [Quadro Kanban](#quadro-kanban)
- [Descrição da solução](#descrição-da-solução)
- [Classificação e arquitetura](#classificação-e-arquitetura)
- [Tool e integração](#tool-e-integração)
- [Contexto e memória](#contexto-e-memória)
- [Segurança e autonomia](#segurança-e-autonomia)
- [Instalação e execução](#instalação-e-execução)
  - [1. Instalar e configurar o projeto](#1-instalar-e-configurar-o-projeto)
  - [2. Executar a aplicação](#2-executar-a-aplicação)
  - [3. Instalar e executar o n8n](#3-instalar-e-executar-o-n8n)
  - [4. Executar os testes](#4-executar-os-testes)
- [QA, observabilidade e DevOps](#qa-observabilidade-e-devops)
- [Automação low-code (n8n)](#automação-low-code-n8n)
- [Cenários de uso](#cenários-de-uso)
- [Análise crítica e limitações](#análise-crítica-e-limitações)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Documentação e evidências](#documentação-e-evidências)

---

## Vídeo de demonstração

> 🎥 *A publicar (YouTube, não listado) — o link entra aqui.*

Demonstração da solução em funcionamento: o problema e o objetivo, a arquitetura,
o fluxo principal e o cenário de falha ao vivo, a aprovação humana antes do envio
do e-mail, as evidências de QA e do pipeline, e o fluxo low-code no n8n.

## Quadro Kanban

O planejamento e o acompanhamento do desenvolvimento estão no GitHub Project:

**<https://github.com/users/joaopuel/projects/1>**

São **26 cards** — 6 epics (E01 a E06) e 19 tarefas (T01 a T19) —, criados
**antes** do início das implementações e movimentados ao longo do trabalho. Cada
card referencia o epic a que pertence, e as branches e os pull requests seguem a
nomenclatura registrada em [`docs/tasks.md`](docs/tasks.md).

---

## Descrição da solução

**Nome:** ItinerAI.

**Problema.** Planejar um roteiro de viagem dá trabalho: é preciso pesquisar o
que visitar no destino, decidir quantas atrações cabem em cada dia e, de
preferência, agrupar lugares próximos para não desperdiçar o dia em
deslocamento. É repetitivo, manual e fácil de fazer mal.

**Público.** Viajantes que querem um roteiro base pronto em segundos, sem abrir
dez abas de pesquisa.

**Objetivo e valor.** A partir de duas informações — destino e duração —, o
agente entrega um roteiro dia a dia, agrupado por região, em um arquivo
reutilizável:

| | |
| --- | --- |
| **Entrada** | destino e duração em dias, coletados na conversa **uma informação por vez**, nesta ordem |
| **Processamento** | busca dos pontos turísticos na Wikipédia e montagem do roteiro, no máximo 3 atrações por dia, agrupadas por proximidade |
| **Saída** | `output/itinerario-<destino>-<n>-dias.md` — **o roteiro não é impresso no terminal**, o agente só informa o nome do arquivo; opcionalmente, o mesmo roteiro por e-mail |

### O que foi mantido e o que evoluiu

Esta entrega dá continuidade ao mini-projeto do Módulo 2.

**Mantido** — o núcleo do produto continua o mesmo: agente ReAct de tool-calling
em LangGraph, Wikipédia como única fonte de dados, geração do `.md` em
`output/`, validação de entrada 100% por regex e memória da última viagem em
SQLite.

**Evoluído:**

| Capacidade | O que mudou |
| --- | --- |
| Busca da Wikipédia | virou **paralelização** no grafo: fan-out em dois ramos + fan-in determinístico |
| Integrações externas | timeout configurável, retry limitado com backoff e fallback amigável, sem derrubar o processo |
| Configuração | modelo, temperatura, timeouts e nível de log saíram do código para variáveis de ambiente |
| Observabilidade | de **zero** para dois sinais correlacionados: logs estruturados em JSON e trilha de auditoria com latência por passo |
| Testes | de **nenhum** teste para uma suíte com gate de cobertura, incluindo testes E2E sobre o grafo compilado |
| CI/CD | pipeline do GitHub Actions com lint, testes, dois gates de cobertura e build |
| Integração externa | envio do roteiro por e-mail via webhook do n8n, condicionado a aprovação humana explícita |

---

## Classificação e arquitetura

**Classificação: agente.** Não é um workflow determinístico nem um híbrido com
etapas fixas de negócio.

A justificativa é observável no grafo: **o LLM decide o próximo passo a cada
iteração**. Nada no código determina que a busca aconteça antes do roteiro — é o
modelo que escolhe chamar `search_tourist_attractions`, e a aresta condicional
`route_after_llm` apenas roteia a decisão dele. O mesmo vale para pedir a duração
da viagem: não há um nó "perguntar duração", há uma instrução de sistema e um
modelo que decide quando perguntar.

O que **é** determinístico está deliberadamente fora do caminho do modelo:
validação de entrada, escolha da melhor página no fan-in, persistência da memória
e a aprovação do envio por e-mail. É uma decisão de projeto, não uma limitação —
ver [Segurança e autonomia](#segurança-e-autonomia).

### Diagrama

```
                     START
                       │
                  route_entry
                 ┌─────┴──────────────────┐
        (envio aprovado)              (turno normal)
                 ▼                          ▼
      ┌────────────────────┐        ┌─────────────────┐
      │  notify_recipient  │        │  validate_input │  regex: anti-injeção,
      │  POST no n8n → END │        └─────────────────┘  idioma, URL (sem LLM)
      └────────────────────┘
                       │
              route_after_validation
                 ┌─────┴─────┐
             (inválida)   (válida)
                 ▼             ▼
                END   ┌─────────────────┐
                      │  persist_memory │  salva a viagem no SQLite
                      └─────────────────┘
                               │
                               ▼
                   ┌───────────────────┐
          ┌───────▶│      call_llm     │  LLM + tools (bind_tools)
          │        └───────────────────┘
          │                  │
          │            route_after_llm
          │       ┌──────────┼────────────────────┐
          │  (sem tool)  (outra tool)   (search_tourist_attractions)
          │       ▼          ▼                     ▼
          │      END   ┌───────────┐      ┌─────────────────┐
          │            │ call_tools│      │ dispatch_search │
          │            └───────────┘      └─────────────────┘
          │                  │             fan-out  ┌───┴────┐
          │                  │                      ▼        ▼
          │                  │        ┌──────────────────┐ ┌───────────────────────┐
          │                  │        │fetch_tourism_page│ │fetch_destination_page │
          │                  │        └──────────────────┘ └───────────────────────┘
          │                  │          "Tourism in X"  ∥  "X"   (Wikipédia, paralelo)
          │                  │                      └───┬────┘  fan-in
          │                  │                          ▼
          │                  │                   ┌─────────────┐
          │                  │                   │ merge_pages │  melhor página,
          │                  │                   └─────────────┘  determinístico (sem LLM)
          │                  │                          │
          └──────────────────┴──────────────────────────┘
             (call_tools e merge_pages devolvem o controle a call_llm)
```

### Nós e rotas

Os nós ficam em `itinerai_agent/utils/nodes.py`; o grafo é montado em
`itinerai_agent/agent.py`.

| Nó / rota | Papel |
| --- | --- |
| `route_entry` | aresta condicional do `START`: desvia para `notify_recipient` quando o envio já foi aprovado; senão, caminho normal |
| `validate_input` | valida a última mensagem do usuário (regex, sem LLM) |
| `route_after_validation` | segue para `persist_memory` ou vai direto a `END` com a recusa |
| `persist_memory` | grava a viagem no SQLite **antes** das buscas que podem falhar |
| `call_llm` | invoca o LLM com as ferramentas vinculadas; repara tool calls "vazadas" como texto |
| `route_after_llm` | 3 saídas: `END`, `call_tools` ou o fan-out da busca |
| `call_tools` | executa `build_itinerary` e devolve o controle ao LLM |
| `dispatch_search` | origem do fan-out: guarda destino e `tool_call_id` em `pending_search` |
| `fetch_tourism_page` ∥ `fetch_destination_page` | **rodam em paralelo**, baixam e extraem as duas páginas |
| `merge_pages` | fan-in determinístico: escolhe a página que rendeu atrações |
| `notify_recipient` | envia o roteiro ao webhook do n8n (sem LLM) e encerra o turno |

### Paralelização

A busca é o ponto de paralelismo do grafo. `dispatch_search` abre dois ramos que
o LangGraph executa no mesmo superstep; cada um escreve **uma chave** em
`AgentState.page_results`, um canal com reducer que mescla as escritas
concorrentes. `merge_pages` é o fan-in.

O ganho foi **medido** numa execução real: os dois ramos custaram 930,7 ms e
7695,1 ms; sequencialmente seriam 8625,8 ms, e o relógio de parede foi 7694,6 ms
— **931,2 ms economizados**, praticamente o ramo mais curto inteiro. Evidência em
[`docs/qa/analise-observabilidade.md`](docs/qa/analise-observabilidade.md).

### Stack

| Tecnologia | Uso |
| --- | --- |
| **Python 3.12.9** | Linguagem base |
| **LangGraph** | Orquestração do agente como grafo de estados (`StateGraph`) |
| **pydantic** | Estado do grafo e todos os modelos de dados |
| **Groq** — `openai/gpt-oss-120b` | LLM do agente e da extração (via `langchain-groq`; configurável por `GROQ_MODEL`) |
| **requests + beautifulsoup4** | Busca e parsing das páginas da Wikipédia |
| **sqlite3** (stdlib) | Memória persistente e trilha de auditoria |
| **n8n** | Automação low-code do envio por e-mail |

---

## Tool e integração

### Ferramentas (`itinerai_agent/utils/tools.py`)

- **`search_tourist_attractions(destination)`** — busca pontos turísticos na
  Wikipédia (páginas `Tourism in <destino>` e `<destino>`) e devolve uma lista
  estruturada de atrações. **Finalidade no fluxo:** é o passo de coleta de dados;
  sem ela o agente não tem o que colocar no roteiro. No grafo roda como o
  fan-out/fan-in paralelo descrito acima.
- **`build_itinerary(destination, num_days)`** — agrupa as atrações por
  proximidade, distribui pelos dias (no máximo 3 por dia) e **grava o `.md`** em
  `output/`. **Finalidade no fluxo:** é o passo que produz o artefato final.

> A lista de atrações é injetada a partir do estado via `InjectedToolArg` e fica
> **oculta do modelo**: o schema exposto ao LLM tem apenas `destination` e
> `num_days`. Schemas pequenos evitam falhas de tool-calling.

### Integração externa: webhook (n8n)

`itinerai_agent/utils/notifications.py` faz um **POST autenticado** para um
webhook do n8n com o payload tipado `ItineraryNotification` (`destination`,
`num_days`, `recipient`, `markdown`, `run_id`). O n8n valida, converte o markdown
em HTML e despacha o e-mail.

**Finalidade no fluxo:** entregar o roteiro fora do terminal. É a única chamada a
um serviço externo que não seja a Wikipédia, e a única ação irreversível do
agente — por isso exige aprovação humana. Ver
[Automação low-code](#automação-low-code-n8n).

---

## Contexto e memória

Duas camadas, com propósitos diferentes.

### 1. Estado do grafo (curto prazo)

`AgentState`, em `itinerai_agent/utils/state.py`, é um modelo **pydantic** (não
um `dict` solto) que atravessa todos os nós de um turno:

| Campo | Conteúdo |
| --- | --- |
| `messages` | histórico da conversa, com o reducer `add_messages` |
| `run_id` | identificador do turno, correlaciona logs e auditoria |
| `destination`, `num_days` | os dois campos obrigatórios, à medida que são descobertos |
| `tourist_attractions` | atrações encontradas, injetadas em `build_itinerary` |
| `itinerary` | o roteiro montado |
| `pending_search`, `page_results` | suportam o fan-out; `page_results` tem reducer para as escritas concorrentes |
| `recipient_email`, `notification` | aprovação do envio e seu desfecho |

**Não há checkpointer.** O estado vive na memória do processo durante o turno e é
repassado entre turnos pelo `main.py`. Foi uma decisão consciente: adotar
`MemorySaver` + `thread_id` exigiria mudanças no projeto inteiro para resolver um
problema que a memória persistente já resolve de forma mais simples.

### 2. Memória persistente (longo prazo)

SQLite (`itinerai_memory.db`), via `sqlite3` da stdlib — sem dependência nova e
sem LLM. Guarda **um único registro**: a última viagem (destino, duração e se o
itinerário foi concluído), sobrescrito a cada salvamento.

**Como a informação é usada.** Na abertura, o `main.py` carrega a memória e, se
houver uma viagem salva, mostra-a e oferece:

- **retomá-la**, se ficou incompleta — ex.: uma falha derrubou o processo antes
  do roteiro;
- **refazê-la**, se o itinerário já estava pronto.

Aceitando, o estado é pré-preenchido com destino e duração e uma mensagem
sintética reafirma a viagem, para o agente refazer a busca sem o usuário
redigitar nada. A gravação acontece **duas vezes**: no nó `persist_memory`, logo
após a validação e **antes** das buscas que podem falhar, e ao fim do turno, para
capturar o que foi descoberto nele.

> A memória **não é exposta ao LLM** durante a conversa — é lida e escrita por
> código determinístico, o que mantém o contexto do modelo enxuto.

---

## Segurança e autonomia

### Proteção de credenciais

- `GROQ_API_KEY`, `N8N_WEBHOOK_URL` e `N8N_WEBHOOK_TOKEN` vêm **sempre** do
  ambiente, carregados de um `.env` que está no `.gitignore`. Nenhuma chave é
  hardcoded.
- O [`.env.example`](.env.example) versionado traz apenas os **nomes** das
  variáveis e os padrões públicos, sem valores sensíveis.
- O workflow do n8n versionado **não contém credencial alguma**: elas entram por
  referência de *nome* dentro do n8n.
- O formatter de log **redige o valor da `GROQ_API_KEY`** da linha final, como
  defesa em profundidade, e o e-mail do destinatário só aparece mascarado
  (`j***@exemplo.com`).

### Validações de entrada

Antes de a mensagem chegar ao LLM, `validate_input` a inspeciona
(`itinerai_agent/utils/validation.py`) e bloqueia três categorias, respondendo
com um aviso em português e **sem acionar nenhuma ferramenta**:

1. **Prompt injection** — padrões nos 6 idiomas mais falados (português, inglês,
   espanhol, francês, mandarim e híndi).
2. **Idioma não suportado** — scripts não-latinos (mandarim/CJK, híndi/devanágari).
3. **URLs/links** enviados pelo usuário — o agente nunca os acessa.

A detecção é **100% por regex, sem nenhuma chamada ao LLM**: determinística,
barata e imune ao julgamento do modelo. A ordem é injeção → idioma → URL, para
que uma injeção em mandarim receba a mensagem de injeção, não a de idioma.

### Comportamento diante de prompt injection

Uma entrada adversarial **não chega ao modelo**. O nó de validação insere a
mensagem de recusa e o roteador manda o fluxo direto para `END`:

- nenhuma ferramenta é executada;
- as instruções de sistema não são substituídas, porque o LLM não é invocado;
- nada do estado interno é revelado.

Isso é verificado por um **teste E2E** cuja asserção central é
`llm.call_count == 0` sobre o grafo compilado — a garantia não é "o modelo
resistiu", é "o modelo nem foi chamado". O cenário foi eleito o prioritário da
análise de risco justamente porque sua falha seria **silenciosa**: trocar a
aresta condicional por uma incondicional não quebraria nenhum teste unitário, nem
o lint, nem o build. Ver
[`docs/qa/analise-testes.md`](docs/qa/analise-testes.md).

### Limites de autonomia e aprovação humana

O agente age sozinho no que é reversível e **para** no que não é.

| Ação | Autonomia |
| --- | --- |
| Pesquisar na Wikipédia | livre — leitura de fonte pública |
| Montar o roteiro e gravar o `.md` | livre — artefato local, reversível |
| Ler e escrever a memória | livre — determinística, sem LLM |
| **Enviar o roteiro por e-mail** | **bloqueada até aprovação explícita** |

O envio é uma ação **externa e irreversível**. A aprovação é uma pergunta s/n no
terminal seguida da coleta do endereço, ambas **fora do grafo e sem passar pelo
LLM**, com o e-mail validado por regex. Sem um "s" e um endereço bem-formado,
nenhuma chamada externa acontece. Sem `N8N_WEBHOOK_URL` configurada, a integração
degrada silenciosamente e o roteiro segue disponível em `output/`.

A recusa também é registrada (log `notification_declined` + linha de auditoria):
sem isso, "o usuário recusou" seria indistinguível de "o agente nunca perguntou".

---

## Instalação e execução

### Pré-requisitos

| | Para quê |
| --- | --- |
| **Python 3.12.9** | a aplicação |
| **Chave de API da Groq** | o LLM — gratuita em [console.groq.com](https://console.groq.com) |
| **Node.js 20+** *ou* **Docker** | apenas para rodar o n8n **localmente** (opcional) — dispensável se usar o n8n Cloud |
| Conta de e-mail com **SMTP** | apenas para o envio por e-mail (opcional) |

O agente funciona por completo sem o n8n; só deixa de oferecer o envio.

### 1. Instalar e configurar o projeto

**1.1. Clone o repositório:**

```bash
git clone https://github.com/joaopuel/mini-projeto-ItinerAI.git
cd mini-projeto-ItinerAI
```

**1.2. Crie e ative um ambiente virtual:**

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS / Git Bash
python -m venv .venv
source .venv/bin/activate
```

> No Windows, se a política de execução bloquear o `Activate.ps1`, use
> `.venv\Scripts\python.exe` no lugar de `python` nos comandos seguintes — chamar
> o interpretador direto não executa script nenhum.

**1.3. Instale as dependências:**

```bash
pip install -r requirements.txt
```

**1.4. Configure as variáveis de ambiente.** Copie o exemplo e preencha:

```bash
cp .env.example .env
```

| Variável | Obrigatória | Padrão | Para que serve |
| --- | :---: | --- | --- |
| `GROQ_API_KEY` | **sim** | — | autenticação na Groq |
| `GROQ_MODEL` | não | `openai/gpt-oss-120b` | modelo do agente **e** da extração |
| `GROQ_TEMPERATURE` | não | `0.7` | temperatura do agente (a extração usa `0` fixo) |
| `WIKIPEDIA_TIMEOUT` | não | `10` | timeout (s) das requisições à Wikipédia |
| `LOG_LEVEL` | não | `INFO` | nível dos logs em `logs/itinerai.log` |
| `LOG_TO_STDERR` | não | desligado | espelha os logs no stderr, para depuração |
| `N8N_WEBHOOK_URL` | não | vazio | URL do webhook. **Vazia desliga a integração** |
| `N8N_WEBHOOK_TOKEN` | não | vazio | valor do header `X-ItinerAI-Token` |
| `N8N_TIMEOUT` | não | `10` | timeout (s) da chamada ao webhook |

> O `.env` está no `.gitignore` e **nunca** deve ser versionado. Rodar apenas com
> `GROQ_API_KEY` funciona: todas as demais caem nos padrões acima, lidos em
> `itinerai_agent/utils/config.py`.

### 2. Executar a aplicação

```bash
python main.py
```

Converse pelo terminal; digite `sair` para encerrar. Os itinerários ficam em
`output/`, os logs em `logs/itinerai.log`.

Para inspecionar a latência de um turno:

```bash
python show_audit.py <run_id>     # o run_id aparece em qualquer linha do log
```

### 3. Instalar e executar o n8n

Opcional — necessário apenas para o envio do roteiro por e-mail.

**3.1. Suba o n8n.** Escolha uma das formas:

```bash
# Opção A — sem instalar nada (requer Node.js 20+)
npx n8n
```

```bash
# Opção B — instalação global (requer Node.js 20+)
npm install -g n8n
n8n start
```

```bash
# Opção C — Docker, com os dados preservados entre execuções
docker volume create n8n_data
docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

**Opção D — n8n Cloud, sem instalar nada.** A plataforma online do n8n
([n8n.io](https://n8n.io)) funciona igualmente bem, tanto no **período de teste
gratuito (trial)** quanto em um **plano pago (Pro)**. É a via mais rápida se você
não quer Node.js nem Docker na máquina: basta criar a conta e a instância já sobe
pronta, com uma URL própria no formato
`https://<sua-instancia>.app.n8n.cloud`.

Nas opções A, B e C o editor abre em **<http://localhost:5678>** e, na primeira
execução, o n8n pede a criação de uma conta local. Na opção D o editor é a URL da
sua instância na nuvem.

> **A escolha só muda a URL.** O workflow, as credenciais e todos os passos
> abaixo são idênticos nos quatro casos — troque `localhost:5678` pelo domínio da
> sua instância onde ele aparecer. Uma diferença prática: no n8n Cloud a
> *Production URL* é pública e acessível de qualquer lugar, enquanto uma
> instância local só responde à própria máquina — o que basta aqui, já que o
> agente roda no mesmo computador.

**3.2. Importe o workflow.** No editor: *Workflows → ⋯ → Import from File* e
selecione [`docs/low-code/n8n-workflow.json`](docs/low-code/n8n-workflow.json).
O arquivo **não contém credenciais**.

**3.3. Crie as duas credenciais** com exatamente estes nomes, para o workflow
importado casar com elas sozinho:

| Tipo | Nome | Conteúdo |
| --- | --- | --- |
| *Header Auth* | `ItinerAI Webhook Token` | Name: `X-ItinerAI-Token` · Value: um token aleatório à sua escolha |
| *SMTP* | `ItinerAI SMTP` | host, porta, usuário e senha do provedor. No Gmail: `smtp.gmail.com`, porta 465, SSL ligado e uma **senha de app** |

**3.4. Ajuste o remetente.** No nó `Enviar email`, troque o `fromEmail`
(`itinerai@example.com`) pelo endereço autenticado na credencial SMTP.

**3.5. Ative o workflow** (chave *Active*, canto superior direito) e copie a
*Production URL* do nó `Webhook`.

**3.6. Aponte a aplicação para ele** no `.env`:

```dotenv
# instância local (opções A, B ou C)
N8N_WEBHOOK_URL=http://localhost:5678/webhook/itinerai-email
# ou, no n8n Cloud (opção D):
# N8N_WEBHOOK_URL=https://<sua-instancia>.app.n8n.cloud/webhook/itinerai-email
N8N_WEBHOOK_TOKEN=<o mesmo token da credencial Header Auth>
```

**3.7. Teste o webhook isoladamente** (opcional), com o workflow ativo:

```bash
curl -i -X POST "http://localhost:5678/webhook/itinerai-email" \
  -H "Content-Type: application/json" \
  -H "X-ItinerAI-Token: $ITINERAI_TOKEN" \
  --data-binary @docs/low-code/payload-exemplo.json
```

Esperado: `200` com `{"status":"sent","run_id":…}` e o e-mail na caixa de
entrada. Detalhes dos nós e das respostas de erro em
[`docs/low-code/README.md`](docs/low-code/README.md).

### 4. Executar os testes

```bash
pip install -r requirements-dev.txt
pytest
```

**Nenhum teste acessa a rede ou exige a `GROQ_API_KEY` real** — HTTP e LLM são
100% dublados e o `conftest.py` injeta uma chave descartável e isola os efeitos
em disco num `tmp_path`.

O `pytest` já roda com cobertura e **falha se ela cair abaixo de 70%**
(configurado em `pyproject.toml`). Na última execução registrada: **250 testes,
99,54% de cobertura**.

Comandos úteis:

```bash
pytest tests/e2e                     # só os testes E2E sobre o grafo compilado
pytest -k validation                 # só os testes de validação de entrada
pytest --cov-report=html             # relatório navegável em htmlcov/index.html
ruff check .                         # o mesmo lint que o CI executa
```

---

## QA, observabilidade e DevOps

### Testes

Suíte com `pytest` cobrindo a lógica determinística de maior risco — validação,
memória, auditoria, funções puras e resiliência das ferramentas — mais **testes
E2E sobre o grafo compilado**, com LLM e rede dublados. O cenário eleito
prioritário por risco foi a **injeção de prompt ponta a ponta**, e a
justificativa está em
[`docs/qa/analise-testes.md`](docs/qa/analise-testes.md).

### Análise de código com IA

Code review assistido por IA de uma alteração real (PR #40), com os achados
classificados por severidade e o desfecho de cada um registrado:
[`docs/qa/analise-cr.md`](docs/qa/analise-cr.md).

### Sinais de observabilidade

Dois sinais correlacionados pelo **`run_id`** gerado a cada turno:

1. **Logs estruturados em JSON** — `logs/itinerai.log`, uma linha por evento:
   entrada e saída de cada nó, decisões de roteamento, execução de ferramentas
   com latência, bloqueios da validação com o motivo. Só stdlib. O terminal do
   usuário fica limpo; segredos e conteúdo de mensagens nunca são registrados.
2. **Trilha de auditoria** — `itinerai_audit.db`, tabela `execution_audit`, uma
   linha por passo (nó, tool ou turno) com a **latência medida**.

A investigação de três execuções reais cruzando os dois está em
[`docs/qa/analise-observabilidade.md`](docs/qa/analise-observabilidade.md), com
os logs e trilhas brutos em [`docs/evidencias/`](docs/evidencias).

**O achado que justifica exigir dois sinais:** o log aponta
`fetch_destination_page` como gargalo (7695,1 ms, 78% do turno), mas a trilha
abre o nó e mostra que **74,4% dele é a extração pelo LLM, não a rede**. Nenhum
dos dois sinais chega a essa conclusão sozinho.

### Pipeline

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em todo `push` e
`pull request` para `develop` e `main`, com três jobs paralelos:

- **lint** — `ruff check` (bloqueante) e `ruff format --check` (informativo);
- **test** — `pytest`, gate de cobertura global (≥ 70%) e gate de cobertura do
  **código novo** (`diff-cover` ≥ 70% das linhas do PR);
- **build** — compila o grafo só com as dependências de produção e valida o
  `langgraph.json`.

O relatório de cobertura sobe como artefato. O pipeline roda **sem
`GROQ_API_KEY` real e sem rede**.

### Análise de logs, anomalia e risco

[`docs/qa/analise-ci.md`](docs/qa/analise-ci.md) analisa uma execução real e
**reprovada** do CI, com os logs brutos versionados:

- **Anomalia identificada:** dois gates de cobertura com o mesmo limiar de 70% e
  sensibilidades opostas — o global passou com **94%** enquanto o do código novo
  reprovou com **50%**, na mesma execução. Um gate de média é estruturalmente
  cego a regressões localizadas: o projeto absorveria ~300 linhas sem cobertura
  antes de o gate global reclamar, o equivalente a **seis** entregas como
  aquela.
- **Anomalia secundária:** o `ruff format --check` reprova mas não derruba o job
  (`continue-on-error`), e a dívida cresce em silêncio — 14 de 42 arquivos.
- **Estimativa de risco:** regra de sucessão de Laplace sobre 6 execuções reais
  → **~50%** de probabilidade de o próximo PR reprovar, com o método e as
  limitações da amostra explicitados.

---

## Automação low-code (n8n)

| | |
| --- | --- |
| **Gatilho** | webhook `POST /webhook/itinerai-email`, autenticado por *Header Auth* (`X-ItinerAI-Token`). Uma chamada sem token recebe `403` e não gera execução |
| **Relação com a aplicação** | o n8n **não** monta roteiro, não decide nada e não conhece a Wikipédia. Recebe um payload pronto, valida, converte o markdown em HTML e despacha o e-mail. Removido o fluxo, o agente continua inteiro — só deixa de oferecer o envio |
| **Saída produzida** | o **e-mail com o roteiro formatado**, mais o registro do disparo na aba *Executions* do n8n e a resposta `200` com o `run_id`, que correlaciona a execução do fluxo com os logs do agente |

O fluxo tem 7 nós e três caminhos de resposta: `200` (enviado), `400` (payload
inválido) e `502` (falha de SMTP). Do lado da aplicação, qualquer resposta
diferente de `2xx` vira `NotificationResult(status="failed")` — o turno não
quebra e o `.md` segue em `output/`.

**Sem retry, deliberadamente.** A busca da Wikipédia repete com backoff porque um
GET é idempotente; um POST que dispara e-mail **não é**. Um timeout do cliente
não prova que o n8n deixou de processar, e repetir mandaria uma segunda cópia do
roteiro.

Instruções de instalação e configuração em
[Instalar e executar o n8n](#3-instalar-e-executar-o-n8n); detalhe dos nós e
evidências em [`docs/low-code/README.md`](docs/low-code/README.md).

---

## Cenários de uso

### Cenário 1 — Fluxo principal

**Entrada:**

```text
ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem.
(digite 'sair' para encerrar)
ItinerAI: Qual o seu próximo destino?
Você: Quero viajar para Lisboa
ItinerAI: Boa escolha! Qual a duração (dias) da sua viagem?
Você: 3 dias
```

**Comportamento esperado:** o agente coleta os dois campos **um por vez**, chama
`search_tourist_attractions`, o grafo abre o fan-out nas duas páginas da
Wikipédia, `merge_pages` escolhe a que rendeu atrações, o modelo chama
`build_itinerary`, o `.md` é gravado e o agente oferece o envio por e-mail.

**Resultado produzido:**

```text
ItinerAI: Prontinho! O arquivo itinerario-lisboa-3-dias.md com o itinerário
para seu destino foi criado em output/. Boa viagem! ✈️
ItinerAI: Deseja receber o roteiro por e-mail? (s/n)
```

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

### Cenário 2 — Risco: falha na integração externa

**Entrada:** a mesma conversa acima, mas com a Wikipédia inacessível. Reproduzível
sem alterar código, forçando o timeout:

```powershell
$env:WIKIPEDIA_TIMEOUT = '0.001'
python main.py
```

**Comportamento esperado:** cada ramo do fan-out tenta 3 vezes (1 + 2 repetições,
backoff 0,5 s → 1,0 s); esgotadas as tentativas, o resultado vira
`unavailable=true` em vez de propagar a exceção. O agente **não cai** e responde
com uma mensagem de problema técnico — distinta de "destino não encontrado".

**Resultado produzido** — execução real, `run_id` `c5f84813`:

| Sinal | O que registrou |
| --- | --- |
| Log | `ConnectTimeout` nos dois ramos, `"unavailable": true` nos dois `page_fetched` e no `search_merged` |
| Auditoria | 15 passos, **4 retries** e **2 erros** de `wikipedia_fetch` |
| Desfecho | **todos os passos terminaram `ok`** e o turno fechou normalmente em 2898,5 ms |

O último ponto é o mais relevante: um incidente de rede completo — seis
requisições falhadas — não derruba nada e é invisível para quem olha só o
desfecho. **Ele só existe porque os dois sinais o registraram.** Análise completa
em [`docs/qa/analise-observabilidade.md`](docs/qa/analise-observabilidade.md).

### Cenário 2b — Risco: entrada adversarial

```text
Você: https://meu-blog-de-viagens.com/roteiro-lisboa
ItinerAI: Por segurança, não acesso links ou URLs enviados por usuários. Se
quiser, me diga apenas o nome do destino (e por quantos dias você pretende
viajar) que eu pesquiso as informações para você.
```

O bloqueio acontece **antes** do LLM: nenhuma ferramenta roda e o modelo não é
invocado. Vale igual para tentativas de prompt injection.

---

## Análise crítica e limitações

### Refinamento realizado: tool calls vazadas como texto

**Problema observado.** O agente imprimia a chamada de ferramenta **crua no
terminal**, em vez de executá-la:

```text
Você: Monte um itinerário de 3 dias para a Inglaterra
ItinerAI: function=build_itinerary>{"destination": "Inglaterra", "num_days": 3}</function>

function=search_tourist_attractions>{"destination": "Inglaterra"}</function>
```

Três defeitos numa saída só: o usuário via markup interno; **nenhuma ferramenta
rodava** (sem `tool_calls` estruturados, o roteador ia para `END` e o roteiro
nunca seria montado); e a ordem estava invertida — `build_itinerary` antes da
busca.

**Alteração aplicada.** Duas frentes. No system prompt, três regras novas — uma
ferramenta por vez, nunca escrever a chamada como texto, sempre buscar antes de
montar. E, como rede de segurança, `_repair_leaked_response` em `nodes.py`:
reconstrói as chamadas por **regex determinístico**, descarta um
`build_itinerary` prematuro quando há busca no mesmo lote e, se nada for
recuperável, troca o texto cru por um aviso amigável.

**Resultado obtido.** O markup nunca mais chega ao terminal; a regressão está
travada por dois testes; ocorrências viram os eventos
`leaked_tool_calls_recovered`/`_unrecoverable` no log — e não houve nenhuma nas
354 linhas analisadas na investigação de observabilidade.

O segundo ciclo de refinamento — redução do escopo de ferramentas de 4 para 2,
com `tools.py` encolhendo 224 linhas — está em
[`docs/prompts/refinamentos.md`](docs/prompts/refinamentos.md).

### Limitações

- **Somente terminal** — não há interface gráfica.
- **Fonte limitada à Wikipédia em inglês** — destinos sem página adequada podem
  não retornar atrações.
- **Agrupamento por proximidade é heurístico** — feito pelo LLM sobre o campo
  `location`, sem distâncias reais nem mapas.
- **Memória guarda apenas a última viagem**, não um histórico.
- **`run_id` é por turno, não por conversa** — reconstruir uma conversa inteira
  exige costurar vários identificadores na mão.
- **Filtro de idioma barra apenas scripts não-latinos.** Trade-off consciente:
  mensagens benignas em inglês, espanhol e francês passam (para não gerar falso
  positivo em português), mas tentativas de injeção nesses idiomas continuam
  bloqueadas pela regra de injeção.
- **A extração pelo LLM domina a latência** — 58% de um turno de busca. As duas
  páginas são sempre extraídas, inclusive a que será descartada.

### Evoluções futuras

1. **`conversation_id` ao lado do `run_id`**, para correlacionar turnos de uma
   mesma conversa.
2. **Extrair só o ramo escolhido**, ou cachear por página — atacaria diretamente
   o maior custo de latência.
3. **Elevar o gate global de cobertura** de 70% para ~90%, transformando um piso
   decorativo (a base está em 99,54%) em detector real de regressão.
4. **Distâncias reais** no agrupamento, via uma API de geocodificação, no lugar
   da heurística sobre texto.
5. **Histórico de viagens** na memória, no lugar do registro único.

> O **vídeo de demonstração** está no topo deste documento, em
> [Vídeo de demonstração](#vídeo-de-demonstração).

---

## Estrutura do projeto

Baseada na organização recomendada pela documentação do LangGraph (variante
`requirements.txt`):

```
mini-projeto-ItinerAI/
├── .github/workflows/
│   └── ci.yml              # pipeline de CI: lint, testes, cobertura, build
├── itinerai_agent/         # todo o código do agente
│   ├── utils/
│   │   ├── config.py       # leitura das variáveis de ambiente
│   │   ├── tools.py        # ferramentas: busca de atrações, geração do .md
│   │   ├── validation.py   # validação de entrada (anti-injeção, idioma, URLs)
│   │   ├── memory.py       # memória persistente da última viagem (SQLite)
│   │   ├── logging_config.py  # logging estruturado em JSON + run_id
│   │   ├── audit.py        # trilha de auditoria + latência por passo (SQLite)
│   │   ├── notifications.py   # cliente do webhook do n8n
│   │   ├── prompts.py      # prompts do agente e das extrações
│   │   ├── nodes.py        # nós do grafo
│   │   └── state.py        # estado do grafo (modelos pydantic)
│   └── agent.py            # construção/compilação do StateGraph
├── tests/                  # suíte de testes (pytest), incluindo tests/e2e/
├── docs/                   # documentação e evidências — ver docs/README.md
│   ├── prompts/            # histórico, instruções de sistema, refinamentos
│   ├── qa/                 # análises: testes, code review, CI, observabilidade
│   ├── evidencias/         # evidência bruta: logs, trilhas, relatórios
│   └── low-code/           # workflow do n8n + evidências
├── output/                 # itinerários .md gerados (não versionado)
├── logs/                   # logs estruturados em JSON (não versionado)
├── main.py                 # ponto de entrada: loop de chat no terminal
├── show_audit.py           # exibe a trilha de auditoria de um run_id
├── .env.example            # modelo das variáveis de ambiente (sem valores)
├── pyproject.toml          # config de pytest + cobertura + Ruff
├── requirements.txt        # dependências de produção
├── requirements-dev.txt    # dependências de teste e lint
└── langgraph.json          # configuração do LangGraph
```

---

## Documentação e evidências

O índice completo, com um mapa de **critério de avaliação → evidência**, está em
**[`docs/README.md`](docs/README.md)**.

| Área | Documento |
| --- | --- |
| Prompts e refinamento | [`docs/prompts/`](docs/prompts) — histórico, instruções de sistema e os dois ciclos |
| QA e testes | [`docs/qa/analise-testes.md`](docs/qa/analise-testes.md), [`docs/qa/analise-cr.md`](docs/qa/analise-cr.md) |
| Observabilidade | [`docs/qa/analise-observabilidade.md`](docs/qa/analise-observabilidade.md) |
| DevOps | [`docs/qa/analise-ci.md`](docs/qa/analise-ci.md) |
| Low-code | [`docs/low-code/README.md`](docs/low-code/README.md) |
| Planejamento | [`docs/tasks.md`](docs/tasks.md) — 6 epics, 19 tarefas |
| Apresentação | [`docs/apresentacao-itinerai.pptx`](docs/apresentacao-itinerai.pptx) ([versão web](docs/apresentacao.html)) |
