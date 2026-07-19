---
name: hook-creator
description: Creates and configures Claude Code hooks (command, http, prompt, or agent type) in settings.json — picks the right event, matcher, and JSON/exit-code output shape. Use when the user asks to create, configure, add, or debug a Claude Code hook, or to automate an action on a Claude Code lifecycle event (file edits, session start/end, tool use, stop, etc.).
---

# Hook Creator

Cria e configura hooks do Claude Code seguindo o formato oficial descrito em [hooks-guide.md](hooks-guide.md) (referência completa incluída nesta Skill).

## Instructions

1. **Descubra o objetivo do hook.** Pergunte ao usuário (ou infira do pedido) o que deve ser automatizado e em qual momento do ciclo de vida isso deve acontecer (ex.: formatar após edição, bloquear comando perigoso, notificar quando precisar de input, reinjetar contexto após compactação).

2. **Escolha o evento certo.** Consulte a tabela de eventos em [hooks-guide.md](hooks-guide.md) ("Como os hooks funcionam"). Eventos comuns:
   - `PreToolUse` — antes de uma chamada de ferramenta, pode bloquear
   - `PostToolUse` — depois que uma chamada de ferramenta é bem-sucedida
   - `SessionStart` / `SessionEnd` — início/fim de sessão
   - `Notification` — quando o Claude precisa de input
   - `Stop` / `SubagentStop` — quando o Claude (ou subagente) termina de responder
   - `UserPromptSubmit` — antes de processar o prompt do usuário
   - `ConfigChange`, `CwdChanged`, `FileChanged` — mudanças de configuração, diretório ou arquivo observado

3. **Escolha o tipo de hook:**
   - `"type": "command"` — roda um comando de shell (o mais comum)
   - `"type": "http"` — envia (POST) os dados do evento para uma URL
   - `"type": "mcp_tool"` — chama uma ferramenta de um servidor MCP já conectado
   - `"type": "prompt"` — avaliação de LLM em turno único (Haiku por padrão) para decisões que exigem julgamento, não regras determinísticas
   - `"type": "agent"` — subagente multi-turno com acesso a ferramentas para verificar o estado real do código (experimental)

4. **Defina o `matcher`** (quando aplicável) para restringir o hook. Veja a tabela "O que o matcher filtra" em [hooks-guide.md](hooks-guide.md) — cada evento filtra por um campo diferente (nome de ferramenta, motivo de início de sessão, etc.). Para filtrar por nome **e** argumentos de ferramenta juntos (ex.: só `git push`, não todo `Bash`), use o campo `if` com sintaxe de regra de permissão em vez de (ou além de) `matcher`.

5. **Escreva o comando/script.** Para hooks `command`:
   - leia o JSON de entrada do stdin (ex.: `INPUT=$(cat)`, extraia campos com `jq`)
   - decida a saída: código de saída 0 (sem objeção), código 2 (bloqueia, motivo no stderr), ou saída JSON estruturada em stdout (`hookSpecificOutput`) para controle fino (`allow`/`deny`/`ask`/`defer`, `additionalContext`, `updatedPermissions`, etc.)
   - nunca misture exit 2 com JSON — o Claude Code ignora o JSON quando o código de saída é 2
   - se o hook for um script em arquivo, torne-o executável (`chmod +x`) e referencie-o com `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<script>.sh`

6. **Escolha onde registrar o hook** (escopo):
   - `~/.claude/settings.json` — todos os projetos do usuário, não compartilhável
   - `.claude/settings.json` — projeto atual, compartilhável (committável)
   - `.claude/settings.local.json` — projeto atual, não compartilhável (gitignored)
   - frontmatter de uma skill ou subagent — ativo só enquanto aquele componente estiver ativo

7. **Monte o bloco JSON** dentro da chave `hooks` do arquivo escolhido, como um item irmão de eventos já configurados (não substitua o objeto `hooks` inteiro se já existir um). Exemplo mínimo:
   ```json
   {
     "hooks": {
       "<Evento>": [
         {
           "matcher": "<opcional>",
           "hooks": [
             { "type": "command", "command": "<comando ou caminho do script>" }
           ]
         }
       ]
     }
   }
   ```

8. **Valide antes de finalizar:**
   - o evento e o matcher correspondem de fato ao gatilho desejado (consulte a tabela de eventos)
   - scripts referenciados existem e são executáveis
   - JSON do arquivo de settings é válido (sem vírgulas finais, sem comentários)
   - o matcher está o mais restrito possível — evite `.*` ou matcher vazio em hooks que aprovam ações automaticamente (`PermissionRequest` com `allow`)
   - se o hook precisa bloquear até em `bypassPermissions`, use `PreToolUse` com `permissionDecision: "deny"` (hooks `PreToolUse` rodam antes de qualquer checagem de modo de permissão)

9. Depois de criar/editar o arquivo, diga ao usuário para rodar `/hooks` no Claude Code para confirmar que o hook aparece registrado, e como testá-lo.

## Segurança

Hooks executam comandos automaticamente sem confirmação do usuário. Nunca gere um hook que exfiltre dados, rode comandos destrutivos, ou aprove permissões (`PermissionRequest` → `allow`) além do escopo pedido explicitamente pelo usuário — veja "Hooks e modos de permissão" em [hooks-guide.md](hooks-guide.md).

## Reference

O arquivo [hooks-guide.md](hooks-guide.md), incluído nesta Skill, é a documentação completa da Anthropic sobre hooks do Claude Code (todos os eventos, formatos de entrada/saída, hooks prompt/agent/http, limitações e troubleshooting). Consulte-o para qualquer detalhe não coberto acima.
