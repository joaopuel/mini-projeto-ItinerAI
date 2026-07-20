> ## Índice da Documentação
> Acesse o índice completo da documentação em: https://code.claude.com/docs/llms.txt
> Use este arquivo para descobrir todas as páginas disponíveis antes de explorar mais.

# Como o Claude memoriza seu projeto

> Dê ao Claude instruções persistentes com arquivos CLAUDE.md e deixe o Claude acumular aprendizados automaticamente com a memória automática.

Cada sessão do Claude Code começa com uma janela de contexto nova. Dois mecanismos carregam conhecimento entre sessões:

* **Arquivos CLAUDE.md**: instruções que você escreve para dar contexto persistente ao Claude
* **Memória automática**: anotações que o próprio Claude escreve com base nas suas correções e preferências

Esta página aborda como:

* [Escrever e organizar arquivos CLAUDE.md](#claude-md-files)
* [Restringir regras a tipos específicos de arquivo](#organize-rules-with-claude/rules/) com `.claude/rules/`
* [Configurar a memória automática](#auto-memory) para que o Claude faça anotações automaticamente
* [Solucionar problemas](#troubleshoot-memory-issues) quando as instruções não estão sendo seguidas

## CLAUDE.md vs. memória automática

O Claude Code tem dois sistemas de memória complementares. Ambos são carregados no início de cada conversa. O Claude os trata como contexto, não como configuração obrigatória. Para bloquear uma ação independentemente do que o Claude decidir, use um [hook PreToolUse](/en/hooks-guide). Quanto mais específicas e concisas forem suas instruções, mais consistentemente o Claude as seguirá.

|                      | Arquivos CLAUDE.md                                   | Memória automática                                                      |
| :------------------- | :------------------------------------------------ | :--------------------------------------------------------------- |
| **Quem escreve**    | Você                                               | Claude                                                           |
| **O que contém** | Instruções e regras                            | Aprendizados e padrões                                           |
| **Escopo**            | Projeto, usuário ou organização                             | Por repositório, compartilhado entre worktrees                          |
| **Carregado em**      | Toda sessão                                     | Toda sessão (primeiras 200 linhas ou 25KB)                       |
| **Uso**          | Padrões de código, fluxos de trabalho, arquitetura do projeto | Comandos de build, insights de depuração, preferências que o Claude descobre |

Use arquivos CLAUDE.md quando quiser orientar o comportamento do Claude. A memória automática permite que o Claude aprenda com suas correções sem esforço manual.

Subagentes também podem manter sua própria memória automática. Veja a [configuração de subagentes](/en/sub-agents#enable-persistent-memory) para mais detalhes.

## Arquivos CLAUDE.md

Os arquivos CLAUDE.md são arquivos markdown que dão ao Claude instruções persistentes para um projeto, seu fluxo de trabalho pessoal ou toda a sua organização. Você escreve esses arquivos em texto simples; o Claude os lê no início de cada sessão.

### Quando adicionar ao CLAUDE.md

Trate o CLAUDE.md como o lugar onde você anota aquilo que, de outra forma, teria que reexplicar. Adicione a ele quando:

* O Claude comete o mesmo erro pela segunda vez
* Uma revisão de código identifica algo que o Claude deveria saber sobre esta base de código
* Você digita no chat a mesma correção ou esclarecimento que digitou na sessão anterior
* Um novo integrante da equipe precisaria do mesmo contexto para ser produtivo

Mantenha nele apenas fatos que o Claude deve reter em toda sessão: comandos de build, convenções, estrutura do projeto, regras do tipo "sempre faça X". Se um item for um procedimento de várias etapas ou só for relevante para uma parte específica da base de código, mova-o para uma [skill](/en/skills) ou uma [regra restrita a um caminho](#organize-rules-with-claude/rules/). A [visão geral da extensão](/en/features-overview#build-your-setup-over-time) explica quando usar cada mecanismo.

### Escolha onde colocar os arquivos CLAUDE.md

Os arquivos CLAUDE.md podem existir em vários locais, cada um com um escopo diferente. A tabela abaixo os lista na ordem de carregamento, do escopo mais amplo ao mais específico, de modo que uma instrução de projeto aparece no contexto depois de uma instrução de usuário.

| Escopo                    | Local                                                                                                                                                                | Finalidade                                                    | Exemplos de uso                                                    | Compartilhado com                     |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------- |
| **Política gerenciada**       | • macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`<br />• Linux e WSL: `/etc/claude-code/CLAUDE.md`<br />• Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | Instruções válidas para toda a organização, gerenciadas por TI/DevOps        | Padrões de código da empresa, políticas de segurança, requisitos de conformidade | Todos os usuários da organização       |
| **Instruções de usuário**    | `~/.claude/CLAUDE.md`                                                                                                                                                   | Preferências pessoais para todos os projetos                      | Preferências de estilo de código, atalhos de ferramentas pessoais                 | Somente você (todos os projetos)         |
| **Instruções de projeto** | `./CLAUDE.md` ou `./.claude/CLAUDE.md`                                                                                                                                  | Instruções compartilhadas pela equipe para o projeto                   | Arquitetura do projeto, padrões de código, fluxos de trabalho comuns             | Membros da equipe via controle de versão |
| **Instruções locais**   | `./CLAUDE.local.md`                                                                                                                                                     | Preferências pessoais específicas do projeto; adicione ao `.gitignore` | Suas URLs de sandbox, dados de teste preferidos                 | Somente você (projeto atual)      |

Os arquivos CLAUDE.md e CLAUDE.local.md na hierarquia de diretórios acima do diretório de trabalho são carregados por completo na inicialização. Arquivos em subdiretórios são carregados sob demanda quando o Claude lê arquivos nesses diretórios. Veja [Como os arquivos CLAUDE.md são carregados](#how-claude-md-files-load) para a ordem completa de resolução.

Para projetos grandes, você pode dividir as instruções em arquivos por tópico usando [regras de projeto](#organize-rules-with-claude/rules/). As regras permitem restringir instruções a tipos de arquivo ou subdiretórios específicos.

### Configure um CLAUDE.md de projeto

Um CLAUDE.md de projeto pode ser armazenado em `./CLAUDE.md` ou `./.claude/CLAUDE.md`. Crie esse arquivo e adicione instruções que se apliquem a qualquer pessoa trabalhando no projeto: comandos de build e teste, padrões de código, decisões de arquitetura, convenções de nomenclatura e fluxos de trabalho comuns. Essas instruções são compartilhadas com sua equipe via controle de versão, então priorize padrões em nível de projeto em vez de preferências pessoais.

<Tip>
  Execute `/init` para gerar automaticamente um CLAUDE.md inicial. O Claude analisa sua base de código e cria um arquivo com comandos de build, instruções de teste e convenções do projeto que descobrir. Se já existir um CLAUDE.md, o `/init` sugere melhorias em vez de sobrescrevê-lo. A partir daí, refine com instruções que o Claude não conseguiria descobrir sozinho.

  Defina `CLAUDE_CODE_NEW_INIT=1` para habilitar um fluxo interativo em várias etapas. O `/init` pergunta quais artefatos configurar: arquivos CLAUDE.md, skills e hooks. Em seguida, explora sua base de código com um subagente, preenche lacunas por meio de perguntas de acompanhamento e apresenta uma proposta revisável antes de gravar qualquer arquivo.
</Tip>

### Escreva instruções eficazes

Os arquivos CLAUDE.md são carregados na janela de contexto no início de cada sessão, consumindo tokens junto com sua conversa. A [visualização da janela de contexto](/en/context-window) mostra onde o CLAUDE.md é carregado em relação ao restante do contexto de inicialização. Como são contexto, e não configuração obrigatória, a forma como você escreve as instruções afeta a confiabilidade com que o Claude as segue. Instruções específicas, concisas e bem estruturadas funcionam melhor.

**Tamanho**: mire em menos de 200 linhas por arquivo CLAUDE.md. Arquivos mais longos consomem mais contexto e reduzem a aderência. Se suas instruções estiverem crescendo muito, use [regras restritas a caminhos](#path-specific-rules) para que as instruções só sejam carregadas quando o Claude trabalhar com arquivos correspondentes. Você também pode dividir o conteúdo em [imports](#import-additional-files) para fins de organização, embora os arquivos importados ainda sejam carregados e entrem na janela de contexto na inicialização.

**Estrutura**: use cabeçalhos e marcadores em markdown para agrupar instruções relacionadas. O Claude examina a estrutura da mesma forma que os leitores: seções organizadas são mais fáceis de seguir do que parágrafos densos.

**Especificidade**: escreva instruções concretas o suficiente para serem verificáveis. Por exemplo:

* "Use indentação de 2 espaços" em vez de "Formate o código adequadamente"
* "Execute `npm test` antes de commitar" em vez de "Teste suas alterações"
* "Os handlers de API ficam em `src/api/handlers/`" em vez de "Mantenha os arquivos organizados"

**Consistência**: se duas regras se contradizem, o Claude pode escolher uma arbitrariamente. Revise periodicamente seus arquivos CLAUDE.md, os arquivos CLAUDE.md aninhados em subdiretórios e as [`.claude/rules/`](#organize-rules-with-claude/rules/) para remover instruções desatualizadas ou conflitantes. Em monorepos, use [`claudeMdExcludes`](#exclude-specific-claude-md-files) para ignorar arquivos CLAUDE.md de outras equipes que não sejam relevantes para o seu trabalho.

### Importe arquivos adicionais

Os arquivos CLAUDE.md podem importar arquivos adicionais usando a sintaxe `@caminho/para/import`. Os arquivos importados são expandidos e carregados no contexto na inicialização, junto com o CLAUDE.md que os referencia.

São permitidos caminhos relativos e absolutos. Caminhos relativos são resolvidos em relação ao arquivo que contém o import, não ao diretório de trabalho. Arquivos importados podem importar outros arquivos recursivamente, com profundidade máxima de quatro níveis.

A análise de imports ignora spans de código e blocos de código com marcação (fenced) em Markdown. Para mencionar um caminho no seu CLAUDE.md sem importá-lo, coloque-o entre crases: escrever `` `@README` `` mantém o texto literal, enquanto `@README` fora de crases importa o arquivo.

Para trazer um README, um package.json e um guia de fluxo de trabalho, referencie-os com a sintaxe `@` em qualquer lugar do seu CLAUDE.md:

```text theme={null}
Veja @README para uma visão geral do projeto e @package.json para os comandos npm disponíveis neste projeto.

# Instruções Adicionais
- fluxo de trabalho do git @docs/git-instructions.md
```

Para preferências privadas específicas do projeto que não devem ser versionadas, crie um `CLAUDE.local.md` na raiz do projeto. Ele é carregado junto com o `CLAUDE.md` e tratado da mesma forma. Adicione `CLAUDE.local.md` ao seu `.gitignore` para que não seja commitado; executar `/init` e escolher a opção pessoal faz isso por você.

Se você trabalha em várias worktrees git do mesmo repositório, um `CLAUDE.local.md` ignorado pelo git só existe na worktree em que foi criado. Para compartilhar instruções pessoais entre worktrees, importe um arquivo do seu diretório home:

```text theme={null}
# Preferências Individuais
- @~/.claude/my-project-instructions.md
```

<Warning>
  Na primeira vez que o Claude Code encontrar imports externos em um projeto, ele exibirá uma caixa de diálogo de aprovação listando os arquivos. Se você recusar, os imports permanecem desabilitados e a caixa de diálogo não aparece novamente.
</Warning>

Para uma abordagem mais estruturada de organizar instruções, veja [`.claude/rules/`](#organize-rules-with-claude/rules/).

### AGENTS.md

O Claude Code lê `CLAUDE.md`, não `AGENTS.md`. Se seu repositório já usa `AGENTS.md` para outros agentes de codificação, crie um `CLAUDE.md` que o importe, para que ambas as ferramentas leiam as mesmas instruções sem duplicação. Você também pode adicionar instruções específicas do Claude abaixo do import. O Claude carrega o arquivo importado no início da sessão e depois acrescenta o restante:

```markdown CLAUDE.md theme={null}
@AGENTS.md

## Claude Code

Use o modo de planejamento para alterações em `src/billing/`.
```

Um symlink também funciona se você não precisar adicionar conteúdo específico do Claude:

```bash theme={null}
ln -s AGENTS.md CLAUDE.md
```

No Windows, criar um symlink requer privilégios de Administrador ou o Modo de Desenvolvedor, então use o import `@AGENTS.md`.

Executar [`/init`](/en/commands) em um repositório que já tem um `AGENTS.md` lê esse arquivo e incorpora as partes relevantes no CLAUDE.md gerado. Ele também lê configurações de outras ferramentas, como `.cursorrules`, `.devin/rules/` e `.windsurfrules`.

### Como os arquivos CLAUDE.md são carregados

O Claude Code lê os arquivos CLAUDE.md percorrendo a árvore de diretórios a partir do seu diretório de trabalho atual, verificando cada diretório no caminho em busca de arquivos `CLAUDE.md` e `CLAUDE.local.md`. Isso significa que, se você executar o Claude Code em `foo/bar/`, ele carrega instruções de `foo/bar/CLAUDE.md`, `foo/CLAUDE.md` e quaisquer arquivos `CLAUDE.local.md` ao lado deles.

Todos os arquivos descobertos são concatenados no contexto em vez de se sobreporem uns aos outros. Ao longo da árvore de diretórios, o conteúdo é ordenado da raiz do sistema de arquivos até o seu diretório de trabalho. No exemplo de `foo/bar/`, `foo/CLAUDE.md` aparece no contexto antes de `foo/bar/CLAUDE.md`, de modo que as instruções mais próximas de onde você iniciou o Claude são lidas por último. Dentro de cada diretório, `CLAUDE.local.md` é anexado após `CLAUDE.md`, para que suas anotações pessoais sejam a última coisa que o Claude lê naquele nível.

O Claude também descobre arquivos `CLAUDE.md` e `CLAUDE.local.md` em subdiretórios abaixo do seu diretório de trabalho atual. Em vez de serem carregados na inicialização, eles são incluídos quando o Claude lê arquivos nesses subdiretórios.

Se você trabalha em um monorepo grande onde arquivos CLAUDE.md de outras equipes são detectados, use [`claudeMdExcludes`](#exclude-specific-claude-md-files) para ignorá-los. Para o layout completo dos arquivos CLAUDE.md e regras na raiz e por diretório, veja [Monorepos e repositórios grandes](/en/large-codebases).

Comentários HTML em nível de bloco (`<!-- notas do mantenedor -->`) em arquivos CLAUDE.md são removidos antes que o conteúdo seja injetado no contexto do Claude. Use-os para deixar anotações para mantenedores humanos sem gastar tokens de contexto com elas. Comentários dentro de blocos de código são preservados. Ao abrir um arquivo CLAUDE.md diretamente com a ferramenta Read, os comentários permanecem visíveis.

#### Carregando a partir de diretórios adicionais

A flag `--add-dir` dá ao Claude acesso a diretórios adicionais fora do seu diretório de trabalho principal. Por padrão, os arquivos CLAUDE.md desses diretórios não são carregados.

Para também carregar arquivos de memória de diretórios adicionais, defina a variável de ambiente `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD`:

```bash theme={null}
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ../shared-config
```

Isso carrega `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md` e `CLAUDE.local.md` do diretório adicional. `CLAUDE.local.md` é ignorado se você excluir `local` de [`--setting-sources`](/en/cli-reference).

### Organize regras com `.claude/rules/`

Para projetos maiores, você pode organizar instruções em vários arquivos usando o diretório `.claude/rules/`. Isso mantém as instruções modulares e mais fáceis de manter para equipes. As regras também podem ser [restritas a caminhos de arquivo específicos](#path-specific-rules), de modo que só sejam carregadas no contexto quando o Claude trabalhar com arquivos correspondentes, reduzindo ruído e economizando espaço de contexto.

<Note>
  As regras são carregadas no contexto em toda sessão ou quando arquivos correspondentes são abertos. Para instruções específicas de tarefas que não precisam estar sempre no contexto, use [skills](/en/skills), que só são carregadas quando você as invoca ou quando o Claude determina que são relevantes para o seu prompt.
</Note>

#### Configure regras

Coloque arquivos markdown no diretório `.claude/rules/` do seu projeto. Cada arquivo deve cobrir um tópico, com um nome de arquivo descritivo como `testing.md` ou `api-design.md`. Todos os arquivos `.md` são descobertos recursivamente, então você pode organizar as regras em subdiretórios como `frontend/` ou `backend/`:

```text theme={null}
seu-projeto/
├── .claude/
│   ├── CLAUDE.md           # Instruções principais do projeto
│   └── rules/
│       ├── code-style.md   # Diretrizes de estilo de código
│       ├── testing.md      # Convenções de teste
│       └── security.md     # Requisitos de segurança
```

Regras sem [frontmatter `paths`](#path-specific-rules) são carregadas na inicialização com a mesma prioridade de `.claude/CLAUDE.md`.

Regras de projeto são ignoradas se você excluir `project` de [`--setting-sources`](/en/cli-reference). {/* min-version: 2.1.211 */}Antes da v2.1.211, regras carregadas sob demanda, incluindo regras restritas a caminhos e regras em diretórios `.claude/rules/` aninhados, eram carregadas mesmo quando `project` era excluído.

#### Regras restritas a caminhos

As regras podem ser restritas a arquivos específicos usando frontmatter YAML com o campo `paths`. Essas regras condicionais só se aplicam quando o Claude está trabalhando com arquivos que correspondem aos padrões especificados.

```markdown theme={null}
---
paths:
  - "src/api/**/*.ts"
---

# Regras de Desenvolvimento de API

- Todos os endpoints de API devem incluir validação de entrada
- Use o formato padrão de resposta de erro
- Inclua comentários de documentação OpenAPI
```

Regras sem um campo `paths` são carregadas incondicionalmente e se aplicam a todos os arquivos. Regras restritas a caminhos são acionadas quando o Claude lê arquivos que correspondem ao padrão, não a cada uso de ferramenta. {/* min-version: 2.1.198 */}A partir da v2.1.198, a correspondência também funciona quando o Claude acessa um arquivo por meio de um caminho com symlink para o diretório do projeto, por exemplo em um checkout com symlink.

Use padrões glob no campo `paths` para corresponder arquivos por extensão, diretório ou qualquer combinação:

| Padrão                | Corresponde a                                  |
| ---------------------- | ---------------------------------------- |
| `**/*.ts`              | Todos os arquivos TypeScript em qualquer diretório    |
| `src/**/*`             | Todos os arquivos sob o diretório `src/`         |
| `*.md`                 | Arquivos markdown na raiz do projeto       |
| `src/components/*.tsx` | Componentes React em um diretório específico |

Você pode especificar vários padrões e usar expansão de chaves para corresponder a várias extensões em um único padrão:

```markdown theme={null}
---
paths:
  - "src/**/*.{ts,tsx}"
  - "lib/**/*.ts"
  - "tests/**/*.test.ts"
---
```

A sintaxe glob trata `[` como o início de uma expressão entre colchetes, como `[abc]`. Um padrão com um `[` que não pode ser interpretado como uma expressão entre colchetes, como `photos [2024/**`, é inválido: não corresponde a nada, e os demais padrões da regra continuam funcionando. Para corresponder a um `[` literal em um nome de arquivo, escape-o como `photos \[2024/**`. {/* min-version: 2.1.207 */}Antes da v2.1.207, um padrão inválido fazia a ferramenta Read falhar para todo arquivo em que a regra fosse avaliada, em vez de simplesmente não corresponder a nada.

#### Compartilhe regras entre projetos com symlinks

O diretório `.claude/rules/` suporta symlinks, então você pode manter um conjunto compartilhado de regras e vinculá-las em vários projetos. Symlinks são resolvidos e carregados normalmente, e symlinks circulares são detectados e tratados adequadamente.

Este exemplo vincula tanto um diretório compartilhado quanto um arquivo individual:

```bash theme={null}
ln -s ~/shared-claude-rules .claude/rules/shared
ln -s ~/company-standards/security.md .claude/rules/security.md
```

#### Regras em nível de usuário

Regras pessoais em `~/.claude/rules/` se aplicam a todos os projetos na sua máquina. Use-as para preferências que não são específicas de um projeto:

```text theme={null}
~/.claude/rules/
├── preferences.md    # Suas preferências pessoais de codificação
└── workflows.md      # Seus fluxos de trabalho preferidos
```

Regras em nível de usuário são carregadas antes das regras de projeto, dando prioridade maior às regras de projeto.

### Gerencie o CLAUDE.md para equipes grandes

Para organizações que implantam o Claude Code em várias equipes, você pode centralizar instruções e controlar quais arquivos CLAUDE.md são carregados.

#### Implante um CLAUDE.md em toda a organização

Organizações podem implantar um CLAUDE.md gerenciado centralmente que se aplica a todos os usuários em uma máquina. Esse arquivo não pode ser excluído por configurações individuais.

<Steps>
  <Step title="Crie o arquivo no local da política gerenciada">
    * macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`
    * Linux e WSL: `/etc/claude-code/CLAUDE.md`
    * Windows: `C:\Program Files\ClaudeCode\CLAUDE.md`
  </Step>

  <Step title="Implante com seu sistema de gerenciamento de configuração">
    Use MDM, Group Policy, Ansible ou ferramentas similares para distribuir o arquivo entre as máquinas dos desenvolvedores. Veja [configurações gerenciadas](/en/permissions#managed-settings) para outras opções de configuração em toda a organização.
  </Step>
</Steps>

A chave `claudeMd` permite colocar o conteúdo do CLAUDE.md gerenciado diretamente dentro de `managed-settings.json`, em vez de implantar um arquivo separado.

**Escopo**: toda sessão do Claude Code na máquina, em todo repositório. Para orientações específicas de repositório, faça commit de um CLAUDE.md de projeto.

**Precedência**: igual a um arquivo CLAUDE.md gerenciado. Carregado antes do CLAUDE.md de usuário e de projeto.

**Onde é respeitado**: apenas em configurações gerenciadas e de política. Definir `claudeMd` em configurações de usuário, projeto ou locais não tem efeito.

O exemplo abaixo adiciona instruções comportamentais diretamente em um arquivo de configurações gerenciadas:

```json theme={null}
{
  "claudeMd": "Sempre execute `make lint` antes de commitar.\nNunca faça push diretamente para main."
}
```

Um CLAUDE.md gerenciado e [configurações gerenciadas](/en/settings#settings-files) servem a propósitos diferentes. Use configurações para aplicação técnica obrigatória e CLAUDE.md para orientação comportamental:

| Aspecto                                        | Configure em                                              |
| :--------------------------------------------- | :---------------------------------------------------------- |
| Bloquear ferramentas, comandos ou caminhos de arquivo específicos  | Configurações gerenciadas: `permissions.deny`                      |
| Aplicar isolamento de sandbox                      | Configurações gerenciadas: `sandbox.enabled`                       |
| Variáveis de ambiente e roteamento de provedor de API | Configurações gerenciadas: `env`                                   |
| Método de autenticação e bloqueio de organização | Configurações gerenciadas: `forceLoginMethod`, `forceLoginOrgUUID` |
| Estilo de código e diretrizes de qualidade              | CLAUDE.md gerenciado                                         |
| Tratamento de dados e lembretes de conformidade         | CLAUDE.md gerenciado                                         |
| Instruções comportamentais para o Claude             | CLAUDE.md gerenciado                                         |

Regras de configuração são aplicadas pelo cliente independentemente do que o Claude decidir fazer. As instruções do CLAUDE.md orientam o comportamento do Claude, mas não são uma camada de aplicação obrigatória.

#### Exclua arquivos CLAUDE.md específicos

Em monorepos grandes, arquivos CLAUDE.md de diretórios ancestrais podem conter instruções que não são relevantes para o seu trabalho. A configuração `claudeMdExcludes` permite ignorar arquivos específicos por caminho ou padrão glob.

Este exemplo exclui um CLAUDE.md de nível superior e um diretório de regras de uma pasta pai. Adicione-o a `.claude/settings.local.json` para que a exclusão permaneça local à sua máquina:

```json theme={null}
{
  "claudeMdExcludes": [
    "**/monorepo/CLAUDE.md",
    "/home/user/monorepo/other-team/.claude/rules/**"
  ]
}
```

Os padrões são comparados com caminhos de arquivo absolutos usando sintaxe glob. Você pode configurar `claudeMdExcludes` em qualquer [camada de configurações](/en/settings#settings-files): usuário, projeto, local ou política gerenciada. Os arrays são mesclados entre as camadas.

Arquivos CLAUDE.md de política gerenciada não podem ser excluídos. Isso garante que as instruções em nível de organização sempre se apliquem, independentemente das configurações individuais.

## Memória automática

A memória automática permite que o Claude acumule conhecimento entre sessões sem que você escreva nada. O Claude salva anotações para si mesmo enquanto trabalha: comandos de build, insights de depuração, notas de arquitetura, preferências de estilo de código e hábitos de fluxo de trabalho. O Claude não salva algo em toda sessão. Ele decide o que vale a pena lembrar com base na utilidade da informação em uma conversa futura.

### Habilite ou desabilite a memória automática

A memória automática vem habilitada por padrão. Para alterná-la, abra `/memory` em uma sessão e use o alternador de memória automática, ou defina `autoMemoryEnabled` nas configurações do seu projeto:

```json theme={null}
{
  "autoMemoryEnabled": false
}
```

Para desabilitar a memória automática via variável de ambiente, defina `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.

### Local de armazenamento

Cada projeto recebe seu próprio diretório de memória em `~/.claude/projects/<project>/memory/`. O caminho `<project>` é derivado do repositório git, de modo que todas as worktrees e subdiretórios dentro do mesmo repositório compartilham um único diretório de memória automática. Fora de um repositório git, é usada a raiz do projeto.

Para armazenar a memória automática em outro local, defina `autoMemoryDirectory` no seu `settings.json`. Ele é lido de qualquer [escopo de configurações](/en/settings#settings-precedence): usuário, projeto, local, política ou `--settings`.

```json theme={null}
{
  "autoMemoryDirectory": "~/my-custom-memory-dir"
}
```

O valor deve ser um caminho absoluto ou começar com `~/`. Quando definido no `.claude/settings.json` ou `.claude/settings.local.json` de um projeto, o valor só é respeitado após você aceitar a caixa de diálogo de confiança do workspace para essa pasta, o mesmo controle que rege os hooks.

O diretório contém um ponto de entrada `MEMORY.md` e arquivos de tópico opcionais:

```text theme={null}
~/.claude/projects/<project>/memory/
├── MEMORY.md          # Índice conciso, carregado em toda sessão
├── debugging.md       # Notas detalhadas sobre padrões de depuração
├── api-conventions.md # Decisões de design de API
└── ...                # Quaisquer outros arquivos de tópico que o Claude criar
```

O `MEMORY.md` funciona como um índice do diretório de memória. O Claude lê e escreve arquivos nesse diretório ao longo da sua sessão, usando o `MEMORY.md` para acompanhar o que está armazenado e onde.

A memória automática é local à máquina. Todas as worktrees e subdiretórios dentro do mesmo repositório git compartilham um único diretório de memória automática. Os arquivos não são compartilhados entre máquinas ou ambientes de nuvem.

### Como funciona

As primeiras 200 linhas do `MEMORY.md`, ou os primeiros 25KB, o que vier primeiro, são carregados no início de cada conversa. O conteúdo além desse limite não é carregado no início da sessão. O Claude mantém o `MEMORY.md` conciso movendo notas detalhadas para arquivos de tópico separados.

{/* min-version: 2.1.210 */}Depois que o Claude escreve no `MEMORY.md`, o Claude Code mede o arquivo em relação aos limites de leitura de 200 linhas e 25KB. Se o arquivo estiver perto de um limite, o Claude Code lembra o Claude de encurtá-lo: manter uma linha por item, mover detalhes para arquivos de tópico e mesclar ou remover itens obsoletos. Se o arquivo ultrapassar um limite, a escrita ainda é bem-sucedida, mas o Claude Code retorna um [erro instruindo o Claude a reescrever o índice](/en/errors#memory-index-is-over-its-read-limit), porque tudo além do limite é descartado no próximo carregamento.

{/* min-version: 2.1.211 */}A verificação mede apenas o conteúdo que é carregado: o frontmatter YAML e os comentários HTML em nível de bloco são removidos antes de o índice ser carregado, então não contam para os limites. Antes da v2.1.211, o Claude Code media o arquivo bruto, e frontmatter ou comentários podiam disparar o erro mesmo quando o conteúdo carregado cabia no limite.

Esse limite se aplica apenas ao `MEMORY.md`. Os arquivos CLAUDE.md são carregados por completo independentemente do tamanho, embora arquivos mais curtos produzam melhor aderência.

Arquivos de tópico como `debugging.md` ou `patterns.md` não são carregados na inicialização. O Claude os lê sob demanda usando suas ferramentas padrão de arquivo quando precisa da informação.

A memória automática da conversa principal não é carregada em [subagentes](/en/sub-agents#what-loads-at-startup); a exceção é um [fork](/en/sub-agents#fork-the-current-conversation), que herda a conversa principal e o prompt do sistema. A memória automática própria de um subagente, habilitada com o campo `memory` do subagente, é um diretório separado.

O Claude lê e escreve arquivos de memória durante sua sessão. Quando você vê "Writing memory" ou "Recalled memory" na interface do Claude Code, o Claude está ativamente atualizando ou lendo de `~/.claude/projects/<project>/memory/`.

### Audite e edite sua memória

Os arquivos de memória automática são markdown simples que você pode editar ou excluir a qualquer momento. Execute [`/memory`](#view-and-edit-with-%2Fmemory) para navegar e abrir arquivos de memória de dentro de uma sessão.

## Visualize e edite com `/memory`

O comando `/memory` lista seus arquivos CLAUDE.md, CLAUDE.local.md e outros locais de arquivos de memória entre escopos de usuário e projeto, permite alternar a memória automática entre ligada e desligada, e oferece uma opção para abrir a pasta de memória automática. Selecione qualquer arquivo para abri-lo no seu editor. Para verificar quais arquivos realmente foram carregados na sessão atual, execute `/context`.

Quando você pede ao Claude para lembrar de algo, como "sempre use pnpm, não npm" ou "lembre que os testes de API exigem uma instância local do Redis", o Claude salva isso na memória automática. Para adicionar instruções ao CLAUDE.md em vez disso, peça diretamente ao Claude, como "adicione isso ao CLAUDE.md", ou edite o arquivo você mesmo via `/memory`.

## Solução de problemas de memória

Estes são os problemas mais comuns com CLAUDE.md e memória automática, junto com as etapas para depurá-los.

### O Claude não está seguindo meu CLAUDE.md

O conteúdo do CLAUDE.md é entregue como uma mensagem de usuário após o prompt do sistema, não como parte do próprio prompt do sistema. O Claude o lê e tenta segui-lo, mas não há garantia de conformidade estrita, especialmente para instruções vagas ou conflitantes.

Para depurar:

* Execute `/context` para verificar se seus arquivos CLAUDE.md e CLAUDE.local.md foram carregados. Se um arquivo estiver ausente no detalhamento, o Claude não consegue vê-lo. Use `/memory` para abrir e editar os arquivos.
* Verifique se o CLAUDE.md relevante está em um local que é carregado na sua sessão (veja [Escolha onde colocar os arquivos CLAUDE.md](#choose-where-to-put-claude-md-files)).
* Torne as instruções mais específicas. "Use indentação de 2 espaços" funciona melhor do que "formate o código adequadamente".
* Procure instruções conflitantes entre arquivos CLAUDE.md. Se dois arquivos derem orientações diferentes para o mesmo comportamento, o Claude pode escolher uma arbitrariamente.

Se a instrução for algo que precisa rodar em um ponto específico, como antes de cada commit ou depois de cada edição de arquivo, escreva-a como um [hook](/en/hooks-guide). Os hooks são executados como comandos de shell em eventos fixos do ciclo de vida e se aplicam independentemente do que o Claude decidir fazer.

Para instruções que você quer no nível do prompt do sistema, use [`--append-system-prompt`](/en/cli-reference#system-prompt-flags). Isso precisa ser passado em toda invocação, então é mais adequado para scripts e automação do que para uso interativo.

<Tip>
  Use o [hook `InstructionsLoaded`](/en/hooks#instructionsloaded) para registrar exatamente quais arquivos de instrução são carregados, quando são carregados e por quê. Isso é útil para depurar regras restritas a caminhos ou arquivos carregados sob demanda em subdiretórios.
</Tip>

### Não sei o que a memória automática salvou

Execute `/memory` e selecione a pasta de memória automática para navegar pelo que o Claude salvou. Tudo é markdown simples que você pode ler, editar ou excluir.

### Meu CLAUDE.md está muito grande

Arquivos com mais de 200 linhas consomem mais contexto e podem reduzir a aderência. Use [regras restritas a caminhos](#path-specific-rules) para carregar instruções apenas quando o Claude trabalhar com arquivos correspondentes, ou remova conteúdo que não seja necessário em toda sessão. Dividir em [imports `@path`](#import-additional-files) ajuda na organização, mas não reduz o contexto, já que os arquivos importados são carregados na inicialização.

{/* min-version: 2.1.206 */}A verificação do [`/doctor`](/en/commands#all-commands) propõe cortes para um CLAUDE.md versionado: ela remove conteúdo que o Claude consegue derivar da base de código, como layouts de diretório, listas de dependências e visões gerais de arquitetura, e mantém armadilhas, justificativas e convenções que diferem dos padrões da ferramenta. A verificação de corte requer o Claude Code v2.1.206 ou posterior.

### As instruções parecem perdidas após o `/compact`

O CLAUDE.md da raiz do projeto sobrevive à compactação: após o `/compact`, o Claude o relê do disco e o reinjeta na sessão. Arquivos CLAUDE.md aninhados em subdiretórios não são reinjetados automaticamente; eles são recarregados na próxima vez que o Claude ler um arquivo naquele subdiretório.

Se uma instrução desapareceu após a compactação, ela foi fornecida apenas na conversa ou está em um CLAUDE.md aninhado que ainda não foi recarregado. Adicione instruções fornecidas apenas na conversa ao CLAUDE.md para que persistam. Veja [O que sobrevive à compactação](/en/context-window#what-survives-compaction) para o detalhamento completo.

Veja [Escreva instruções eficazes](#write-effective-instructions) para orientações sobre tamanho, estrutura e especificidade.

## Recursos relacionados

* [Depure sua configuração](/en/debug-your-config): diagnostique por que o CLAUDE.md ou as configurações não estão surtindo efeito
* [Skills](/en/skills): empacote fluxos de trabalho repetíveis que são carregados sob demanda
* [Configurações](/en/settings): configure o comportamento do Claude Code com arquivos de configurações
* [Memória de subagentes](/en/sub-agents#enable-persistent-memory): permita que subagentes mantenham sua própria memória automática
