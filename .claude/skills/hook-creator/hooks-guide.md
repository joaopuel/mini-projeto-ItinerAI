> ## Índice da Documentação
> Busque o índice completo da documentação em: https://code.claude.com/docs/llms.txt
> Use este arquivo para descobrir todas as páginas disponíveis antes de explorar mais.

# Automatize ações com hooks

> Execute comandos de shell automaticamente quando o Claude Code edita arquivos, termina tarefas ou precisa de input. Formate código, envie notificações, valide comandos e reforce regras do projeto.

Hooks são comandos de shell definidos pelo usuário que são executados em pontos específicos do ciclo de vida do Claude Code. Eles fornecem controle determinístico sobre o comportamento do Claude Code, garantindo que certas ações sempre aconteçam em vez de depender do LLM escolher executá-las. Use hooks para reforçar regras do projeto, automatizar tarefas repetitivas e integrar o Claude Code com suas ferramentas existentes.

Para decisões que exigem julgamento em vez de regras determinísticas, você também pode usar [hooks baseados em prompt](#prompt-based-hooks) ou [hooks baseados em agente](#agent-based-hooks) que usam um modelo Claude para avaliar condições.

Para outras formas de estender o Claude Code, veja [skills](/en/skills) para dar ao Claude instruções e comandos executáveis adicionais, [subagents](/en/sub-agents) para executar tarefas em contextos isolados, e [plugins](/en/plugins) para empacotar extensões a serem compartilhadas entre projetos.

<Tip>
  Este guia cobre casos de uso comuns e como começar. Para os esquemas completos de eventos, formatos de entrada/saída JSON e recursos avançados como hooks assíncronos e hooks de ferramentas MCP, veja a [referência de Hooks](/en/hooks).
</Tip>

## Configure seu primeiro hook

Para criar um hook, adicione um bloco `hooks` a um [arquivo de configurações](#configure-hook-location). Este passo a passo cria um hook de notificação na área de trabalho, para que você seja avisado sempre que o Claude estiver esperando seu input, em vez de precisar ficar olhando o terminal.

<Steps>
  <Step title="Adicione o hook às suas configurações">
    Abra `~/.claude/settings.json` e adicione um hook `Notification`. Se o arquivo não existir, crie-o. O exemplo abaixo usa `osascript` para macOS; veja [Seja notificado quando o Claude precisar de input](#get-notified-when-claude-needs-input) para os comandos de Linux e Windows.

    ```json theme={null}
    {
      "hooks": {
        "Notification": [
          {
            "matcher": "",
            "hooks": [
              {
                "type": "command",
                "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
              }
            ]
          }
        ]
      }
    }
    ```

    Se seu arquivo de configurações já tiver uma chave `hooks`, adicione `Notification` como um item irmão das chaves de evento existentes, em vez de substituir o objeto inteiro. Cada nome de evento é uma chave dentro do objeto único `hooks`:

    ```json theme={null}
    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write",
            "hooks": [{ "type": "command", "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write" }]
          }
        ],
        "Notification": [
          {
            "matcher": "",
            "hooks": [{ "type": "command", "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'" }]
          }
        ]
      }
    }
    ```

    Você também pode pedir ao Claude para escrever o hook para você, descrevendo o que deseja na CLI.
  </Step>

  <Step title="Verifique a configuração">
    Digite `/hooks` para abrir o navegador de hooks. Você verá uma lista de todos os eventos de hook disponíveis, com uma contagem ao lado de cada evento que tem hooks configurados. Selecione `Notification` para confirmar que seu novo hook aparece na lista. Selecionar o hook mostra seus detalhes: o evento, o matcher, o tipo, o arquivo de origem e o comando.
  </Step>

  <Step title="Teste o hook">
    Pressione `Esc` para voltar à CLI. Peça ao Claude para fazer algo que exija permissão e depois mude para fora do terminal. Você deve receber uma notificação na área de trabalho.
  </Step>
</Steps>

<Tip>
  O menu `/hooks` é somente leitura. Para adicionar, modificar ou remover hooks, edite diretamente o JSON de configurações ou peça ao Claude para fazer a alteração.
</Tip>

## O que você pode automatizar

Hooks permitem executar código em pontos-chave do ciclo de vida do Claude Code: formatar arquivos após edições, bloquear comandos antes de serem executados, enviar notificações quando o Claude precisa de input, injetar contexto no início da sessão, e mais. Para a lista completa de eventos de hook, veja a [referência de Hooks](/en/hooks#hook-lifecycle).

Cada exemplo inclui um bloco de configuração pronto para uso que você adiciona a um [arquivo de configurações](#configure-hook-location).

Para um exemplo de produção de hooks que executam uma revisão separada por modelo e realimentam os achados de volta na sessão, veja [como o plugin `security-guidance` se integra ao Claude Code](/en/security-guidance#how-the-plugin-integrates-with-claude-code).

### Seja notificado quando o Claude precisar de input

Receba uma notificação na área de trabalho sempre que o Claude terminar de trabalhar e precisar do seu input, para que você possa alternar para outras tarefas sem ficar checando o terminal.

Esse hook usa o evento `Notification`, que dispara quando o Claude está esperando por input ou permissão. Cada aba abaixo usa o comando de notificação nativo da plataforma. Adicione isto a `~/.claude/settings.json`:

<Tabs>
  <Tab title="macOS">
    ```json theme={null}
    {
      "hooks": {
        "Notification": [
          {
            "matcher": "",
            "hooks": [
              {
                "type": "command",
                "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
              }
            ]
          }
        ]
      }
    }
    ```

    <Accordion title="Se nenhuma notificação aparecer">
      O `osascript` roteia notificações através do aplicativo integrado Script Editor. Se o Script Editor não tiver permissão de notificação, o comando falha silenciosamente, e o macOS não vai pedir para você concedê-la. Execute isto no Terminal uma vez para que o Script Editor apareça nas suas configurações de notificação:

      ```bash theme={null}
      osascript -e 'display notification "test"'
      ```

      Nada vai aparecer ainda. Abra **Ajustes do Sistema > Notificações**, encontre **Script Editor** na lista e ative **Permitir Notificações**. Execute o comando novamente para confirmar que a notificação de teste aparece.
    </Accordion>
  </Tab>

  <Tab title="Linux">
    ```json theme={null}
    {
      "hooks": {
        "Notification": [
          {
            "matcher": "",
            "hooks": [
              {
                "type": "command",
                "command": "notify-send 'Claude Code' 'Claude Code needs your attention'"
              }
            ]
          }
        ]
      }
    }
    ```
  </Tab>

  <Tab title="Windows (PowerShell)">
    ```json theme={null}
    {
      "hooks": {
        "Notification": [
          {
            "matcher": "",
            "hooks": [
              {
                "type": "command",
                "command": "powershell.exe -Command \"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('Claude Code needs your attention', 'Claude Code')\""
              }
            ]
          }
        ]
      }
    }
    ```
  </Tab>
</Tabs>

O `matcher` vazio dispara em todos os tipos de notificação. Para disparar apenas em eventos específicos, defina-o para um destes valores:

| Matcher                | Dispara quando                                                                                           |
| :---------------------- | :--------------------------------------------------------------------------------------------------------- |
| `permission_prompt`    | O Claude precisa que você aprove o uso de uma ferramenta                                                 |
| `idle_prompt`          | O Claude terminou e está esperando seu próximo prompt                                                     |
| `auth_success`         | A autenticação é concluída                                                                                |
| `elicitation_dialog`   | Um servidor MCP abre um formulário de elicitação                                                          |
| `elicitation_complete` | Um formulário de elicitação MCP é enviado ou descartado                                                   |
| `elicitation_response` | Uma resposta de elicitação MCP é enviada de volta ao servidor                                              |
| `agent_needs_input`    | Uma sessão em segundo plano começa a esperar por seu input. Dispara apenas enquanto a [visão de agente](/en/agent-view) estiver aberta |
| `agent_completed`      | Uma sessão em segundo plano termina ou falha. Dispara apenas enquanto a [visão de agente](/en/agent-view) estiver aberta |

Os matchers `agent_needs_input` e `agent_completed` exigem Claude Code v2.1.198 ou posterior.

Digite `/hooks` e selecione `Notification` para confirmar que o hook está registrado. Para o esquema completo do evento, veja a [referência de Notification](/en/hooks#notification).

### Formate código automaticamente após edições

Execute automaticamente o [Prettier](https://prettier.io/) em cada arquivo que o Claude editar, para que a formatação permaneça consistente sem intervenção manual.

Esse hook usa o evento `PostToolUse` com um matcher `Edit|Write`, então ele roda apenas depois de ferramentas de edição de arquivo. O comando extrai o caminho do arquivo editado com [`jq`](https://jqlang.org/) e o passa para o Prettier. Adicione isto a `.claude/settings.json` na raiz do seu projeto:

```json theme={null}
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
          }
        ]
      }
    ]
  }
}
```

No Claude Code v2.1.191 ou posterior você também pode escrever o matcher como `Edit,Write`, já que `|` e `,` são separadores de lista intercambiáveis para matchers de nome de ferramenta nessas versões.

<Note>
  Os exemplos em Bash nesta página usam `jq` para parsing de JSON. Instale-o com `brew install jq` no macOS, `apt-get install jq` no Debian e Ubuntu, ou veja [downloads do `jq`](https://jqlang.org/download/).
</Note>

### Bloqueie edições em arquivos protegidos

Impeça que o Claude modifique arquivos sensíveis como `.env`, `package-lock.json`, ou qualquer coisa dentro de `.git/`. O Claude recebe um feedback explicando por que a edição foi bloqueada, para que possa ajustar sua abordagem.

Este exemplo usa um arquivo de script separado que o hook chama. O script verifica o caminho do arquivo-alvo contra uma lista de padrões protegidos e sai com o código 2 para bloquear a edição.

<Steps>
  <Step title="Crie o script do hook">
    Salve isto em `.claude/hooks/protect-files.sh`:

    ```bash theme={null}
    #!/bin/bash
    # protect-files.sh

    INPUT=$(cat)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

    PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/")

    for pattern in "${PROTECTED_PATTERNS[@]}"; do
      if [[ "$FILE_PATH" == *"$pattern"* ]]; then
        echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
        exit 2
      fi
    done

    exit 0
    ```
  </Step>

  <Step title="Torne o script executável no macOS e no Linux">
    Scripts de hook precisam ser executáveis para que o Claude Code possa executá-los:

    ```bash theme={null}
    chmod +x .claude/hooks/protect-files.sh
    ```
  </Step>

  <Step title="Registre o hook">
    Adicione um hook `PreToolUse` a `.claude/settings.json` que executa o script antes de qualquer chamada às ferramentas `Edit` ou `Write`:

    ```json theme={null}
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "Edit|Write",
            "hooks": [
              {
                "type": "command",
                "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh"
              }
            ]
          }
        ]
      }
    }
    ```
  </Step>
</Steps>

### Reinjete contexto após a compactação

Quando a janela de contexto do Claude se enche, a compactação resume a conversa para liberar espaço. Isso pode fazer perder detalhes importantes. Use um hook `SessionStart` com um matcher `compact` para reinjetar contexto crítico após cada compactação.

Qualquer texto que seu comando escrever no stdout é adicionado ao contexto do Claude. Este exemplo lembra o Claude das convenções do projeto e do trabalho recente. Adicione isto a `.claude/settings.json` na raiz do seu projeto:

```json theme={null}
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: use Bun, not npm. Run bun test before committing. Current sprint: auth refactor.'"
          }
        ]
      }
    ]
  }
}
```

Você pode substituir o `echo` por qualquer comando que produza saída dinâmica, como `git log --oneline -5` para mostrar os commits recentes. Para injetar contexto em todo início de sessão, considere usar [CLAUDE.md](/en/memory) em vez disso. Para variáveis de ambiente, veja [`CLAUDE_ENV_FILE`](/en/hooks#persist-environment-variables) na referência.

### Audite mudanças de configuração

Rastreie quando arquivos de configurações ou de skills mudam durante uma sessão. O evento `ConfigChange` dispara quando um processo externo ou editor modifica um arquivo de configuração, para que você possa registrar mudanças para conformidade ou bloquear modificações não autorizadas.

Este exemplo anexa cada mudança a um log de auditoria. Adicione isto a `~/.claude/settings.json`:

```json theme={null}
{
  "hooks": {
    "ConfigChange": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "jq -c '{timestamp: now | todate, source: .source, file: .file_path}' >> ~/claude-config-audit.log"
          }
        ]
      }
    ]
  }
}
```

O matcher filtra pelo tipo de configuração: `user_settings`, `project_settings`, `local_settings`, `policy_settings`, ou `skills`. Para bloquear uma mudança de entrar em vigor, saia com o código 2 ou retorne `{"decision": "block"}`. Veja a [referência de ConfigChange](/en/hooks#configchange) para o esquema completo de entrada.

### Recarregue o ambiente quando o diretório ou arquivos mudarem

Alguns projetos definem variáveis de ambiente diferentes dependendo de em qual diretório você está. Ferramentas como o [direnv](https://direnv.net/) fazem isso automaticamente no seu shell, mas a ferramenta Bash do Claude não capta essas mudanças por conta própria.

Combinar um hook `SessionStart` com um hook `CwdChanged` resolve isso. O `SessionStart` carrega as variáveis do diretório em que você inicia, e o `CwdChanged` as recarrega toda vez que o Claude muda de diretório. Ambos escrevem em `CLAUDE_ENV_FILE`, que o Claude Code executa como um preâmbulo de script antes de cada comando Bash. Adicione isto a `~/.claude/settings.json`:

```json theme={null}
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "direnv export bash > \"$CLAUDE_ENV_FILE\""
          }
        ]
      }
    ],
    "CwdChanged": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "direnv export bash > \"$CLAUDE_ENV_FILE\""
          }
        ]
      }
    ]
  }
}
```

Execute `direnv allow` uma vez em cada diretório que tenha um `.envrc` para que o direnv tenha permissão de carregá-lo. Se você usa devbox ou nix em vez de direnv, o mesmo padrão funciona com `devbox shellenv` ou `devbox global shellenv` no lugar de `direnv export bash`.

Para reagir a arquivos específicos em vez de a cada mudança de diretório, use `FileChanged` com um `matcher` listando os nomes de arquivo a observar, separados por `|`. Ao montar a lista de observação, o Claude Code divide esse valor em nomes de arquivo literais em vez de avaliá-lo como regex. Veja [FileChanged](/en/hooks#filechanged) para saber como esse mesmo valor também filtra quais grupos de hook rodam quando um arquivo muda. Este exemplo observa `.envrc` e `.env` no diretório de trabalho:

```json theme={null}
{
  "hooks": {
    "FileChanged": [
      {
        "matcher": ".envrc|.env",
        "hooks": [
          {
            "type": "command",
            "command": "direnv export bash > \"$CLAUDE_ENV_FILE\""
          }
        ]
      }
    ]
  }
}
```

Veja as entradas de referência de [CwdChanged](/en/hooks#cwdchanged) e [FileChanged](/en/hooks#filechanged) para esquemas de entrada, saída de `watchPaths`, e detalhes de `CLAUDE_ENV_FILE`.

### Aprove automaticamente prompts de permissão específicos

Pule a caixa de diálogo de aprovação para chamadas de ferramenta que você sempre permite. Este exemplo aprova automaticamente `ExitPlanMode`, a ferramenta que o Claude chama quando termina de apresentar um plano e pede para prosseguir, para que você não seja questionado toda vez que um plano estiver pronto.

Diferente dos exemplos de código de saída acima, a aprovação automática exige que seu hook escreva uma decisão JSON no stdout. Um hook `PermissionRequest` dispara quando o Claude Code está prestes a mostrar uma caixa de diálogo de permissão, e retornar `"behavior": "allow"` responde a ela em seu nome.

O matcher restringe o hook apenas a `ExitPlanMode`, então nenhum outro prompt é afetado. Adicione isto a `~/.claude/settings.json`:

```json theme={null}
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"PermissionRequest\", \"decision\": {\"behavior\": \"allow\"}}}'"
          }
        ]
      }
    ]
  }
}
```

Quando o hook aprova, o Claude Code sai do modo de planejamento e restaura o modo de permissão que estava ativo antes de você entrar no modo de planejamento. A transcrição mostra "Allowed by PermissionRequest hook" onde a caixa de diálogo apareceria. O caminho do hook sempre mantém a conversa atual: ele não pode limpar o contexto e iniciar uma nova sessão de implementação como a caixa de diálogo pode.

Para definir um modo de permissão específico em vez disso, a saída do seu hook pode incluir um array `updatedPermissions` com uma entrada `setMode`. O valor de `mode` é qualquer modo de permissão como `default`, `acceptEdits`, ou `bypassPermissions`, e `destination: "session"` o aplica apenas para a sessão atual.

<Note>
  `bypassPermissions` só se aplica se a sessão foi iniciada com o modo bypass já disponível: `--dangerously-skip-permissions`, `--permission-mode bypassPermissions`, `--allow-dangerously-skip-permissions`, ou `permissions.defaultMode: "bypassPermissions"` nas configurações, e não desabilitado por [`permissions.disableBypassPermissionsMode`](/en/permissions#managed-settings). Ele nunca é persistido como `defaultMode`.
</Note>

Para mudar a sessão para `acceptEdits`, seu hook escreve este JSON no stdout:

```json theme={null}
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow",
      "updatedPermissions": [
        { "type": "setMode", "mode": "acceptEdits", "destination": "session" }
      ]
    }
  }
}
```

Mantenha o matcher o mais restrito possível. Combinar com `.*` ou deixar o matcher vazio aprovaria automaticamente todo prompt de permissão, incluindo escritas de arquivo e comandos de shell. Veja a [referência de PermissionRequest](/en/hooks#permissionrequest-decision-control) para o conjunto completo de campos de decisão.

## Como os hooks funcionam

Eventos de hook disparam em pontos específicos do ciclo de vida do Claude Code. Quando um evento dispara, todos os hooks correspondentes rodam em paralelo, e comandos de hook idênticos são automaticamente deduplicados. A tabela abaixo mostra cada evento e quando ele é acionado:

| Evento                 | Quando dispara                                                                                                                                          |
| :-------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SessionStart`        | Quando uma sessão começa ou é retomada                                                                                                                   |
| `Setup`               | Quando você inicia o Claude Code com `--init-only`, ou com `--init` ou `--maintenance` no modo `-p`. Para preparação única em CI ou scripts             |
| `UserPromptSubmit`    | Quando você envia um prompt, antes de o Claude processá-lo                                                                                               |
| `UserPromptExpansion` | Quando um comando digitado pelo usuário se expande em um prompt, antes de chegar ao Claude. Pode bloquear a expansão                                    |
| `PreToolUse`          | Antes da execução de uma chamada de ferramenta. Pode bloqueá-la                                                                                          |
| `PermissionRequest`   | Quando uma caixa de diálogo de permissão aparece                                                                                                         |
| `PermissionDenied`    | Quando uma chamada de ferramenta é negada pelo classificador do modo automático. Retorne `{retry: true}` para dizer ao modelo que ele pode tentar novamente a chamada negada |
| `PostToolUse`         | Depois que uma chamada de ferramenta é bem-sucedida                                                                                                      |
| `PostToolUseFailure`  | Depois que uma chamada de ferramenta falha                                                                                                               |
| `PostToolBatch`       | Depois que um lote completo de chamadas de ferramenta em paralelo é resolvido, antes da próxima chamada ao modelo                                       |
| `Notification`        | Quando o Claude Code envia uma notificação                                                                                                               |
| `MessageDisplay`      | Enquanto o texto da mensagem do assistente é exibido                                                                                                     |
| `SubagentStart`       | Quando um subagente é criado                                                                                                                             |
| `SubagentStop`        | Quando um subagente termina                                                                                                                              |
| `TaskCreated`         | Quando uma tarefa está sendo criada via `TaskCreate`                                                                                                     |
| `TaskCompleted`       | Quando uma tarefa está sendo marcada como concluída                                                                                                      |
| `Stop`                | Quando o Claude termina de responder                                                                                                                     |
| `StopFailure`         | Quando o turno termina devido a um erro de API. A saída e o código de saída são ignorados                                                                |
| `TeammateIdle`        | Quando um membro de uma [equipe de agentes](/en/agent-teams) está prestes a ficar ocioso                                                                 |
| `InstructionsLoaded`  | Quando um arquivo CLAUDE.md ou `.claude/rules/*.md` é carregado no contexto. Dispara no início da sessão e quando arquivos são carregados de forma preguiçosa durante uma sessão |
| `ConfigChange`        | Quando um arquivo de configuração muda durante uma sessão                                                                                                |
| `CwdChanged`          | Quando o diretório de trabalho muda, por exemplo quando o Claude executa um comando `cd`. Útil para gerenciamento reativo de ambiente com ferramentas como direnv |
| `FileChanged`         | Quando um arquivo observado muda no disco. O campo `matcher` especifica quais nomes de arquivo observar                                                  |
| `WorktreeCreate`      | Quando um worktree está sendo criado via `--worktree` ou `isolation: "worktree"`. Substitui o comportamento padrão do git                                |
| `WorktreeRemove`      | Quando um worktree está sendo removido, seja na saída da sessão ou quando um subagente termina                                                          |
| `PreCompact`          | Antes da compactação de contexto                                                                                                                         |
| `PostCompact`         | Depois que a compactação de contexto é concluída                                                                                                         |
| `Elicitation`         | Quando um servidor MCP solicita input do usuário durante uma chamada de ferramenta                                                                       |
| `ElicitationResult`   | Depois que um usuário responde a uma elicitação MCP, antes de a resposta ser enviada de volta ao servidor                                                |
| `SessionEnd`          | Quando uma sessão termina                                                                                                                                 |

Cada hook tem um `type` que determina como ele roda. A maioria dos hooks usa `"type": "command"`, que executa um comando de shell. Quatro outros tipos estão disponíveis:

* `"type": "http"`: envia (POST) os dados do evento para uma URL. Veja [Hooks HTTP](#http-hooks).
* `"type": "mcp_tool"`: chama uma ferramenta em um servidor MCP já conectado. Veja [Hooks de ferramenta MCP](/en/hooks#mcp-tool-hook-fields).
* `"type": "prompt"`: avaliação de LLM em turno único. Veja [Hooks baseados em prompt](#prompt-based-hooks).
* `"type": "agent"`: verificação multi-turno com acesso a ferramentas. Hooks de agente são experimentais e podem mudar. Veja [Hooks baseados em agente](#agent-based-hooks).

### Combine resultados de múltiplos hooks

Quando múltiplos hooks correspondem ao mesmo evento, o comando de cada hook roda até o final antes de o Claude Code mesclar os resultados. Um hook retornando `deny` não impede que hooks irmãos sejam executados. Não conte com o `deny` de um hook para suprimir efeitos colaterais em outro hook.

Depois que todos os hooks correspondentes terminam, o Claude Code combina suas saídas. Para decisões de permissão de `PreToolUse`, a resposta mais restritiva prevalece, na ordem `deny`, `defer`, `ask`, `allow`. O texto de `additionalContext` é mantido de cada hook e passado ao Claude junto.

O exemplo abaixo registra dois hooks `PreToolUse` em `Bash`. O primeiro anexa cada comando a um arquivo de log e sai com 0. O segundo executa um script que sai com 2 para negar quando o comando contém `rm -rf`:

```json theme={null}
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r .tool_input.command >> ~/.claude/bash.log"
          },
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/block-rm-rf.sh"
          }
        ]
      }
    ]
  }
}
```

Quando o Claude tenta executar `rm -rf /tmp/build`, ambos os hooks são executados em paralelo. O hook de log escreve o comando em `~/.claude/bash.log` e sai com 0, o que reporta nenhuma decisão. O hook de proteção sai com 2, o que nega a chamada de ferramenta. A negação prevalece, então o Claude Code bloqueia o comando e mostra ao Claude o stderr do hook de proteção. A entrada de log ainda é escrita porque o hook de log já havia rodado.

### Leia a entrada e retorne a saída

Hooks se comunicam com o Claude Code através de stdin, stdout, stderr e códigos de saída. Quando um evento dispara, o Claude Code passa dados específicos do evento como JSON para o stdin do seu script. Seu script lê esses dados, faz seu trabalho e diz ao Claude Code o que fazer em seguida via o código de saída.

#### Entrada do hook

Todo evento inclui campos comuns como `session_id` e `cwd`, mas cada tipo de evento adiciona dados diferentes. Por exemplo, quando o Claude executa um comando Bash, um hook `PreToolUse` recebe algo assim no stdin:

```json theme={null}
{
  "session_id": "abc123",          // ID único para esta sessão
  "cwd": "/Users/sarah/myproject", // diretório de trabalho quando o evento disparou
  "hook_event_name": "PreToolUse", // qual evento acionou este hook
  "tool_name": "Bash",             // a ferramenta que o Claude está prestes a usar
  "tool_input": {                  // os argumentos que o Claude passou para a ferramenta
    "command": "npm test"          // para Bash, este é o comando de shell
  }
}
```

Seu script pode fazer parsing desse JSON e agir sobre qualquer um desses campos. Hooks `UserPromptSubmit` recebem o texto de `prompt` em vez disso, hooks `SessionStart` recebem uma `source` de `startup`, `resume`, `clear`, ou `compact`, e assim por diante. Veja [Campos comuns de entrada](/en/hooks#common-input-fields) na referência para campos compartilhados, e a seção de cada evento para esquemas específicos de cada evento.

#### Saída do hook

Seu script diz ao Claude Code o que fazer em seguida escrevendo no stdout ou stderr e saindo com um código específico. O hook `PreToolUse` a seguir bloqueia um comando:

```bash theme={null}
#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

if echo "$COMMAND" | grep -q "drop table"; then
  echo "Blocked: dropping tables is not allowed" >&2  # stderr vira o feedback do Claude
  exit 2                                               # exit 2 = bloqueia a ação
fi

exit 0  # exit 0 = nenhuma decisão; o fluxo normal de permissão se aplica
```

O código de saída determina o que acontece a seguir:

* **Saída 0**: o hook reporta nenhuma objeção e a ação prossegue normalmente. Para um hook `PreToolUse` isso não aprova a chamada de ferramenta: o [fluxo normal de permissão](/en/permissions) ainda se aplica. Para hooks `UserPromptSubmit`, `UserPromptExpansion` e `SessionStart`, tudo que você escrever no stdout é adicionado ao contexto do Claude.
* **Saída 2**: a ação é bloqueada. Escreva um motivo no stderr, e o Claude o recebe como feedback para poder se ajustar. Alguns eventos não podem ser bloqueados: para `SessionStart`, `Setup`, `Notification` e outros, a saída 2 mostra o stderr ao usuário e a execução continua. Veja [comportamento do código de saída 2 por evento](/en/hooks#exit-code-2-behavior-per-event) para a lista completa.
* **Qualquer outro código de saída**: a ação prossegue. A transcrição mostra um aviso `<hook name> hook error` seguido pela primeira linha do stderr; o stderr completo vai para o [log de depuração](/en/hooks#debug-hooks).

#### Saída estruturada em JSON

Códigos de saída só permitem bloquear ou ficar em silêncio. Para mais controle, saia com 0 e imprima um objeto JSON no stdout em vez disso.

<Note>
  Use a saída 2 para bloquear com uma mensagem de stderr, ou a saída 0 com JSON para controle estruturado. Não misture os dois: o Claude Code ignora o JSON quando você sai com 2.
</Note>

Por exemplo, um hook `PreToolUse` pode negar uma chamada de ferramenta e dizer ao Claude por quê, ou escalar para o usuário aprovar:

```json theme={null}
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Use rg instead of grep for better performance"
  }
}
```

Com `"deny"`, o Claude Code cancela a chamada de ferramenta e realimenta `permissionDecisionReason` ao Claude. Estes valores de `permissionDecision` são específicos de `PreToolUse`:

* `"allow"`: pula o prompt interativo de permissão. Regras de negação e de pergunta, incluindo listas de negação gerenciadas pela empresa, ainda se aplicam, assim como prompts para ferramentas de conector que [sua organização configurou como `ask`](/en/mcp#organization-controls-on-connector-tools) e ferramentas MCP marcadas como [`requiresUserInteraction`](/en/mcp#require-approval-for-a-specific-tool)
* `"deny"`: cancela a chamada de ferramenta e envia o motivo ao Claude
* `"ask"`: mostra o prompt de permissão ao usuário normalmente

Um quarto valor, `"defer"`, está disponível no [modo não interativo](/en/headless) com a flag `-p`. Ele encerra o processo com a chamada de ferramenta preservada para que um wrapper do Agent SDK possa coletar o input e retomar. Veja [Adiar uma chamada de ferramenta para depois](/en/hooks#defer-a-tool-call-for-later) na referência.

Retornar `"allow"` pula o prompt interativo, mas não substitui as [regras de permissão](/en/permissions#manage-permissions). Se uma regra de negação corresponder à chamada de ferramenta, a chamada é bloqueada mesmo quando seu hook retorna `"allow"`. Se uma regra de pergunta corresponder, o usuário ainda é questionado, assim como ferramentas de conector [que sua organização configurou como `ask`](/en/mcp#organization-controls-on-connector-tools) e ferramentas MCP marcadas como [`requiresUserInteraction`](/en/mcp#require-approval-for-a-specific-tool). Isso significa que regras de negação de qualquer escopo de configurações, incluindo [configurações gerenciadas](/en/settings#settings-files), sempre têm precedência sobre aprovações de hooks.

Outros eventos usam padrões de decisão diferentes. Por exemplo, hooks `PostToolUse` e `Stop` usam um campo de nível superior `decision: "block"`, enquanto `PermissionRequest` usa `hookSpecificOutput.decision.behavior`. Veja a [tabela-resumo](/en/hooks#decision-control) na referência para um detalhamento completo por evento.

Para hooks `UserPromptSubmit`, use `hookSpecificOutput.additionalContext` em vez disso para injetar texto no contexto do Claude. Aninhe `additionalContext` dentro de `hookSpecificOutput`; se você colocá-lo no nível superior do JSON, o Claude Code o ignora silenciosamente. Por exemplo, esta saída adiciona o estado atual da branch a cada prompt:

```json theme={null}
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Current branch: release-42. Deploy freeze until Friday."
  }
}
```

Veja [controle de decisão de UserPromptSubmit](/en/hooks#userpromptsubmit-decision-control) para o formato completo de saída, incluindo bloquear prompts e definir o título da sessão.

Hooks com `type: "prompt"` lidam com a saída de forma diferente: veja [Hooks baseados em prompt](#prompt-based-hooks).

### Filtre hooks com matchers

Sem um matcher, um hook dispara em toda ocorrência do seu evento. Matchers permitem restringir isso. Por exemplo, se você quer rodar um formatador apenas depois de edições de arquivo, não depois de toda chamada de ferramenta, adicione um matcher ao seu hook `PostToolUse`:

```json theme={null}
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "prettier --write ..." }
        ]
      }
    ]
  }
}
```

O matcher `"Edit|Write"` dispara apenas quando o Claude usa a ferramenta `Edit` ou `Write`, não quando usa `Bash`, `Read`, ou qualquer outra ferramenta. {/* min-version: 2.1.191 */}No Claude Code v2.1.191 ou posterior, uma vírgula separa alternativas da mesma forma, então `"Edit, Write"` é equivalente. Veja [Padrões de matcher](/en/hooks#matcher-patterns) para saber como nomes simples e expressões regulares são avaliados.

<Note>
  O Claude também pode criar ou modificar arquivos executando comandos de shell através da ferramenta `Bash`. Se seu hook precisa ver toda mudança de arquivo, como para varredura de conformidade ou log de auditoria, adicione um hook [`Stop`](/en/hooks#stop) que varre a árvore de trabalho uma vez por turno. Para cobertura por chamada individual, também combine com `Bash` e faça seu script listar arquivos modificados e não rastreados com `git status --porcelain`.
</Note>

Cada tipo de evento combina com um campo específico:

| Evento                                                                                                                                                           | O que o matcher filtra                                                | Exemplos de valores de matcher                                                                                                                                                      |
| :-------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`                                                                      | nome da ferramenta                                                       | `Bash`, `Edit\|Write`, `mcp__.*`                                                                                                                                                    |
| `SessionStart`                                                                                                                                                  | como a sessão começou                                                    | `startup`, `resume`, `clear`, `compact`                                                                                                                                             |
| `Setup`                                                                                                                                                         | qual flag de CLI acionou a configuração                                  | `init`, `maintenance`                                                                                                                                                               |
| `SessionEnd`                                                                                                                                                    | por que a sessão terminou                                                | `clear`, `resume`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other`                                                                                            |
| `Notification`                                                                                                                                                  | tipo de notificação                                                      | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_complete`, `elicitation_response`, `agent_needs_input`, `agent_completed`                    |
| `SubagentStart`                                                                                                                                                 | tipo de agente                                                           | `general-purpose`, `Explore`, `Plan`, ou nomes de agentes personalizados                                                                                                            |
| `PreCompact`, `PostCompact`                                                                                                                                     | o que acionou a compactação                                              | `manual`, `auto`                                                                                                                                                                    |
| `SubagentStop`                                                                                                                                                  | tipo de agente                                                           | mesmos valores de `SubagentStart`                                                                                                                                                   |
| `ConfigChange`                                                                                                                                                  | origem da configuração                                                   | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills`                                                                                                  |
| `StopFailure`                                                                                                                                                   | tipo de erro                                                             | `rate_limit`, `overloaded`, `authentication_failed`, `oauth_org_not_allowed`, `billing_error`, `invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `unknown` |
| `InstructionsLoaded`                                                                                                                                            | motivo do carregamento                                                   | `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact`                                                                                                        |
| `Elicitation`                                                                                                                                                   | nome do servidor MCP                                                     | os nomes dos seus servidores MCP configurados                                                                                                                                       |
| `ElicitationResult`                                                                                                                                             | nome do servidor MCP                                                     | mesmos valores de `Elicitation`                                                                                                                                                     |
| `FileChanged`                                                                                                                                                   | nomes de arquivo literais a observar (veja [FileChanged](/en/hooks#filechanged)) | `.envrc\|.env`                                                                                                                                                                      |
| `UserPromptExpansion`                                                                                                                                           | nome do comando                                                          | os nomes das suas skills ou comandos                                                                                                                                                |
| `UserPromptSubmit`, `PostToolBatch`, `Stop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `CwdChanged`, `MessageDisplay` | sem suporte a matcher                                                    | sempre dispara em toda ocorrência                                                                                                                                                   |

As abas abaixo mostram mais alguns matchers em diferentes tipos de evento.

<Tabs>
  <Tab title="Registrar cada comando Bash">
    Combine apenas com chamadas de ferramenta `Bash` e registre cada comando em um arquivo. O evento `PostToolUse` dispara depois que o comando é concluído, então `tool_input.command` contém o que rodou. O hook recebe os dados do evento como JSON no stdin, e `jq -r '.tool_input.command'` extrai apenas a string do comando, que `>>` anexa ao arquivo de log:

    ```json theme={null}
    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Bash",
            "hooks": [
              {
                "type": "command",
                "command": "jq -r '.tool_input.command' >> ~/.claude/command-log.txt"
              }
            ]
          }
        ]
      }
    }
    ```
  </Tab>

  <Tab title="Combinar com ferramentas MCP">
    Ferramentas MCP usam uma convenção de nomenclatura diferente das ferramentas integradas: `mcp__<server>__<tool>`, onde `<server>` é o nome do servidor MCP e `<tool>` é a ferramenta que ele fornece. Por exemplo, `mcp__github__search_repositories` ou `mcp__filesystem__read_file`. Ferramentas de um [servidor empacotado em plugin](/en/mcp#plugin-provided-mcp-servers) usam um segmento de servidor com escopo, como `mcp__plugin_my-plugin_db__query`. Use um matcher de regex para atingir todas as ferramentas de um servidor específico, ou combine entre servidores com um padrão como `mcp__.*__write.*`. Veja [Combinar com ferramentas MCP](/en/hooks#match-mcp-tools) na referência para a lista completa de exemplos.

    O comando abaixo extrai o nome da ferramenta da entrada JSON do hook com `jq` e o escreve no stderr. Escrever no stderr mantém o stdout limpo para saída JSON e envia a mensagem para o [log de depuração](/en/hooks#debug-hooks):

    ```json theme={null}
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "mcp__github__.*",
            "hooks": [
              {
                "type": "command",
                "command": "echo \"GitHub tool called: $(jq -r '.tool_name')\" >&2"
              }
            ]
          }
        ]
      }
    }
    ```
  </Tab>

  <Tab title="Limpar ao final da sessão">
    O evento `SessionEnd` suporta matchers pelo motivo do término da sessão. Este hook dispara apenas no motivo `clear`, definido quando você executa `/clear`, não em saídas normais:

    ```json theme={null}
    {
      "hooks": {
        "SessionEnd": [
          {
            "matcher": "clear",
            "hooks": [
              {
                "type": "command",
                "command": "rm -f /tmp/claude-scratch-*.txt"
              }
            ]
          }
        ]
      }
    }
    ```
  </Tab>
</Tabs>

Para a sintaxe completa de matcher, veja a [referência de Hooks](/en/hooks#configuration).

#### Filtre por nome e argumentos da ferramenta com o campo `if`

O campo `if` usa a [sintaxe de regra de permissão](/en/permissions) para filtrar hooks pelo nome da ferramenta e argumentos juntos, então o processo do hook só é criado quando a chamada de ferramenta corresponde. Isso vai além de `matcher`, que filtra no nível do grupo apenas pelo nome da ferramenta.

Por exemplo, esta configuração roda um hook apenas quando o Claude usa comandos `git` em vez de todos os comandos Bash:

```json theme={null}
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(git *)",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-git-policy.sh"
          }
        ]
      }
    ]
  }
}
```

Se o comando do seu hook roda depende do formato do seu padrão `if` e do comando Bash que o Claude está invocando:

| Padrão `if`       | Comando Bash            | O hook roda? | Por quê                                                                                                 |
| :----------------- | :--------------------- | :--------- | :--------------------------------------------------------------------------------------------------- |
| `Bash(git *)`      | `git push`             | sim        | o nome do comando corresponde                                                                          |
| `Bash(git *)`      | `npm test && git push` | sim        | cada subcomando é verificado; `git push` corresponde                                                   |
| `Bash(git *)`      | `echo $(git log)`      | sim        | comandos dentro de `$()` e crases são verificados; `git log` corresponde                                |
| `Bash(git *)`      | `echo $(date)`         | não        | nenhum subcomando corresponde a `git *`                                                                 |
| `Bash(git push *)` | `echo $(date)`         | sim        | padrões que especificam mais do que o nome do comando rodam o hook de qualquer forma em `$()`, crases ou `$VAR` |

O filtro também falha de forma aberta, rodando seu hook independente do padrão, quando o comando Bash não pode ser interpretado. Como o filtro é best-effort, use o [sistema de permissões](/en/permissions) em vez de um hook para reforçar uma permissão ou negação definitiva.

O campo `if` aceita os mesmos padrões de regras de permissão: `"Bash(git *)"`, `"Edit(*.ts)"`, e assim por diante. Para combinar com múltiplos nomes de ferramenta, use handlers separados cada um com seu próprio valor de `if`, ou combine no nível de `matcher` onde a alternância por pipe é suportada.

`if` só funciona em eventos de ferramenta: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, e `PermissionDenied`. Adicioná-lo a qualquer outro evento impede que o hook rode.

### Configure a localização do hook

Onde você adiciona um hook determina seu escopo:

| Localização                                                   | Escopo                              | Compartilhável                                  |
| :--------------------------------------------------------- | :---------------------------------- | :----------------------------------------- |
| `~/.claude/settings.json`                                  | Todos os seus projetos              | Não, local à sua máquina                   |
| `.claude/settings.json`                                    | Um único projeto                    | Sim, pode ser commitado no repositório     |
| `.claude/settings.local.json`                              | Um único projeto                    | Não, ignorado pelo git quando o Claude Code o cria |
| Configurações de política gerenciadas                      | Em toda a organização               | Sim, controlado por administrador          |
| `hooks/hooks.json` de um [plugin](/en/plugins)              | Enquanto o plugin estiver habilitado | Sim, empacotado com o plugin                |
| Frontmatter de [skill](/en/skills) ou [agente](/en/sub-agents) | Enquanto a skill ou agente estiver ativo | Sim, definido no arquivo do componente     |

Execute [`/hooks`](/en/hooks#the-%2Fhooks-menu) no Claude Code para navegar por todos os hooks configurados, agrupados por evento.

Para desabilitar hooks, defina `"disableAllHooks": true` no seu arquivo de configurações. Hooks configurados em configurações gerenciadas continuam rodando a menos que `disableAllHooks` também seja definido lá.

Se você editar os arquivos de configurações diretamente enquanto o Claude Code está rodando, o observador de arquivos normalmente capta as mudanças de hook automaticamente.

## Hooks baseados em prompt

Para decisões que exigem julgamento em vez de regras determinísticas, use hooks `type: "prompt"`. Em vez de rodar um comando de shell, o Claude Code envia seu prompt e os dados de entrada do hook para um modelo Claude, Haiku por padrão, para tomar a decisão. Você pode especificar um modelo diferente com o campo `model` se precisar de mais capacidade.

O único trabalho do modelo é retornar uma decisão sim/não como JSON:

* `"ok": true`: a ação prossegue
* `"ok": false`: o que acontece depende do evento:
  * `Stop` e `SubagentStop`: o `reason` é realimentado ao Claude para que ele continue trabalhando
  * `PreToolUse`: a chamada de ferramenta é negada e o `reason` é retornado ao Claude como o erro da ferramenta, para que ele possa se ajustar e continuar
  * `PostToolUse`, `PostToolBatch`, `UserPromptSubmit`, e `UserPromptExpansion`: o turno termina e o `reason` aparece no chat como uma linha de aviso

Este exemplo usa um hook `Stop` para perguntar ao modelo se todas as tarefas solicitadas estão completas. Se o modelo retornar `"ok": false`, o Claude continua trabalhando e usa o `reason` como sua próxima instrução:

```json theme={null}
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains to be done\"}."
          }
        ]
      }
    ]
  }
}
```

Para as opções completas de configuração, veja [Hooks baseados em prompt](/en/hooks#prompt-based-hooks) na referência.

## Hooks baseados em agente

<Warning>
  Hooks de agente são experimentais. O comportamento e a configuração podem mudar em versões futuras. Para fluxos de produção, prefira [hooks de comando](/en/hooks#command-hook-fields).
</Warning>

Quando a verificação exige inspecionar arquivos ou rodar comandos, use hooks `type: "agent"`. Diferente dos hooks de prompt, que fazem uma única chamada de LLM, hooks de agente criam um subagente que pode ler arquivos, buscar código e usar outras ferramentas para verificar condições antes de retornar uma decisão.

Hooks de agente usam o mesmo formato de resposta `"ok"` / `"reason"` dos hooks de prompt, mas com um timeout padrão maior de 60 segundos e até 50 turnos de uso de ferramentas. O placeholder `$ARGUMENTS` no prompt é substituído pela entrada JSON do hook. Veja [campos de hook de prompt e agente](/en/hooks#prompt-and-agent-hook-fields).

Este exemplo verifica se os testes passam antes de permitir que o Claude pare:

```json theme={null}
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Verify that all unit tests pass. Run the test suite and check the results. $ARGUMENTS",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

Use hooks de prompt quando os dados de entrada do hook por si só forem suficientes para tomar uma decisão. Use hooks de agente quando você precisar verificar algo contra o estado real do código-fonte.

Para as opções completas de configuração, veja [Hooks baseados em agente](/en/hooks#agent-based-hooks) na referência.

## Hooks HTTP

Use hooks `type: "http"` para enviar (POST) os dados do evento a um endpoint HTTP em vez de rodar um comando de shell. O endpoint recebe o mesmo JSON que um hook de comando receberia no stdin, e retorna resultados através do corpo da resposta HTTP usando o mesmo formato JSON.

Hooks HTTP são úteis quando você quer que um servidor web, função em nuvem, ou serviço externo lide com a lógica do hook: por exemplo, um serviço de auditoria compartilhado que registra eventos de uso de ferramenta em toda uma equipe.

Este exemplo envia cada uso de ferramenta a um serviço de log local:

```json theme={null}
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "http",
            "url": "http://localhost:8080/hooks/tool-use",
            "headers": {
              "Authorization": "Bearer $MY_TOKEN"
            },
            "allowedEnvVars": ["MY_TOKEN"]
          }
        ]
      }
    ]
  }
}
```

O endpoint deve retornar um corpo de resposta JSON usando o mesmo [formato de saída](/en/hooks#json-output) dos hooks de comando. Para bloquear uma chamada de ferramenta, retorne uma resposta 2xx com os campos apropriados de `hookSpecificOutput`. Códigos de status HTTP sozinhos não podem bloquear ações.

Valores de cabeçalho suportam interpolação de variável de ambiente usando a sintaxe `$VAR_NAME` ou `${VAR_NAME}`. Apenas variáveis listadas no array `allowedEnvVars` são resolvidas; todas as outras referências `$VAR` permanecem vazias.

Para as opções completas de configuração e tratamento de resposta, veja [Hooks HTTP](/en/hooks#http-hook-fields) na referência.

## Limitações e solução de problemas

### Limitações

Tenha em mente estas restrições ao projetar hooks:

* Hooks de comando se comunicam apenas por stdout, stderr e códigos de saída. Eles não podem acionar comandos `/` ou chamadas de ferramenta. Texto retornado via `additionalContext` é injetado como um lembrete de sistema que o Claude lê como texto simples. Hooks HTTP se comunicam através do corpo da resposta em vez disso.
* Os timeouts de hook variam por tipo. Sobrescreva por hook com o campo `timeout` em segundos.
  * `command`, `http`, `mcp_tool`: 10 minutos. `UserPromptSubmit` reduz isso para 30 segundos, e `MessageDisplay` reduz para 10 segundos.
  * `prompt`: 30 segundos.
  * `agent`: 60 segundos.
* Hooks `PostToolUse` não podem desfazer ações, já que a ferramenta já foi executada.
* Hooks `PermissionRequest` não disparam no [modo não interativo](/en/headless) com a flag `-p`. Use hooks `PreToolUse` para decisões de permissão automatizadas.
* Hooks `Stop` disparam sempre que o Claude termina de responder, não apenas na conclusão de tarefas. Eles não disparam em interrupções do usuário. Erros de API disparam [StopFailure](/en/hooks#stopfailure) em vez disso.
* Quando múltiplos hooks `PreToolUse` retornam [`updatedInput`](/en/hooks#pretooluse) para reescrever os argumentos de uma ferramenta, o último a terminar prevalece. Como os hooks rodam em paralelo, a ordem é não determinística. Evite ter mais de um hook modificando o input da mesma ferramenta.

### Hooks e modos de permissão

Hooks `PreToolUse` disparam antes de qualquer verificação de modo de permissão, em todo [modo de permissão](/en/permission-modes), incluindo `dontAsk`. Um hook que retorna `permissionDecision: "deny"` bloqueia a ferramenta mesmo no modo `bypassPermissions` ou com `--dangerously-skip-permissions`. Isso permite reforçar uma política que os usuários não podem contornar mudando seu modo de permissão.

O inverso não é verdadeiro: um hook retornando `"allow"` não substitui regras de negação das configurações, e não pode suprimir o prompt para ferramentas de conector [que sua organização configurou como `ask`](/en/mcp#organization-controls-on-connector-tools) ou ferramentas MCP marcadas como [`requiresUserInteraction`](/en/mcp#require-approval-for-a-specific-tool). Hooks podem apertar restrições, mas não afrouxá-las além do que as regras de permissão permitem.

### O hook não dispara

O hook está configurado mas nunca executa.

* Execute `/hooks` e confirme que o hook aparece sob o evento correto
* Verifique se o padrão do matcher corresponde exatamente ao nome da ferramenta. Matchers diferenciam maiúsculas de minúsculas
* Verifique se você está acionando o tipo de evento correto: `PreToolUse` dispara antes da execução da ferramenta, `PostToolUse` dispara depois
* Se estiver usando hooks `PermissionRequest` no modo não interativo com a flag `-p`, mude para `PreToolUse` em vez disso

### Erro de hook na saída

Você vê uma mensagem como "PreToolUse hook error: ..." na transcrição.

* Seu script saiu com um código diferente de zero inesperadamente. Teste-o manualmente passando um JSON de exemplo:
  ```bash theme={null}
  echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | ./my-hook.sh
  echo $?  # Verifique o código de saída
  ```
* Se você vir "command not found", use caminhos absolutos ou `${CLAUDE_PROJECT_DIR}` para referenciar scripts. Para evitar completamente o escaping de shell, adicione `"args": []` para mudar para a [forma exec](/en/hooks#exec-form-and-shell-form), que cria o script diretamente sem um shell
* Se você vir "jq: command not found", instale `jq` ou use Python/Node.js para parsing de JSON
* Se o script não estiver rodando de forma alguma, torne-o executável: `chmod +x ./my-hook.sh`

### `/hooks` não mostra nenhum hook configurado

Você editou um arquivo de configurações, mas os hooks não aparecem no menu.

* Edições de arquivo normalmente são captadas automaticamente. Se não aparecerem depois de alguns segundos, o observador de arquivos pode ter perdido a mudança: reinicie sua sessão para forçar um recarregamento.
* Verifique se seu JSON é válido: vírgulas finais e comentários não são permitidos
* Confirme se o arquivo de configurações está na localização correta: `.claude/settings.json` para hooks de projeto, `~/.claude/settings.json` para hooks globais

### O hook Stop atinge o limite de bloqueio

O Claude continua trabalhando em vez de parar, então encerra o turno com um aviso de que o hook Stop bloqueou muitas vezes seguidas.

O Claude Code substitui um hook Stop depois que ele bloqueia oito vezes seguidas sem progresso. O script do seu hook precisa verificar se ele já acionou uma continuação. Faça o parsing do campo `stop_hook_active` da entrada JSON e saia antecipadamente se for `true`:

```bash theme={null}
#!/bin/bash
INPUT=$(cat)
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0  # Permite que o Claude pare
fi
# ... resto da lógica do seu hook
```

Se seu hook legitimamente precisa de mais de oito iterações para convergir, aumente o limite com [`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`](/en/env-vars).

### Falha na validação de JSON

O Claude Code mostra um erro de parsing de JSON mesmo que o script do seu hook produza um JSON válido.

Quando o Claude Code executa um hook de comando em forma de shell, um sem `args`, ele cria `sh -c` no macOS e Linux ou Git Bash no Windows por padrão. Esse shell é não interativo, mas o Git Bash e algumas configurações, como `BASH_ENV` apontando para `~/.bashrc`, ainda fazem source do seu perfil. Se esse perfil contiver declarações `echo` incondicionais, a saída é anexada antes do JSON do seu hook:

```text theme={null}
Shell ready on arm64
{"decision": "block", "reason": "Not allowed"}
```

O Claude Code tenta interpretar isso como JSON e falha. Para corrigir isso, envolva as declarações `echo` no seu perfil de shell para que rodem apenas em shells interativos:

```bash theme={null}
# Em ~/.zshrc ou ~/.bashrc
if [[ $- == *i* ]]; then
  echo "Shell ready"
fi
```

A variável `$-` contém as flags do shell, e `i` significa interativo. Hooks rodam em shells não interativos, então o echo é pulado.

### Técnicas de depuração

A visão de transcrição, alternada com `Ctrl+O`, mostra um resumo de uma linha para cada hook que disparou: sucesso é silencioso, erros de bloqueio mostram o stderr, e erros não bloqueantes mostram um aviso `<hook name> hook error` seguido pela primeira linha do stderr.

Para detalhes completos de execução, incluindo quais hooks corresponderam, seus códigos de saída, stdout e stderr, leia o log de depuração. Inicie o Claude Code com `claude --debug-file /tmp/claude.log` para escrever em um caminho conhecido, depois `tail -f /tmp/claude.log` em outro terminal. Se você iniciou sem essa flag, execute `/debug` no meio da sessão para habilitar o log e encontrar o caminho do arquivo.

## Saiba mais

* [Referência de Hooks](/en/hooks): esquemas completos de evento, formato de saída JSON, hooks assíncronos, e hooks de ferramentas MCP
* [Considerações de segurança](/en/hooks#security-considerations): revise antes de implantar hooks em ambientes compartilhados ou de produção
* [Exemplo de validador de comando Bash](https://github.com/anthropics/claude-code/blob/main/examples/hooks/bash_command_validator_example.py): implementação de referência completa
