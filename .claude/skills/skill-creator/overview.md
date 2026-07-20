# Skills do Agente

Skills do Agente são capacidades modulares que estendem a funcionalidade do Claude. Cada Skill empacota instruções, metadados e recursos opcionais (scripts, modelos) que o Claude usa automaticamente quando relevante.

---

<Note>
  Para saber como a retenção zero de dados (ZDR) se aplica a este recurso, consulte [API e retenção de dados](/docs/en/manage-claude/api-and-data-retention).
</Note>

## Por que usar Skills

Skills são recursos reutilizáveis, baseados em sistema de arquivos, que dão ao Claude expertise específica de domínio: fluxos de trabalho, contexto e boas práticas que transformam um agente de propósito geral em um especialista. Diferente de prompts (instruções no nível da conversa para tarefas pontuais), Skills são carregadas sob demanda, então você não precisa repetir a mesma orientação em várias conversas.

**Principais benefícios:**

* **Especializar o Claude:** Adapte capacidades para tarefas específicas de domínio
* **Reduzir repetição:** Crie uma vez, use automaticamente
* **Compor capacidades:** Combine Skills para tarefas complexas e multietapas

<Note>
  Para mais detalhes sobre a arquitetura e aplicações reais das Skills do Agente, veja o post do blog de engenharia [Equipando agentes para o mundo real com Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills).
</Note>

## Usando Skills

A Anthropic fornece Skills do Agente pré-construídas para tarefas comuns com documentos (PowerPoint, Excel, Word, PDF), e você também pode criar suas próprias Skills personalizadas. Ambas funcionam da mesma forma: uma vez que uma Skill esteja disponível no seu ambiente, o Claude a usa automaticamente quando for relevante para sua solicitação.

**Skills do Agente pré-construídas** estão disponíveis no claude.ai, na Claude API, na [Claude Platform on AWS](/docs/en/build-with-claude/claude-platform-on-aws) e no [Microsoft Foundry](/docs/en/build-with-claude/claude-in-microsoft-foundry). No Microsoft Foundry, as Skills do Agente exigem uma [implantação Hosted on Anthropic](/docs/en/build-with-claude/claude-in-microsoft-foundry#additional-features-not-supported-when-hosted-on-azure). Veja [Skills Disponíveis](#available-skills) para a lista completa.

**Skills personalizadas** permitem empacotar expertise de domínio e conhecimento organizacional. Elas estão disponíveis em todos os produtos do Claude: crie-as no Claude Code, envie-as pela Claude API ou adicione-as nas configurações do claude.ai. Na [Claude Platform on AWS](/docs/en/build-with-claude/claude-platform-on-aws) e no [Microsoft Foundry](/docs/en/build-with-claude/claude-in-microsoft-foundry), envie Skills personalizadas pela Skills API.

<Note>
  **Comece agora:**

  * Para Skills do Agente pré-construídas: veja o [tutorial de início rápido](/docs/en/agents-and-tools/agent-skills/quickstart) para começar a usar as Skills de PowerPoint, Excel, Word e PDF na API
  * Para Skills personalizadas: veja o [Agent Skills Cookbook](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction) para aprender a criar suas próprias Skills
</Note>

## Como as Skills funcionam

As Skills usam o ambiente de VM do Claude para fornecer capacidades além do que é possível apenas com prompts. O Claude opera em uma máquina virtual com acesso ao sistema de arquivos, permitindo que as Skills existam como diretórios contendo instruções, código executável e materiais de referência, organizados como um guia de integração que você criaria para um novo membro da equipe.

Essa arquitetura baseada em sistema de arquivos permite a **divulgação progressiva:** o Claude carrega informações em estágios, conforme necessário, em vez de consumir contexto antecipadamente.

Skills podem conter três tipos de conteúdo, cada um carregado em um momento diferente:

### Nível 1: Metadados (sempre carregados)

O frontmatter YAML da Skill fornece informações de descoberta:

```yaml
---
name: pdf-processing
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
---
```

O Claude carrega esses metadados na inicialização e os inclui no system prompt. A `description` é o que o Claude compara com sua solicitação ao determinar se deve acionar a Skill, então ela precisa indicar tanto o que a Skill faz quanto quando usá-la. Essa abordagem leve significa que você pode instalar muitas Skills sem penalidade de contexto: até que uma Skill seja acionada, apenas seu nome e descrição ocupam contexto.

### Nível 2: Instruções (carregadas quando acionadas)

O corpo principal do SKILL.md contém conhecimento procedural: fluxos de trabalho, boas práticas e orientações:

````markdown
# PDF Processing

## Quick start

Use pdfplumber to extract text from PDFs:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

For advanced form filling, see [FORMS.md](FORMS.md).
````

Quando você solicita algo que corresponde à descrição de uma Skill, o Claude lê o SKILL.md do sistema de arquivos usando bash. Só então esse conteúdo entra na janela de contexto.

### Nível 3: Recursos e código (carregados conforme necessário)

Skills podem incluir materiais adicionais:

```text
pdf-processing/
├── SKILL.md (main instructions)
├── FORMS.md (form-filling guide)
├── REFERENCE.md (detailed API reference)
└── scripts/
    └── fill_form.py (utility script)
```

**Instruções:** Arquivos markdown adicionais (FORMS.md, REFERENCE.md) contendo orientações e fluxos de trabalho especializados

**Código:** Scripts executáveis (fill\_form.py, validate.py) que o Claude executa usando bash, fornecendo operações determinísticas sem carregar seu código no contexto

**Recursos:** Materiais de referência como esquemas de banco de dados, documentação de API, modelos ou exemplos

O Claude acessa esses arquivos apenas quando referenciados. O modelo baseado em sistema de arquivos significa que cada tipo de conteúdo tem pontos fortes diferentes: instruções para orientação flexível, código para confiabilidade, recursos para consulta factual.

| Nível                        | Quando é carregado         | Custo em tokens          | Conteúdo                                                                                                                    |
| ----------------------------- | --------------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Nível 1: Metadados**        | Sempre (na inicialização)   | \~100 tokens por Skill    | `name` e `description` do frontmatter YAML                                                                                    |
| **Nível 2: Instruções**       | Quando a Skill é acionada   | Menos de 5 mil tokens     | Corpo do SKILL.md com instruções e orientações                                                                                |
| **Nível 3+: Recursos**        | Conforme necessário         | Nenhum até serem acessados | Arquivos incluídos. Arquivos de referência entram no contexto quando lidos. Scripts rodam via bash, e apenas a saída entra no contexto |

A divulgação progressiva garante que apenas o conteúdo relevante ocupe a janela de contexto a cada momento.

### A arquitetura das Skills

As Skills rodam em um ambiente de execução de código onde o Claude tem acesso ao sistema de arquivos, comandos bash e capacidades de execução de código. Skills existem como diretórios em uma máquina virtual, e o Claude interage com elas usando os mesmos comandos bash que você usaria para navegar em arquivos no seu computador.

![Arquitetura das Agent Skills - mostrando como as Skills se integram à configuração do agente e à máquina virtual](/docs/images/agent-skills-architecture.png)

**Como o Claude acessa o conteúdo de uma Skill:**

Quando uma Skill é acionada, o Claude usa bash para ler o SKILL.md do sistema de arquivos, trazendo suas instruções para a janela de contexto. Se essas instruções referenciarem outros arquivos (como FORMS.md ou um esquema de banco de dados), o Claude lê esses arquivos também, usando comandos bash adicionais. Quando as instruções mencionam scripts executáveis, o Claude os executa via bash e recebe apenas a saída (o código do script em si nunca entra no contexto).

**O que essa arquitetura permite:**

* **Acesso a arquivos sob demanda:** O Claude lê apenas os arquivos que cada tarefa precisa. Uma Skill pode incluir dezenas de arquivos de referência, mas se sua tarefa só precisa do esquema de vendas, esse é o único arquivo que o Claude carrega. O restante permanece no sistema de arquivos e não consome tokens.
* **Execução eficiente de scripts:** Quando o Claude executa `validate_form.py`, o código do script nunca é carregado na janela de contexto. Apenas sua saída (como "Validação aprovada" ou uma mensagem de erro específica) consome tokens, o que torna scripts muito mais eficientes do que fazer o Claude gerar código equivalente em tempo real.
* **Sem limite prático de conteúdo incluído:** Os arquivos não consomem contexto até serem acessados, então as Skills podem incluir documentação abrangente de API, grandes conjuntos de dados ou exemplos extensos. Não há penalidade de contexto para conteúdo incluído que não é usado.

### Exemplo: carregando uma Skill de processamento de PDF

Veja como o Claude carrega e usa a Skill personalizada `pdf-processing` dos exemplos anteriores (não a Skill pré-construída `pdf`):

1. **Inicialização:** O system prompt inclui: `pdf-processing - Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.`
2. **Solicitação do usuário:** "Extraia o texto deste PDF e resuma"
3. **O Claude invoca:** `bash: cat pdf-processing/SKILL.md` → Instruções carregadas no contexto
4. **O Claude determina:** o preenchimento de formulários não é necessário, então o FORMS.md não é lido
5. **O Claude executa:** usa as instruções do SKILL.md para concluir a tarefa

![Skills carregando no contexto - mostrando o carregamento progressivo dos metadados e conteúdo da skill](/docs/images/agent-skills-context-window.png)

## Onde as Skills funcionam

Skills estão disponíveis em todos os produtos de agente do Claude:

<Note>
  Claude Platform on AWS e Microsoft Foundry herdam o mesmo comportamento de Skills que a Claude API em todas as seções a seguir.
</Note>

### Claude API

A Claude API suporta tanto Skills do Agente pré-construídas quanto Skills personalizadas. Ambas funcionam de forma idêntica: especifique o `skill_id` relevante no parâmetro `container` junto com a [ferramenta de execução de código](/docs/en/agents-and-tools/tool-use/code-execution-tool).

**Pré-requisitos:** Usar Skills pela API exige a [ferramenta de execução de código](/docs/en/agents-and-tools/tool-use/code-execution-tool), cujo container é onde as Skills são executadas, e um cabeçalho beta:

* `skills-2025-10-02` - Habilita a funcionalidade de Skills

Adicione um segundo cabeçalho, `files-api-2025-04-14`, quando usar a [Files API](/docs/en/build-with-claude/files) para enviar arquivos de entrada ao container ou baixar arquivos que uma Skill produz.

Use as Skills do Agente pré-construídas referenciando seu `skill_id` (`pptx`, `xlsx`, `docx` ou `pdf`), ou crie e envie as suas próprias pela Skills API (endpoints `/v1/skills`). Skills personalizadas são compartilhadas em todo o workspace: todos os membros do workspace podem acessá-las.

As Skills na API rodam em um container isolado sem acesso à rede e sem instalação de pacotes em tempo de execução. Veja [Limitações e restrições](#limitations-and-constraints) para detalhes.

Para saber mais, veja [Usando Agent Skills com a API](/docs/en/build-with-claude/skills-guide).

### Claude Code

O [Claude Code](https://code.claude.com/docs/en/overview) suporta Skills personalizadas. As Skills de documentos pré-construídas (PowerPoint, Excel, Word, PDF) não estão disponíveis no Claude Code, embora a [Claude API skill](/docs/en/agents-and-tools/agent-skills/claude-api-skill) de código aberto venha empacotada com ele. Veja a lista completa de [comandos e Skills integrados](https://code.claude.com/docs/en/commands) que acompanham o Claude Code.

**Skills personalizadas:** Crie Skills como diretórios com arquivos SKILL.md. O Claude as descobre e usa automaticamente.

Skills personalizadas no Claude Code são baseadas em sistema de arquivos e não exigem envios pela API: coloque-as em `~/.claude/skills/` (pessoal) ou `.claude/skills/` (projeto).

Para saber mais, veja [Usar Skills no Claude Code](https://code.claude.com/docs/en/skills).

### claude.ai

O [claude.ai](https://claude.ai) suporta tanto Skills do Agente pré-construídas quanto Skills personalizadas.

**Skills do Agente pré-construídas:** Essas Skills ficam ativas quando você cria documentos. O Claude as usa sem necessidade de configuração.

**Skills personalizadas:** Envie suas próprias Skills como arquivos zip em Configurações > Recursos. Disponível nos planos Pro, Max, Team e Enterprise com [execução de código habilitada](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude). Skills personalizadas são individuais para cada usuário. Elas não são compartilhadas em toda a organização e não podem ser gerenciadas centralmente por administradores.

Para saber mais sobre o uso de Skills no claude.ai, veja os seguintes recursos na Central de Ajuda do Claude:

* [O que são Skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
* [Usando Skills no Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
* [Como criar Skills personalizadas](https://support.claude.com/en/articles/12512198-creating-custom-skills)
* [Ensine ao Claude seu jeito de trabalhar usando Skills](https://support.claude.com/en/articles/12580051-teach-claude-your-way-of-working-using-skills)

## Estrutura de uma Skill

Toda Skill requer um arquivo `SKILL.md` com frontmatter YAML:

```markdown
---
name: your-skill-name
description: Brief description of what this Skill does and when to use it
---

# Your Skill Name

## Instructions
[Clear, step-by-step guidance for Claude to follow]

## Examples
[Concrete examples of using this Skill]
```

**Campos obrigatórios:** `name` e `description`

**Requisitos de campo:**

`name`:

* Máximo de 64 caracteres
* Deve conter apenas letras minúsculas, números e hífens
* Não pode conter tags XML
* Não pode conter palavras reservadas: "anthropic", "claude"

`description`:

* Deve ser não vazio
* Máximo de 1024 caracteres
* Não pode conter tags XML

A `description` deve incluir tanto o que a Skill faz quanto quando o Claude deve usá-la. Para orientações completas de criação, veja [Boas práticas para criar Skills](/docs/en/agents-and-tools/agent-skills/best-practices).

## Considerações de segurança

Use Skills apenas de fontes confiáveis: aquelas que você mesmo criou ou obteve da Anthropic. Skills dão ao Claude novas capacidades por meio de instruções e código, o que também significa que uma Skill maliciosa pode direcionar o Claude a invocar ferramentas ou executar código de formas que não correspondem ao propósito declarado da Skill.

<Warning>
  Se você precisar usar uma Skill de uma fonte não confiável ou desconhecida, tenha extremo cuidado e a audite minuciosamente antes de usá-la. Dependendo do acesso que o Claude tem ao executar a Skill, Skills maliciosas podem levar a vazamento de dados, acesso não autorizado ao sistema ou outros riscos de segurança.
</Warning>

**Principais considerações de segurança:**

* **Audite minuciosamente:** Revise todos os arquivos incluídos na Skill: SKILL.md, scripts, imagens e outros recursos. Procure por padrões incomuns, como chamadas de rede inesperadas, padrões de acesso a arquivos ou operações que não correspondem ao propósito declarado da Skill
* **Fontes externas são arriscadas:** Skills que buscam dados de URLs externas representam risco particular, já que o conteúdo obtido pode conter instruções maliciosas. Mesmo Skills confiáveis podem ser comprometidas se suas dependências externas mudarem com o tempo
* **Uso indevido de ferramentas:** Skills maliciosas podem invocar ferramentas (operações de arquivo, comandos bash, execução de código) de formas prejudiciais
* **Exposição de dados:** Skills com acesso a dados sensíveis podem ser projetadas para vazar informações para sistemas externos
* **Trate como instalação de software:** Tenha cuidado especial ao integrar Skills em sistemas de produção com acesso a dados sensíveis ou operações críticas

Para orientações de governança, avaliação e implantação em escala organizacional, veja [Skills para empresas](/docs/en/agents-and-tools/agent-skills/enterprise).

## Skills disponíveis

### Skills do Agente pré-construídas

As seguintes Skills do Agente pré-construídas estão disponíveis para uso imediato:

* **PowerPoint (pptx):** Crie apresentações, edite slides, analise conteúdo de apresentações
* **Excel (xlsx):** Crie planilhas, analise dados, gere relatórios com gráficos
* **Word (docx):** Crie documentos, edite conteúdo, formate texto
* **PDF (pdf):** Gere documentos e relatórios em PDF formatados

Essas Skills estão disponíveis na Claude API, na [Claude Platform on AWS](/docs/en/build-with-claude/claude-platform-on-aws), no [Microsoft Foundry](/docs/en/build-with-claude/claude-in-microsoft-foundry) e no claude.ai. Veja o [tutorial de início rápido](/docs/en/agents-and-tools/agent-skills/quickstart) para começar a usá-las na API.

### Skills de código aberto

A Anthropic também publica Skills de código aberto no [repositório de skills](https://github.com/anthropics/skills):

* **[Claude API skill](/docs/en/agents-and-tools/agent-skills/claude-api-skill):** Fornece ao Claude material de referência atualizado da API, documentação de SDK e boas práticas para oito linguagens de programação. Vem empacotada com o Claude Code e também disponível para instalação a partir do repositório de skills.

### Exemplos de Skills personalizadas

Para exemplos completos de Skills personalizadas, veja o [Skills cookbook](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction).

## Retenção de dados

As Skills do Agente não são cobertas por acordos de ZDR (retenção zero de dados). As definições de Skills e os dados de execução são retidos de acordo com a política padrão de retenção de dados da Anthropic.

Para elegibilidade de ZDR em todos os recursos, veja [API e retenção de dados](/docs/en/manage-claude/api-and-data-retention).

## Limitações e restrições

Claude Platform on AWS e Microsoft Foundry seguem as mesmas limitações que a Claude API nas subseções a seguir.

### Disponibilidade entre superfícies

**Skills personalizadas não são sincronizadas entre superfícies**. Skills enviadas para uma superfície não ficam automaticamente disponíveis em outras:

* Skills enviadas para o claude.ai devem ser enviadas separadamente para a API
* Skills enviadas pela API não ficam disponíveis no claude.ai
* Skills do Claude Code são baseadas em sistema de arquivos e separadas tanto do claude.ai quanto da API

Gerencie e envie Skills separadamente para cada superfície onde deseja usá-las.

### Escopo de compartilhamento

Skills têm modelos de compartilhamento diferentes dependendo de onde você as usa:

* **claude.ai:** Apenas individual por usuário. Cada membro da equipe deve enviar separadamente.
* **Claude API:** Em todo o workspace. Todos os membros do workspace podem acessar Skills enviadas.
* **Claude Code:** Pessoal (`~/.claude/skills/`) ou baseada em projeto (`.claude/skills/`). Também pode ser compartilhada por meio de Claude Code Plugins.

O claude.ai não suporta gerenciamento centralizado por administradores nem distribuição em toda a organização de Skills personalizadas.

### Restrições do ambiente de execução

O ambiente de execução exato disponível para sua Skill depende da superfície do produto onde você a usa.

* **claude.ai:**
  * **Acesso variável à rede:** Dependendo das configurações do usuário/administrador, as Skills podem ter acesso total, parcial ou nenhum acesso à rede. Para mais detalhes, veja o artigo de suporte [Create and Edit Files](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude#h_6b7e833898).

* **Claude API:**

  * **Sem acesso à rede:** Skills não podem fazer chamadas de API externas nem acessar a internet.
  * **Sem instalação de pacotes em tempo de execução:** Apenas pacotes pré-instalados estão disponíveis. Não é possível instalar novos pacotes durante a execução.
  * **Apenas dependências pré-configuradas:** Consulte a documentação da [ferramenta de execução de código](/docs/en/agents-and-tools/tool-use/code-execution-tool) para a lista de pacotes disponíveis.

* **Claude Code:**

  * **Acesso total à rede:** Skills têm o mesmo acesso à rede que qualquer outro programa no computador do usuário.
  * **Instalação global de pacotes desencorajada:** Skills devem instalar pacotes apenas localmente para evitar interferir no computador do usuário.

Planeje suas Skills para funcionar dentro dessas restrições.

## Próximos passos

<CardGroup cols={2}>
  <Card title="Comece a usar Agent Skills na API" icon="graduation-cap" href="/docs/en/agents-and-tools/agent-skills/quickstart">
    Aprenda a usar as Agent Skills para criar documentos com a Claude API em menos de 10 minutos.
  </Card>

  <Card title="Usando Agent Skills com a API" icon="code" href="/docs/en/build-with-claude/skills-guide">
    Aprenda a usar as Agent Skills para estender as capacidades do Claude por meio da API.
  </Card>

  <Card title="Usar Skills no Claude Code" icon="terminal" href="https://code.claude.com/docs/en/skills">
    Crie e gerencie Skills personalizadas no Claude Code.
  </Card>

  <Card title="Boas práticas para criar Skills" icon="lightbulb" href="/docs/en/agents-and-tools/agent-skills/best-practices">
    Aprenda a escrever Skills eficazes que o Claude possa descobrir e usar com sucesso.
  </Card>
</CardGroup>
