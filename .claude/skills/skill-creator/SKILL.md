---
name: skill-creator
description: Creates new Agent Skills — scaffolds the SKILL.md file (with valid YAML frontmatter), supporting reference files, and scripts following Anthropic's Skill authoring format. Use when the user asks to create, scaffold, author, or set up a new Skill, or asks how Skills should be structured.
---

# Skill Creator

Cria novas Agent Skills seguindo o formato oficial descrito em [overview.md](overview.md) (referência completa incluída nesta Skill).

## Instructions

1. **Descubra o propósito da Skill.** Pergunte ao usuário (ou infira do pedido) o que a Skill deve fazer e em quais situações deve ser acionada. Isso vira a base da `description`.

2. **Escolha o `name`.** Deve:
   - ter no máximo 64 caracteres
   - conter apenas letras minúsculas, números e hífens
   - não conter tags XML
   - não conter as palavras reservadas "anthropic" ou "claude"

3. **Escreva a `description`.** Deve:
   - ser não vazia, com no máximo 1024 caracteres
   - não conter tags XML
   - descrever **o que** a Skill faz **e quando** o Claude deve usá-la (a description é o que o Claude compara com o pedido do usuário para decidir se aciona a Skill — veja Nível 1 em [overview.md](overview.md))

4. **Decida a estrutura em camadas** (progressive disclosure, ver [overview.md](overview.md)):
   - **Nível 1 (sempre carregado):** frontmatter YAML com `name` e `description`
   - **Nível 2 (carregado quando acionada):** corpo do SKILL.md com instruções, workflows e boas práticas — mantenha abaixo de ~5k tokens
   - **Nível 3 (carregado sob demanda):** arquivos de referência adicionais (`REFERENCE.md`, `FORMS.md`, etc.) e scripts executáveis (`scripts/*.py`, etc.), citados a partir do SKILL.md e só lidos/executados quando necessário

5. **Escolha onde a Skill vai morar** (ver seção "Onde Skills funcionam" em [overview.md](overview.md)):
   - Claude Code — pessoal: `~/.claude/skills/<name>/SKILL.md`
   - Claude Code — projeto: `.claude/skills/<name>/SKILL.md`
   - Para outras superfícies (API, claude.ai), consulte [overview.md](overview.md)

6. **Crie o diretório e os arquivos:**
   ```
   .claude/skills/<name>/
   ├── SKILL.md          # frontmatter + instruções
   ├── REFERENCE.md       # (opcional) detalhes extensos
   └── scripts/           # (opcional) código executável determinístico
   ```

7. **Escreva o SKILL.md** com esta forma mínima:
   ```markdown
   ---
   name: <nome-em-kebab-case>
   description: <o que faz + quando usar>
   ---

   # <Nome da Skill>

   ## Instructions
   [passos claros e sequenciais]

   ## Examples
   [exemplos concretos de uso]
   ```

8. **Valide antes de finalizar:**
   - `name` e `description` respeitam os limites e restrições acima
   - a description cobre "o quê" e "quando"
   - conteúdo de Nível 2 é instrucional, não uma enciclopédia (mova detalhes extensos para arquivos de Nível 3)
   - qualquer script bundlado é referenciado no corpo do SKILL.md, não colado inline

9. Após criar os arquivos, informe ao usuário o caminho da nova Skill e como testá-la.

## Segurança

Ao criar Skills, não inclua chamadas de rede não solicitadas nem instruções que peçam para o Claude agir fora do propósito declarado da Skill — veja "Security considerations" em [overview.md](overview.md).

## Reference

O arquivo [overview.md](overview.md), incluído nesta Skill, é a documentação completa da Anthropic sobre Agent Skills (arquitetura, requisitos de frontmatter, superfícies suportadas, limitações). Consulte-o para qualquer detalhe não coberto acima.
