# Code review assistido por IA — PR #40

Revisão assistida por IA de uma alteração real do projeto, com achados
classificados por severidade e priorizados por risco e impacto no domínio,
conforme o §4.7.

| | |
| --- | --- |
| **PR revisado** | [#40 — feat: envio do roteiro por e-mail via webhook do n8n (T14/#25)](https://github.com/joaopuel/mini-projeto-ItinerAI/pull/40) |
| **Branch** | `feature/low-code-n8n-app` → `develop` |
| **Commits** | `95070f1`, `9a5c57b`, `183464f`, `19f588b`, `025c998`, `53c706a` |
| **Data da revisão** | 2026-08-30 |
| **Método** | Leitura estática do diff, do código-fonte e do workflow do n8n. Nenhuma execução da aplicação (restrição vigente na T14). Afirmações verificáveis foram conferidas — ver M4. |

## Escopo da alteração

Integração da aplicação ao webhook do n8n para envio do itinerário por e-mail:
módulo novo `notifications.py` (cliente HTTP com timeout/retry/fallback), nó
`notify_recipient` e roteador `route_entry` no grafo, campos novos no
`AgentState`, validação de e-mail por regex, aprovação humana no `main.py`, três
variáveis de ambiente, documentação e a análise de logs do CI.

**379 linhas de código** em 8 arquivos, mais documentação e evidências.

---

## Critério de severidade

| Severidade | Significado | Efeito sobre a entrega |
| --- | --- | --- |
| 🔴 **Crítico** | Exposição de credencial, perda de dado ou falha de segurança explorável | **Bloqueante** |
| 🟠 Alto | Defeito provável ou lacuna estrutural de garantia | Exige tarefa registrada antes da entrega final |
| 🟡 Médio | Defeito latente, contradição entre código e documentação, ou lacuna de rastreabilidade | Entra no backlog com prazo |
| 🔵 Baixo | Cosmético, organizacional ou sem impacto observável | Oportunístico |

**Achados críticos são bloqueantes: o PR não deve ser mesclado enquanto houver um
🔴 em aberto.** O regime é o mesmo dos gates do CI — assim como o job `test`
reprova quando a cobertura do código novo cai abaixo de 70%, um achado crítico
reprova a revisão. A diferença é que o gate do CI é automático e este é humano, o
que torna o bloqueio uma decisão explícita em vez de um efeito colateral.

Vale registrar que, nesta revisão, **o achado bloqueante não foi detectado por
nenhum gate automático** (ver A1): `lint` e `build` ficaram verdes. O bloqueio
depende inteiramente da revisão humana.

---

## Resumo dos achados

| ID | Severidade | Achado |
| --- | --- | --- |
| **C1** | 🔴 Crítico | Token do webhook hardcoded em `config.py` |
| **A1** | 🟠 Alto | Pipeline não tem varredura de segredos |
| **A2** | 🟠 Alto | Módulo de integração externa sem nenhum teste |
| **M1** | 🟡 Médio | Retry sobre POST não-idempotente pode duplicar e-mail |
| **M2** | 🟡 Médio | Contrato "nunca levanta" mais estreito que o documentado |
| **M3** | 🟡 Médio | Recusa e e-mail inválido não deixam rastro na auditoria |
| **M4** | 🟡 Médio | Documentação afirma paridade de regex que não existe |
| **B1** | 🔵 Baixo | Nome da pasta de evidências divergia do backlog |
| **B2** | 🔵 Baixo | Ctrl+C na coleta do e-mail é registrado como `invalid_email` |
| **B3** | 🔵 Baixo | Duas `AIMessage` consecutivas no histórico |
| **B4** | 🔵 Baixo | `route_entry` emite log de roteamento em todo turno |

---

## 🔴 C1 — Token do webhook hardcoded em `config.py` · **BLOQUEANTE**

**Arquivo:** `itinerai_agent/utils/config.py:31` · **Commits:** `025c998`, `53c706a`

```diff
-N8N_WEBHOOK_TOKEN = os.getenv("N8N_WEBHOOK_TOKEN", "").strip()
+N8N_WEBHOOK_TOKEN= '<token real de 43 caracteres — omitido deste documento>'
```

### Por que é crítico

O valor é a **credencial real** da instância n8n do autor, criada nesta mesma
entrega. O repositório é público e o commit **já está no remoto**
(`origin/feature/low-code-n8n-app`).

Quem obtiver o par URL + token pode disparar e-mails pela conta SMTP do autor
para **qualquer destinatário**, com conteúdo arbitrário no campo `markdown` —
efetivamente um relay aberto, com o custo e a reputação do remetente. A URL do
webhook, por si só, é o dado menos protegido dos dois: ela aparece em qualquer
log de rede e no `.env` de qualquer máquina que rode o agente.

### O que agrava

O achado contradiz, simultaneamente:

- a regra do `CLAUDE.md` — "nunca hardcode a chave; carregue de `.env`/ambiente";
- o checklist da #24 e da #25 — "nunca versionar o segredo";
- o **comentário na linha imediatamente acima**, que continua dizendo "Nunca
  versionado";
- o `.env.example` e o `README.md`, que documentam a variável como configurável e
  passam a descrever um comportamento que o código não tem mais.

Efeito colateral funcional: `N8N_WEBHOOK_TOKEN` deixou de ser configurável. Quem
clonar o projeto e puser o próprio token no `.env` será silenciosamente ignorado.

### Contexto

O commit `025c998` se chama *"Adição de falha de segurança para simular erro no
CR"* — a falha foi **plantada deliberadamente** para este exercício. Isso explica
a origem, mas **não neutraliza a exposição**: o token é real e o histórico é
público.

### Correção

```python
N8N_WEBHOOK_TOKEN = os.getenv("N8N_WEBHOOK_TOKEN", "").strip()
```

### ⚠️ Ação urgente, independente da correção do código

**Rotacionar o token na credencial `ItinerAI Webhook Token` do n8n.** Remover a
linha num commit futuro **não apaga o valor do histórico do git** — ele
permanece recuperável em `git log -p`, na aba de commits do PR e em qualquer
clone ou fork já feito. Rotacionar é o único passo que efetivamente invalida a
exposição.

---

## 🟠 A1 — O pipeline não tem varredura de segredos

**Arquivo:** `.github/workflows/ci.yml`

O C1 passou por **todos os gates do CI**. Na execução
[33333506048](https://github.com/joaopuel/mini-projeto-ItinerAI/actions/runs/33333506048),
`lint` ✓ e `build` ✓; o único job vermelho foi por cobertura, sem nenhuma relação
com o segredo.

Nenhum mecanismo atual detectaria:

- **Ruff** — as regras ativas (`E4`, `E7`, `E9`, `F`) tratam de erros de sintaxe,
  imports e nomes; não olham conteúdo de literais.
- **`diff-cover`** — mede cobertura, não conteúdo.
- **Secret scanning do GitHub** — dispara em padrões de provedores conhecidos
  (`gsk_`, `ghp_`, chaves AWS). Uma string aleatória de 43 caracteres sem prefixo
  reconhecível não aciona o alerta.

### Impacto no domínio

O projeto inteiro se apoia na premissa "segredo só no ambiente" — `GROQ_API_KEY`,
`N8N_WEBHOOK_TOKEN`, credencial SMTP. Sem gate automatizado, essa premissa é
sustentada apenas por disciplina, e o C1 é a prova de que a disciplina falha.

### Correção

Um passo `gitleaks` no job `lint`, bloqueante. É a causa-raiz do C1: sem ele,
nada impede a próxima credencial de entrar pelo mesmo caminho.

---

## 🟠 A2 — Módulo de integração externa sem nenhum teste

**Arquivos:** `notifications.py` (44% de cobertura), `nodes.py` (41,2% no diff)

Todo o caminho de erro está descoberto: o laço de retry, o backoff, o fallback
para `status="failed"`, a degradação por ausência de configuração e o
mascaramento do e-mail. Evidência em
[`evidencias/ci-run-33333506048-diff-cover.md`](evidencias/ci-run-33333506048-diff-cover.md).

### Impacto no domínio

É o **único** código do projeto que faz chamada de rede autenticada e manipula
dado pessoal do usuário. É, por definição, o trecho onde um teste vale mais — e é
o único módulo sem nenhum.

### Contexto

A ausência de testes foi imposta como restrição da T14, para que a reprovação do
gate de cobertura servisse de evidência em [`analise-ci.md`](analise-ci.md).
Escrever os testes agora destruiria esse artefato. A lacuna, porém, é real e
permanece.

---

## 🟡 M1 — Retry sobre POST não-idempotente pode duplicar o e-mail

**Arquivo:** `itinerai_agent/utils/notifications.py:109-134`

`_post_with_retry` repete a requisição em `Timeout` e `ConnectionError`, até 3
tentativas. Mas o `Timeout` do lado do cliente **não significa que o servidor não
processou**: se o n8n recebeu o POST, disparou o e-mail e a resposta demorou mais
que `N8N_TIMEOUT`, a retentativa manda **outro e-mail**. Até 3 cópias do mesmo
roteiro.

### Por que importa aqui mais que em outros lugares

O mesmo padrão de retry foi copiado de `_get_wikipedia`, onde é seguro — um GET
repetido não tem efeito colateral. Aqui o efeito colateral é justamente a ação
que o §4.5 classifica como **irreversível** e para a qual se exigiu aprovação
humana explícita. O código pede permissão uma vez e então repete a ação
automaticamente até três vezes.

O `run_id` já viaja no payload e serviria de chave de idempotência, mas o
workflow do n8n não o utiliza para deduplicar.

### Correção

Duas opções:

1. **Nó de deduplicação por `run_id` no workflow do n8n** — preserva a
   resiliência a falha real de rede. Preferível.
2. **Não repetir em POST** — uma única tentativa, e a falha vira
   `status="failed"`. Mais simples, mas perde a tolerância a instabilidade
   transitória.

---

## 🟡 M2 — O contrato "nunca levanta" é mais estreito que o documentado

**Arquivo:** `itinerai_agent/utils/notifications.py:137-142, 156-172`

A docstring de `send_itinerary` afirma: *"Nunca levanta: uma falha de rede, um
status HTTP de erro ou a ausência de configuração viram um
`NotificationResult`."* Mas o `except` captura apenas `RequestException`.

Uma exceção fora dessa família — serialização do payload, por exemplo — escapa da
função, é re-levantada por `_logged_node`, re-levantada por `_run_turn` e
**derruba a aplicação**. Isso viola o critério de aceitação da #23: *"A falha da
integração não derruba a aplicação"*.

**Probabilidade baixa** (o payload é composto de `str` e `int` simples),
**impacto alto** (crash do processo, com o roteiro já gerado em `output/` mas a
sessão perdida).

### Correção

Trocar por `except Exception` **não** serve: violaria a regra do `CLAUDE.md`
("Exceções específicas, não `except Exception`; falha alto em bug, degrada em
rede"). Duas alternativas compatíveis com essa regra:

1. **Estreitar a docstring** para "nunca levanta em falha de rede ou de
   configuração" — documenta o comportamento real e mantém bug como bug;
2. **Capturar de forma ampla apenas na fronteira do nó** (`notify_recipient`), se
   a garantia de não-crash for requisito firme — ali a decisão é de produto, não
   de biblioteca.

---

## 🟡 M3 — Recusa e e-mail inválido não deixam rastro na auditoria

**Arquivo:** `main.py:_offer_email`

Os desfechos `declined` e `invalid_email` são gravados **direto no estado**, sem
passar pelo grafo. Consequência: não emitem nenhum `logger.*` nem qualquer linha
em `execution_audit`. Só o caminho "sim" produz sinais, porque só ele chega ao nó
instrumentado.

### Impacto no domínio

Para a narrativa do §4.5 — limite de autonomia — a **recusa** é precisamente o
evento que se quer auditável: é a prova de que o agente perguntou, o humano disse
não e nada foi enviado. Hoje a trilha registra apenas os envios; a ausência de
registro é indistinguível de "nunca perguntou".

### Correção

Emitir em `_offer_email` um `logger.info("notification_declined")` /
`("notification_invalid_email")` e a linha de auditoria correspondente, com o
`run_id` do turno anterior. Correção pequena e de alto valor probatório.

---

## 🟡 M4 — A documentação afirma uma paridade de regex que não existe

**Arquivos:** `itinerai_agent/utils/validation.py:120-123`, `CLAUDE.md`

O comentário afirma: *"Mesmo regex do nó `Validar payload` do workflow, **para os
dois lados recusarem exatamente as mesmas entradas**"*. Os dois padrões não são
iguais:

| | Padrão |
| --- | --- |
| Aplicação | `^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$` |
| Workflow n8n | `^[^@\s]+@[^@\s.]+\.[^@\s]+$` |

Verificado por comparação direta dos dois padrões:

| Entrada | Aplicação | n8n | |
| --- | --- | --- | --- |
| `a@b.co` | aceita | aceita | ✓ concordam |
| `joao@exemplo.com.br` | aceita | aceita | ✓ concordam |
| `a@b.c.` | **recusa** | **aceita** | ✗ divergem |
| `a@b..c` | **recusa** | **aceita** | ✗ divergem |
| `a@b` | recusa | recusa | ✓ concordam |

A causa é que `[^@\s]+` no padrão do n8n permite pontos, aceitando rótulos vazios
e ponto final; a aplicação exige rótulos não vazios separados por ponto.

### Impacto

**Prático hoje: nenhum.** A aplicação valida primeiro e é a **mais estrita**, então
o n8n nunca recebe um endereço que a aplicação teria recusado — a divergência é
inalcançável pelo fluxo normal.

**Real: a afirmação é falsa**, e é o tipo de comentário em que se confia para
mexer num lado supondo que o outro acompanha. Se um dia o webhook passar a ser
chamado por outro cliente, a diferença deixa de ser teórica.

### Correção

Corrigir a afirmação — a aplicação é *mais estrita* que o workflow, e é isso que
garante a segurança do fluxo — ou igualar literalmente os dois padrões.

---

## 🔵 Achados de baixa severidade

### B1 — nome da pasta de evidências divergia do backlog

O `tasks.md` planeja `docs/evidencias/` na T11 e na T16, mas a pasta foi criada
como `docs/evidences/`. Risco real: as duas coexistirem e a evidência ficar
espalhada.

**Correção:** a pasta foi renomeada para **`docs/evidencias/`**, o nome original
da demanda, e os links das duas análises acompanharam. Prevaleceu o backlog —
que é o documento que o avaliador segue — sobre a convenção de "pastas em inglês"
do `CLAUDE.md`, que vale para o código-fonte. Vale registrar a exceção no
`CLAUDE.md` para ninguém "corrigir" de volta.

### B2 — Ctrl+C na coleta do e-mail vira `invalid_email`

`_prompt_text` devolve `""` em `KeyboardInterrupt`, que reprova na validação e é
registrado como `invalid_email`. Semanticamente é cancelamento, não endereço
malformado. Polui levemente o desfecho auditado; sem impacto funcional.

**Correção:** um desfecho `cancelled` distinto, ou tratar a interrupção antes da
validação.

### B3 — Duas `AIMessage` consecutivas no histórico

O turno de notificação acrescenta uma `AIMessage` sem `HumanMessage` anterior. A
API tolera e nenhum comportamento anômalo foi observado.

**Custo da correção:** exigiria injetar uma mensagem sintética no histórico — o
que suja mais a conversa do que a sequência que pretende arrumar. O custo supera
o benefício enquanto não houver sintoma observado.

### B4 — `route_entry` emite `routing_decision` em todo turno

Uma linha de log a mais por turno, quase sempre com a mesma decisão
(`validate_input`).

**Custo da correção:** não decorar o roteador quebraria a consistência com
`route_after_validation` e `route_after_llm`, criando uma exceção que alguém
teria de explicar depois. O custo de uma linha de log é menor que o da exceção.

---

## Priorização por risco e impacto

Cada achado avaliado por **probabilidade de se materializar** × **impacto no
domínio da aplicação**.

| ID | Probabilidade | Impacto | Prioridade | Justificativa no domínio |
| --- | --- | --- | --- | --- |
| **C1** | **Certa** — já ocorreu | **Crítico** | **P0 — bloqueante** | Credencial real exposta em repositório público. Permite relay de e-mail pela conta do autor. |
| **A1** | Alta | Alto | **P1** | Sem este gate, o C1 se repete. É a causa-raiz, não o sintoma. |
| **M3** | Certa — ocorre em toda recusa | Médio | **P1** | Compromete a evidência do §4.5, que vale nota na avaliação. Correção pequena. |
| **M1** | Média — depende de timeout real | Alto | **P2** | E-mail duplicado é visível ao usuário final e contradiz o desenho de "ação irreversível com aprovação". |
| **A2** | Alta | Médio | **P2** | Alta chance de defeito latente no módulo mais arriscado, mas hoje mitigado por teste manual ponta a ponta. |
| **M2** | Baixa | Alto | **P3** | Crash da sessão. Improvável com o payload atual; degrada mal se acontecer. |
| **M4** | Baixa | Baixo | **P3** | Inalcançável pelo fluxo atual. É dívida de documentação, que só vira defeito com um segundo cliente. |
| **B1** | Certa | Muito baixo | **P4** | Organização de evidências para o avaliador. |
| **B2** | Baixa | Muito baixo | **P4** | Cosmético. |

**Ordem de ataque recomendada:** C1 (com rotação do token) → A1 → M3 → M1 → A2.

Duas observações sobre a ordem:

- **C1 é bloqueante** — enquanto estiver em aberto, os demais itens são
  irrelevantes para a decisão de mesclar. Nenhum outro achado tem esse peso.
- **C1 e A1 andam juntos.** Corrigir apenas o C1 remove o sintoma e deixa a
  causa: nada impede a próxima credencial de entrar pelo mesmo caminho. A
  varredura de segredos é o que transforma a regra em garantia.

---

## Anexo — prompt utilizado

Prompt do usuário que originou esta revisão (sessão de 2026-08-30, verbatim):

```
Também vamos trabalhar a task [DOCS] Code review com IA de uma alteração real e
priorização por risco junto a esta implementação. Gere uma análise de CR em
/docs/analise-cr.md referente as implementações realizadas em
https://github.com/joaopuel/mini-projeto-ItinerAI/pull/40. Classifique pontos com
priorização baseada em risco, impacto ou criticidade.
```

Comandos usados para levantar o diff (todos somente leitura):

```bash
git log --oneline origin/develop..HEAD
git show 025c998 --stat
git diff 19f588b..HEAD
grep -o '"rightValue": "\^\[^@[^"]*"' docs/low-code/n8n-workflow.json
```

### Nota de transparência

Boa parte do código revisado foi escrita pelo mesmo assistente que produz esta
revisão, na T14/#25. Um autor revisando o próprio trabalho tende ao viés de
confirmação, e os achados M2, M3 e M4 são defeitos de código e documentação que eu
próprio introduzi — M4 inclusive contradiz uma afirmação que escrevi no
`CLAUDE.md`. Registro o conflito para que a revisão seja lida com o desconto
apropriado, e recomendo que os achados P0 e P1 sejam conferidos de forma
independente.
