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
| 🟠 Alto | Defeito provável ou lacuna estrutural de garantia | Não bloqueia; pode ser endereçado numa versão posterior, com o risco residual assumido por escrito |
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

### Correção — mapeada para uma versão futura

Um passo `gitleaks` no job `lint`, bloqueante. É a causa-raiz do C1: sem ele,
nada impede a próxima credencial de entrar pelo mesmo caminho.

**Não entra na entrega final**, por decisão de escopo: o CI não será mais
alterado, e a entrega fica restrita às demandas já previstas no backlog
(`docs/tasks.md`). Ver "Risco residual assumido", ao final.

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

> Esta priorização é a da revisão original, e permanece como registro do
> raciocínio. A ordem foi seguida com **uma exceção deliberada**: o A1 saiu do
> escopo desta entrega — ver "Risco residual assumido".

---

## Situação após as correções

Atualizado em 2026-08-30, após os commits `86f2ece` (correções), `4563ec3`
(testes) e `3f39737` (documentação e renomeação), com o
[run 33338449639](https://github.com/joaopuel/mini-projeto-ItinerAI/actions/runs/33338449639)
do CI **verde nos três jobs** e a credencial do n8n rotacionada.

### Decisão por achado

**Aceito** = corrigido nesta entrega · **Recusado** = não será corrigido, com o
motivo registrado · **Adiado** = achado válido, endereçado numa versão futura.

| ID | Sev. | Decisão | Justificativa e situação | Commit |
| --- | --- | --- | --- | --- |
| **C1** | 🔴 | **Aceito** | Exposição de credencial real em repositório público — não havia alternativa a corrigir. Fechado por duas frentes: `config.py` voltou a ler do ambiente **e** a credencial foi rotacionada no n8n. O valor que restou no histórico é hoje um token morto. | `86f2ece` + rotação |
| **A1** | 🟠 | **Adiado** | Achado válido e causa-raiz do C1, mas o CI não será mais alterado: a entrega final fica restrita ao backlog. Mapeado para uma versão futura, com o risco residual assumido por escrito abaixo. | — |
| **A2** | 🟠 | **Aceito** | Era o único módulo do projeto com chamada de rede autenticada e sem nenhum teste. Suíte escrita e **verificada no CI**: 238 testes, `notifications.py` de 44% para 100%. | `4563ec3` |
| **M1** | 🟡 | **Aceito** | O retry sobre um POST não idempotente podia entregar até três cópias do mesmo e-mail. Corrigido para tentativa única, com a regressão travada por `test_timeout_does_not_retry`. | `86f2ece` |
| **M2** | 🟡 | **Aceito** | O docstring prometia mais do que o `except` entregava, contrariando o critério de aceitação da #23. Corrigido nas duas pontas: docstring ajustado ao real e captura ampla na fronteira do nó. | `86f2ece` |
| **M3** | 🟡 | **Aceito** | A recusa do usuário é a evidência do limite de autonomia do §4.5 e não deixava rastro algum. Correção pequena, valor probatório alto. | `86f2ece` |
| **M4** | 🟡 | **Aceito** | A afirmação de paridade entre os dois regex foi verificada e é falsa. Corrigida a documentação; os padrões **não** foram igualados, para não exigir reimportação do workflow na conta do autor. | `86f2ece` |
| **B1** | 🔵 | **Aceito** | Divergência real de nomenclatura. Resolvido **ao contrário do que a revisão sugeria**: prevaleceu o nome do backlog (`docs/evidencias/`), que é o que o avaliador procura, com a exceção registrada no `CLAUDE.md`. | `3f39737` |
| **B2** | 🔵 | **Aceito** | Ctrl+C na coleta do e-mail era registrado como "endereço malformado". Passa a ter o desfecho `cancelled`, distinto. | `86f2ece` |
| **B3** | 🔵 | **Recusado** | Corrigir as duas `AIMessage` consecutivas exigiria injetar uma mensagem sintética no histórico — que suja mais a conversa do que a sequência que pretende arrumar. Nenhum sintoma observado, e a API tolera. | — |
| **B4** | 🔵 | **Recusado** | Não decorar `route_entry` quebraria a consistência com `route_after_validation` e `route_after_llm`, criando uma exceção que alguém teria de explicar depois. O custo supera o de uma linha de log por turno. | — |

**Placar: 8 aceitos · 2 recusados · 1 adiado**, sobre os 11 achados da revisão.

---

## O PR pode seguir para o merge?

### ✅ Sim — as duas condições bloqueantes foram atendidas

#### 1. C1 fechado pela rotação da credencial

O código voltou a ler o token do ambiente (`86f2ece`) e **uma nova credencial foi
gerada no n8n**. É a rotação que efetivamente encerra o achado: o valor exposto
nos commits `025c998` e `53c706a` continua no histórico — o git é imutável —, mas
deixou de ser uma credencial válida. O que restou é um token morto.

A prevenção também está no lugar: `N8N_WEBHOOK_TOKEN` é lido por `os.getenv`, de
modo que o **novo** token não tem caminho para o repositório.

> Sugestão de higiene, não condição: um **squash merge** manteria a `develop`
> livre dos dois commits de "falha de segurança", que são artefatos do exercício
> de code review e não trabalho de produto. As referências por SHA feitas neste
> documento continuam resolvendo pelo PR.

#### 2. A2 fechado e verificado no CI

Os testes foram escritos sob a restrição de implementação estática — sem uma
única execução — e eu registrei que aquilo era hipótese, não garantia. O
[run 33338449639](https://github.com/joaopuel/mini-projeto-ItinerAI/actions/runs/33338449639)
resolveu a hipótese, com os três jobs verdes:

| Métrica | Antes (run 33333506048) | Agora (run 33338449639) |
| --- | --- | --- |
| Testes | 200 | **238** |
| Cobertura global | 94% | **99%** |
| `notifications.py` | 44% | **100%** |
| `nodes.py` | 96% | **100%** |
| `diff-cover` (código novo) | **50% — reprovado** | **100% — 0 linhas descobertas** |

O `diff-cover`, que era o único gate vermelho, passou com 89 de 89 linhas
cobertas. E vale registrar: a suíte passou **no primeiro run**, sem correção
intermediária — as quatro execuções vermelhas anteriores são dos commits que
precedem `4563ec3`, quando o código novo ainda não tinha teste algum.

### Risco residual assumido

**A1 — varredura de segredos no CI — não entra na entrega final.** O pipeline não
será mais alterado, e a entrega fica restrita às demandas já previstas no backlog
(`docs/tasks.md`); o A1 está mapeado para uma **versão futura da aplicação**.

A decisão é de escopo, não uma reavaliação do achado: ele continua válido e
continua sendo a causa-raiz do C1. O que muda é quem carrega o risco no
intervalo. Registrando o que fica em aberto, para a decisão ser informada e não
implícita:

- **Nenhum gate do CI detecta uma credencial commitada.** Ruff olha sintaxe e
  imports, `diff-cover` olha cobertura, e o secret scanning do GitHub não dispara
  em string aleatória sem prefixo de provedor. Foi assim que o C1 passou por
  `lint` e `build` verdes.
- **A premissa "segredo só no ambiente"** — que vale para `GROQ_API_KEY`,
  `N8N_WEBHOOK_TOKEN` e a credencial SMTP — segue sustentada por disciplina e
  revisão humana, não por automação.
- **Uma repetição do C1 depende de alguém notar no code review**, como aconteceu
  aqui. Funcionou uma vez; não é garantia.

O risco é aceitável para o escopo de uma entrega avaliativa, com repositório de
um único autor e credenciais descartáveis. Deixa de ser aceitável se a aplicação
ganhar mais colaboradores ou credenciais de valor real — que é exatamente o
gatilho para o A1 sair da versão futura e virar prioridade.

### Veredito

**Liberado para merge.** Dos onze achados: **oito aceitos e corrigidos**, **um
adiado** para uma versão futura com o risco residual assumido acima (A1) e **dois
recusados** por custo superior ao benefício (B3, B4), com o raciocínio registrado
na tabela de decisões.

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
