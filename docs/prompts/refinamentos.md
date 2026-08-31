# Ciclos de refinamento do agente

Registro dos refinamentos de prompt e de comportamento do agente exigidos pelo
§4.10, no formato **problema observado → alteração realizada → resultado
obtido**. Ambos os ciclos são reais, datados e rastreáveis a commits.

| # | Ciclo | Data | Commit | Natureza |
| --- | --- | --- | --- | --- |
| 1 | [Tool calls vazadas como texto](#ciclo-1) | 2026-07-20 | `5e57116` | prompt + código |
| 2 | [Redução do escopo de ferramentas](#ciclo-2) | 2026-07-20 | `5e57116` | prompt + arquitetura |

Os dois saíram do mesmo commit porque têm a **mesma causa raiz**: o
`llama-3.1-8b-instant`, modelo pequeno, quebrava sob um contexto grande demais.
O ciclo 2 ataca a causa (menos contexto); o ciclo 1, o sintoma que sobra.

---

<a id="ciclo-1"></a>

## Ciclo 1 — Tool calls vazadas como texto

### Problema observado

O agente imprimia a chamada de ferramenta **crua no terminal**, em vez de
executá-la. Transcrição real da sessão que originou a investigação:

```text
ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem.
(digite 'sair' para encerrar)
ItinerAI: Encontrei uma viagem em andamento para Espanha. Deseja retomá-la? (s/n)
Você: não
ItinerAI: Qual o seu próximo destino?
Você: Monte um itinerário de 3 dias para a Inglaterra
ItinerAI: function=build_itinerary>{"destination": "Inglaterra", "num_days": 3}</function>

function=search_tourist_attractions>{"destination": "Inglaterra"}</function>
Você:
```

Três defeitos numa saída só:

1. **O usuário vê markup interno.** O modelo emitiu o formato nativo de tool call
   do Llama (`<function=nome>{json}</function>`) como **texto** da resposta. A
   Groq não parseia esse formato, então `tool_calls` chegou vazio e o texto cru
   foi direto ao terminal.
2. **Nenhuma ferramenta rodou.** Sem `tool_calls` estruturados, o roteador
   `route_after_llm` via uma resposta comum e ia para `END`. O roteiro nunca
   seria montado.
3. **A ordem estava invertida.** O modelo pediu `build_itinerary` **antes** de
   `search_tourist_attractions` — montar o roteiro sem ter buscado as atrações.

### Alteração realizada

Duas frentes, deliberadamente: o prompt reduz a **frequência**, o código trata o
que escapa.

**Na origem — `AGENT_SYSTEM_PROMPT`:**

```
Regras ao usar as ferramentas: chame apenas UMA ferramenta por vez e NUNCA
escreva a chamada de ferramenta como texto na sua resposta. Sempre use
`search_tourist_attractions` ANTES de `build_itinerary`: só monte o roteiro
depois que a busca de pontos turísticos retornar.
```

Cada oração corresponde a um dos três defeitos acima, na ordem.

**Como rede de segurança — `nodes.py`** (+77 linhas no commit):

| Função | Papel |
| --- | --- |
| `_LEAKED_TOOL_CALL_RE` | regex que reconhece `<function=nome>{json}</function>` |
| `_parse_leaked_tool_calls` | reconstrói tool calls válidas; **ignora com tolerância** nomes desconhecidos e JSON truncado |
| `_drop_premature_build_itinerary` | descarta o `build_itinerary` quando há busca no mesmo lote |
| `_repair_leaked_response` | orquestra: sem nada recuperável, troca o texto cru por um aviso amigável |

Três decisões de design que valem registro:

- **O reparo é determinístico** (regex + `json.loads`), sem nenhuma chamada extra
  ao LLM. Mesma filosofia da validação de entrada: não usar o modelo para
  consertar o modelo.
- **`_drop_premature_build_itinerary` vale também para tool calls
  estruturados**, não só vazados. `call_llm` o aplica antes do roteamento, para
  que `merge_pages` responda sempre a exatamente um `tool_call_id`.
- **Falha visível, nunca silenciosa.** Se nada for recuperável, o usuário recebe
  uma mensagem em português — nunca o `<function=...>`.

### Resultado obtido

| Evidência | Onde |
| --- | --- |
| O markup nunca mais chega ao terminal | `_repair_leaked_response` cobre os dois desfechos: recupera, ou substitui por aviso |
| Regressão travada por testes | `test_repair_recovers_leaked_call` (`tests/utils/test_nodes_helpers.py:112`) e `test_call_llm_recovers_leaked` (`tests/utils/test_nodes.py:303`) |
| Ocorrências ficam observáveis | eventos `leaked_tool_calls_recovered` (com nome e contagem) e `leaked_tool_calls_unrecoverable` em `logs/itinerai.log` |
| Nenhum vazamento nas execuções recentes | os 354 eventos analisados na T06 não contêm nenhum dos dois eventos |

O `llama-3.1-8b-instant` foi desligado pela Groq em 16/08/2026 e substituído pelo
`openai/gpt-oss-120b`, que erra muito menos. **A proteção foi mantida**: o custo
é uma regex e um `if`, e o modelo é configurável por `GROQ_MODEL` — um modelo
mais fraco pode voltar a qualquer momento.

---

<a id="ciclo-2"></a>

## Ciclo 2 — Redução do escopo de ferramentas

### Problema observado

O agente nasceu com **quatro** ferramentas: busca de pontos turísticos, busca de
eventos e festivais (`search_events_and_festivals`, commit `9622c14`), cálculo da
duração entre duas datas (`calculate_trip_days`) e construção do itinerário.

Com o `llama-3.1-8b-instant`, esse escopo produzia sintomas recorrentes:
`tool_use_failed`, JSON truncado, ferramenta errada escolhida e a coleta de
campos obrigatórios saindo de ordem. O diagnóstico, registrado no prompt original
do usuário:

> *"Por se tratar de um modelo simples, o montante de ferramentas pode estar
> causando sobrecarga de contexto na LLM."*

O peso não estava só na quantidade de ferramentas, mas no **texto que cada uma
arrastava para o system prompt**. A de eventos sozinha ocupava 14 linhas de
instrução, incluindo um `disclaimer` que o modelo tinha de repassar na íntegra; a
de datas exigia explicar dois formatos de entrada, validação e o caminho de erro.

### Alteração realizada

**Escopo cortado pela metade** — de 4 ferramentas para 2:

| Removida | Substituída por |
| --- | --- |
| `search_events_and_festivals` | nada; eventos saíram do produto |
| `calculate_trip_days` | o usuário informa a duração **em dias**, direto |

E o corte foi seguido de outras simplificações na mesma direção: os períodos do
dia (Manhã/Tarde/Noite) saíram do itinerário, e o máximo de atrações por dia foi
fixado em 3.

Efeito medido no commit `5e57116`:

| Arquivo | Inserções | Deleções | Líquido |
| --- | ---: | ---: | ---: |
| `itinerai_agent/utils/tools.py` | 33 | 257 | **−224** |
| `itinerai_agent/utils/prompts.py` | 21 | 70 | **−49** |
| `itinerai_agent/utils/state.py` | 6 | 28 | −22 |
| `itinerai_agent/utils/nodes.py` | 77 | 29 | +48 (ciclo 1) |
| **commit inteiro** | **240** | **461** | **−221** |

O `AGENT_SYSTEM_PROMPT` encolheu ~49 linhas líquidas — o parágrafo de eventos e o
de datas desapareceram inteiros, e a coleta de campos passou de *"as datas de ida
e volta OU o número de dias"* para *"a duração da viagem em dias"*.

### Justificativa da decisão

O que se perdeu foi **funcionalidade opcional**; o que se ganhou foi
confiabilidade no caminho principal. Três razões sustentam a troca:

1. **A ferramenta de eventos era a de menor valor e maior custo.** A Wikipédia é
   texto estático: os eventos não têm data confiável, e o próprio prompt tinha de
   avisar o usuário para confirmar dia e horário no site oficial. Uma ferramenta
   cuja saída precisa de ressalva é uma ferramenta de baixa confiança.
2. **`calculate_trip_days` resolvia um problema autoinfligido.** Ela existia para
   aceitar datas; pedir a duração em dias elimina a ferramenta *e* o caminho de
   erro de validação de datas.
3. **Contexto é recurso escasso num modelo pequeno.** Cada ferramenta ocupa
   espaço no system prompt e no schema exposto pelo `bind_tools`, competindo com
   as regras de comportamento.

### Resultado obtido

| Evidência | Onde |
| --- | --- |
| Duas ferramentas, schemas mínimos | `search_tourist_attractions(destination)` e `build_itinerary(destination, num_days)`; as atrações entram por `InjectedToolArg`, invisíveis ao modelo |
| Coleta de campos estável | nos turnos analisados na T06, o agente pediu a duração no momento certo e chamou a busca antes do roteiro, sem intervenção |
| Escopo congelado | o `CLAUDE.md` passou a proibir novas funcionalidades sem alinhamento prévio — a decisão virou regra do projeto |

**Limitação assumida:** o produto perdeu a busca de eventos e a entrada por
datas. É um recuo deliberado de escopo em favor de confiabilidade, e não foi
revertido nem depois da troca para o `openai/gpt-oss-120b` — o escopo menor
continua sendo o desenho preferido.

---

## O que os dois ciclos têm em comum

Os dois seguem o mesmo princípio, que o `CLAUDE.md` registra como regra: **não
usar o LLM para compensar o LLM.** O ciclo 1 conserta a saída do modelo com
regex; o ciclo 2 reduz o que se pede a ele. Nenhum dos dois adiciona uma chamada
de modelo para supervisionar outra.

O mesmo princípio aparece na validação de entrada (regex, sem LLM), na escolha da
página no fan-out (`merge_pages`, determinística) e na aprovação do envio por
e-mail (pergunta s/n fora do grafo).
