# Instruções de sistema do agente

As três instruções de sistema do ItinerAI, o que cada uma faz e **por que cada
cláusula não óbvia existe**. Todas vivem em
[`itinerai_agent/utils/prompts.py`](../../itinerai_agent/utils/prompts.py); este
documento é a explicação, não uma cópia — a fonte é o código.

| Prompt | Onde é usado | Modelo | Temperatura |
| --- | --- | --- | --- |
| `AGENT_SYSTEM_PROMPT` | `call_llm`, em toda invocação do agente | `GROQ_MODEL` (padrão `openai/gpt-oss-120b`) | `GROQ_TEMPERATURE` (padrão `0.7`) |
| `ATTRACTION_EXTRACTION_PROMPT` | `_extract_attractions`, um por ramo do fan-out | mesmo modelo | `0` (fixo) |
| `ITINERARY_CLUSTERING_PROMPT` | `_cluster_by_proximity`, dentro de `build_itinerary` | mesmo modelo | `0` (fixo) |

A separação de temperatura é deliberada: a conversa pode variar, a **extração
não**. Um agrupamento por proximidade que muda a cada chamada tornaria o roteiro
irreprodutível.

---

## 1. `AGENT_SYSTEM_PROMPT` — o comportamento do agente

Define a persona, o objetivo e as regras de uso das ferramentas. É a única
instrução que o usuário influencia indiretamente, e por isso a mais defendida:
a validação de entrada (`validation.py`) roda **antes** dela, por regex, sem
passar pelo LLM.

### Coleta ordenada dos campos obrigatórios

> *"Antes de pesquisar qualquer coisa ou montar o roteiro, confirme que você tem
> as duas informações obrigatórias, verificando-as NESTA ORDEM: 1. O destino…
> 2. A duração da viagem em dias."*
>
> *"Peça apenas UMA informação que falte por vez, na ordem acima."*

**Por quê:** a coleta é conduzida pelo prompt, não por código. Pedir as duas de
uma vez produz respostas parciais que o modelo depois interpreta mal; pedir fora
de ordem faz o agente buscar atrações de um destino que ainda não conhece. A
ordem é observável nos logs — no turno `81579be0` o modelo respondeu
`plain_answer` após a busca justamente porque `num_days` ainda faltava (ver
[`analise-observabilidade.md`](../qa/analise-observabilidade.md), §4.1).

### Como repassar o resultado da busca

> *"…se `unavailable` for `true`, avise que houve um problema técnico ao acessar
> a Wikipédia e peça para tentar de novo em instantes (NÃO diga que o destino
> não existe); se `found` for `false` sem `unavailable`, informe educadamente
> que não foi possível encontrar informações desse destino."*

**Por quê:** são dois desfechos com a mesma aparência (nenhuma atração) e causas
opostas — a Wikipédia caiu, ou o destino não tem página. A flag `unavailable`
nasce da política de resiliência da T02/#13 e só serve para alguma coisa se o
prompt souber traduzi-la. É a ponte entre a resiliência e a experiência do
usuário.

### O roteiro não vai para o terminal

> *"O itinerário NÃO é exibido no terminal: ele fica salvo no arquivo. Ao receber
> o resultado, apenas repasse ao usuário… a mensagem de confirmação retornada
> (com o nome do arquivo criado em `output/`) — não liste o roteiro dia a dia."*

**Por quê:** é requisito de produto. Vale registrar o custo medido: mesmo com
essa instrução, a chamada final ao LLM do turno `9ec40ebb` levou **12687,7 ms**,
84% do turno — o modelo processa um contexto grande (as 12 atrações e o
resultado da tool) para produzir uma frase curta.

### Regras de tool-calling

> *"…chame apenas UMA ferramenta por vez e NUNCA escreva a chamada de ferramenta
> como texto na sua resposta. Sempre use `search_tourist_attractions` ANTES de
> `build_itinerary`."*

**Por quê:** cada uma dessas três regras corrige uma falha real, documentada no
[ciclo de refinamento nº 1](refinamentos.md#ciclo-1). Elas atacam o problema na
origem; a rede de segurança em código (`_repair_leaked_response`) trata o que
escapa.

### Atrações injetadas, não repassadas

> *"As atrações já encontradas são fornecidas automaticamente à ferramenta,
> então você NÃO precisa repassá-las."*

**Por quê:** `build_itinerary` recebe as atrações do estado via
`InjectedToolArg`, e o schema exposto ao modelo tem apenas `destination` e
`num_days`. Expor uma lista aninhada de 15 objetos ao modelo era fonte de JSON
truncado.

---

## 2. `ATTRACTION_EXTRACTION_PROMPT` — extrair atrações de uma página

Recebe o texto bruto de uma página da Wikipédia e devolve uma lista tipada de
atrações. Roda **uma vez por ramo** do fan-out da busca.

| Cláusula | Por quê |
| --- | --- |
| *"Liste no máximo 15 pontos turísticos… e NUNCA repita"* | Sem o teto e a proibição de repetição, o modelo entrava em loop e truncava o JSON no meio, derrubando o parse. |
| *"location: … ou, quando não houver, o local provável. Nunca deixe este campo vazio."* | O agrupamento por proximidade depende deste campo. Vazio, o roteiro perde a lógica de reduzir deslocamento. |
| *"Escreva… em português, mesmo que o texto original esteja em inglês"* | As páginas consultadas são `en.wikipedia.org`; a saída ao usuário é em português. |
| *"Responda SOMENTE com um objeto JSON válido, sem… cerca de código"* + o formato explícito | O projeto **não** usa `with_structured_output` — ver §4. O formato precisa estar no prompt. |

**Custo medido:** esta extração foi o gargalo real da busca — **5726,4 ms**, 74%
do nó `fetch_destination_page` e 58% do turno inteiro. A conclusão só apareceu ao
cruzar os dois sinais de observabilidade.

---

## 3. `ITINERARY_CLUSTERING_PROMPT` — agrupar por proximidade

Recebe as atrações com suas localizações e devolve cada uma rotulada com uma
`area`, ordenadas de modo que atrações da mesma região fiquem em sequência. É o
que permite ao `build_itinerary` distribuir os dias reduzindo deslocamento.

| Cláusula | Por quê |
| --- | --- |
| *"name: exatamente o mesmo nome recebido (não traduza nem altere)"* | O nome é a chave de junção com a lista original. Alterado, a atração se perde. |
| *"Inclua todas as atrações recebidas, sem inventar novas nem remover nenhuma"* | Sem isso o modelo resumia a lista, e dias do roteiro ficavam vazios. |
| *"Liste as atrações da mesma area em sequência"* | A distribuição por dias consome a lista em ordem; o agrupamento **é** a ordem. |

**Custo medido:** 1776,1 ms dos 1789,8 ms de `build_itinerary` — **99,2% da
ferramenta é esta chamada**. Agrupar, distribuir pelos dias e gravar o `.md`
custam os 13,7 ms restantes.

---

## 4. Por que a extração não usa `with_structured_output`

Decisão registrada no `CLAUDE.md` e responsável pelo formato explícito de JSON
nos dois prompts de extração.

Com o `openai/gpt-oss-120b`, `ChatGroq.with_structured_output` força
`tool_choice`, e o modelo devolve o JSON como **texto** em vez de uma tool call.
A Groq rejeita isso com `tool_use_failed` ("model did not call a tool").

A solução é `_invoke_structured` (`tools.py`): o formato do JSON é pedido **no
próprio prompt**, e a resposta em texto é parseada por `_extract_json_payload`,
que tolera cercas ` ```json `, texto ao redor e listas "soltas" (embrulhadas no
campo único do schema). A validação final é `schema.model_validate`.

Falhas de extração são auditadas com o motivo — `invoke_exception`, `no_json` ou
`schema_mismatch` — no passo `llm_extraction` da trilha.

---

## 5. O que **não** é um prompt

Três decisões de projeto mantêm o LLM fora de caminhos onde ele seria caro,
imprevisível ou inseguro. Vale registrar aqui porque são, na prática, o
complemento dos prompts acima:

| Função | Como é feito |
| --- | --- |
| Validação de entrada (injeção, idioma, URL) | 100% regex em `validation.py`, **antes** do LLM |
| Escolha da melhor página no fan-out | `merge_pages`, determinístico |
| Aprovação do envio por e-mail | pergunta s/n em `main.py` + regex de e-mail, fora do grafo |
| Memória da última viagem | SQLite, nunca exposta ao modelo durante a conversa |
