---
name: instructions-md-manager
description: Creates or updates a project's CLAUDE.md instructions file — analyzes the codebase, merges findings with any existing CLAUDE.md, and keeps the result concise and well-structured following Anthropic's official conventions. Use when the user asks to create, init, update, or improve CLAUDE.md, or asks how CLAUDE.md files should be organized/structured/sized.
---

# Instructions.md Manager

Cria ou atualiza o arquivo `CLAUDE.md` de um projeto seguindo o formato e as boas práticas descritas em [claude-md-reference.md](claude-md-reference.md) (documentação oficial completa, incluída nesta Skill como referência).

## Instructions

1. **Descubra o estado atual.** Verifique se já existe `./CLAUDE.md` ou `./.claude/CLAUDE.md` no projeto (e `CLAUDE.local.md` ao lado). Se existir, leia o conteúdo por completo antes de tocar nele — nunca sobrescreva um arquivo existente sem primeiro entender o que já está documentado.

2. **Escolha o modo:**
   - **Criar do zero:** nenhum CLAUDE.md encontrado. Analise a base de código (estrutura de diretórios, `package.json`/`pyproject.toml`/etc., scripts de build/test/lint, README, `AGENTS.md`, `.cursorrules`, `.windsurfrules`) para extrair comandos e convenções reais.
   - **Atualizar:** já existe um CLAUDE.md. Não reescreva do zero — proponha adições/ajustes pontuais, preserve o que ainda é válido e remova apenas o que estiver desatualizado ou contradiz o código atual.

3. **Decida o que entra no arquivo**, seguindo a seção "Quando adicionar ao CLAUDE.md" da referência. Inclua apenas fatos que o Claude deve reter em toda sessão: comandos de build/test, convenções de nomenclatura, arquitetura, regras do tipo "sempre faça X". Não inclua:
   - conteúdo que o Claude consegue derivar sozinho lendo o código (listas triviais de dependências, layout óbvio de diretórios)
   - procedimentos de várias etapas específicos de uma tarefa (isso vira uma [skill](claude-md-reference.md))
   - preferências pessoais não compartilháveis pela equipe (isso vira `CLAUDE.local.md`)

4. **Escolha o local certo** (ver tabela "Escolha onde colocar os arquivos CLAUDE.md" na referência):
   - `./CLAUDE.md` ou `./.claude/CLAUDE.md` — instruções de projeto, compartilhadas via controle de versão
   - `./CLAUDE.local.md` — preferências pessoais específicas do projeto; garanta que está no `.gitignore`
   - Para monorepos, considere um CLAUDE.md por subdiretório relevante em vez de um único arquivo gigante na raiz

5. **Se já existir um `AGENTS.md`** no projeto, prefira importá-lo com `@AGENTS.md` no topo do CLAUDE.md e adicionar instruções específicas do Claude Code abaixo, em vez de duplicar conteúdo.

6. **Escreva/edite seguindo as regras de qualidade** da seção "Escreva instruções eficazes":
   - **Tamanho:** mire em menos de 200 linhas. Se estiver crescendo demais, mova tópicos para `.claude/rules/<topico>.md` (com `paths:` no frontmatter, se aplicável a arquivos específicos).
   - **Estrutura:** use headers e bullets em markdown, não parágrafos densos.
   - **Especificidade:** prefira instruções verificáveis ("Use indentação de 2 espaços", "Rode `npm test` antes de commitar") a instruções vagas ("formate adequadamente", "teste suas alterações").
   - **Consistência:** não introduza regras que contradigam instruções já presentes no mesmo arquivo ou em CLAUDE.md de diretórios ancestrais/aninhados.

7. **Valide antes de finalizar:**
   - contagem de linhas do arquivo final (< 200; se maior, avalie mover conteúdo para `.claude/rules/`)
   - nenhuma instrução conflitante com arquivos CLAUDE.md existentes na árvore
   - todo comando citado (build/test/lint) foi conferido contra o projeto real, não inventado
   - se o arquivo for versionado, nenhuma informação sensível (segredos, URLs internas de sandbox) foi incluída — isso pertence ao `CLAUDE.local.md`

8. Ao terminar, informe ao usuário onde o arquivo ficou e sugira rodar `/context` para confirmar que foi carregado na sessão.

## Reference

O arquivo [claude-md-reference.md](claude-md-reference.md), incluído nesta Skill, é a documentação oficial da Anthropic sobre arquivos CLAUDE.md e memória automática (onde colocar cada arquivo, como são carregados e concatenados, imports com `@caminho`, regras em `.claude/rules/`, `AGENTS.md`, troubleshooting). Consulte-o para qualquer detalhe não coberto acima.
