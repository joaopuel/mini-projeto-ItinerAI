# Documentação e evidências do ItinerAI

Índice de tudo que está em `/docs`. Cada evidência aponta para o requisito que
atende e para os dados brutos que a sustentam.

Para instalação, configuração e execução, ver o [`README.md` da
raiz](../README.md).

## Estrutura

```
docs/
├── README.md                 # este índice
├── requisitos.md             # enunciado da avaliação
├── tasks.md                  # backlog: epics, tarefas e checklists
├── application-structure.md  # referência de estrutura do LangGraph
├── prompts/                  # prompts, instruções de sistema e refinamento
├── qa/                       # análises de qualidade, observabilidade e DevOps
├── evidencias/               # evidência bruta (logs, trilhas, relatórios)
├── low-code/                 # workflow do n8n e instruções de reprodução
└── issues-templates/         # templates das issues do GitHub Project
```

A separação que organiza a pasta é entre **análise** e **evidência bruta**:
`qa/` guarda os documentos que interpretam; `evidencias/` guarda os arquivos
originais que eles citam, versionados porque `logs/` e os bancos SQLite não são.

---

## Prompts e refinamento — §4.10

| Documento | Conteúdo |
| --- | --- |
| [`prompts/historico.md`](prompts/historico.md) | Todos os prompts do projeto, em ordem cronológica, com data, autor e tipo |
| [`prompts/system-prompts.md`](prompts/system-prompts.md) | As três instruções de sistema do agente e **por que cada cláusula existe** |
| [`prompts/refinamentos.md`](prompts/refinamentos.md) | Os dois ciclos de refinamento, em problema → alteração → resultado |

Os dois ciclos: **tool calls vazadas como texto** (o modelo imprimia
`<function=…>` no terminal em vez de executar a ferramenta) e **redução do escopo
de ferramentas** (de 4 para 2, para não sobrecarregar um modelo pequeno).

## QA e testes — §4.7

| Documento | Conteúdo |
| --- | --- |
| [`qa/analise-testes.md`](qa/analise-testes.md) | Priorização de cenários por risco, impacto e criticidade; justificativa do cenário prioritário (prompt injection ponta a ponta) |
| [`qa/analise-cr.md`](qa/analise-cr.md) | Code review assistido por IA do PR #40, com os achados classificados e o desfecho de cada um |

Suíte em `tests/`, com gate de cobertura de 70% aplicado no CI.

## Observabilidade — §4.6

| Documento | Conteúdo |
| --- | --- |
| [`qa/analise-observabilidade.md`](qa/analise-observabilidade.md) | Reconstrução de três execuções reais cruzando logs estruturados e trilha de auditoria pelo `run_id` |

Evidência bruta — 3 turnos, log e trilha de cada:

| `run_id` | Log | Trilha | Desfecho |
| --- | --- | --- | --- |
| `81579be0` | [log](evidencias/run-81579be0-log.jsonl) | [trilha](evidencias/run-81579be0-audit.txt) | busca com fan-out, 12 atrações |
| `9ec40ebb` | [log](evidencias/run-9ec40ebb-log.jsonl) | [trilha](evidencias/run-9ec40ebb-audit.txt) | roteiro gravado, e-mail recusado |
| `c5f84813` | [log](evidencias/run-c5f84813-log.jsonl) | [trilha](evidencias/run-c5f84813-audit.txt) | falha de rede, 4 retries, 2 erros |

**Achado principal:** o log aponta `fetch_destination_page` como gargalo
(7695,1 ms), mas a trilha abre o nó e mostra que 74,4% dele é extração pelo LLM,
não rede. Nenhum dos dois sinais chega a essa conclusão sozinho.

## DevOps e detecção de anomalias — §4.8

| Documento | Conteúdo |
| --- | --- |
| [`qa/analise-ci.md`](qa/analise-ci.md) | Análise assistida por IA dos logs do CI: duas etapas explicadas, duas anomalias, estimativa de probabilidade de falha e mitigações |

Evidência bruta da execução analisada (run `33333506048`, PR #40, reprovada):

- [log do job *Lint (Ruff)*](evidencias/ci-run-33333506048-lint.log)
- [log do job *Testes + cobertura*](evidencias/ci-run-33333506048-test.log)
- [relatório do `diff-cover`](evidencias/ci-run-33333506048-diff-cover.md)

**Anomalia principal:** dois gates de cobertura com o mesmo limiar de 70% e
sensibilidades opostas — o global passou com 94% enquanto o do código novo
reprovou com 50%, na mesma execução.

## Low-code — §4.9

| Documento | Conteúdo |
| --- | --- |
| [`low-code/README.md`](low-code/README.md) | O fluxo do n8n, instruções de reprodução e evidências de execução |
| [`low-code/n8n-workflow.json`](low-code/n8n-workflow.json) | O workflow versionado, sem credenciais |
| [`low-code/payload-exemplo.json`](low-code/payload-exemplo.json) | Payload de exemplo para testar o webhook |

O envio do roteiro por e-mail exige **aprovação humana explícita** (pergunta s/n
e e-mail validado por regex, ambos fora do LLM) — o limite de autonomia do §4.5.

## Planejamento e referência

| Documento | Conteúdo |
| --- | --- |
| [`tasks.md`](tasks.md) | Backlog completo: 6 epics, 19 tarefas, com checklist e escopo entregue de cada |
| [`requisitos.md`](requisitos.md) | Enunciado da avaliação |
| [`roteiro-video.md`](roteiro-video.md) | Roteiro de gravação do vídeo de demonstração, com os 8 blocos de tempo do §5.5 |
| [`application-structure.md`](application-structure.md) | Estrutura recomendada pela documentação do LangGraph, base da organização do código |
| [`issues-templates/`](issues-templates) | Templates de epic, tech, docs e user story usados nas issues |

---

## Mapa rápido: critério do §6 → evidência

| Critério | Onde está |
| --- | --- |
| 11 — observabilidade correlacionada e tratamento de falhas | [`qa/analise-observabilidade.md`](qa/analise-observabilidade.md) + `evidencias/run-*` |
| 12 — QA, testes e priorização por risco | [`qa/analise-testes.md`](qa/analise-testes.md), [`qa/analise-cr.md`](qa/analise-cr.md), `tests/` |
| 13 — CI, análise de logs, anomalia e risco | [`qa/analise-ci.md`](qa/analise-ci.md) + `evidencias/ci-run-*` |
| 14 — integração low-code | [`low-code/`](low-code) |
| 15 — prompts, modelos e refinamento | [`prompts/`](prompts) |
