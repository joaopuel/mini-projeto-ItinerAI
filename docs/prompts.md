
---

## Criação do CLAUDE.md do projeto

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Configuração / Documentação

### Prompt original
```
#Instrução
Crie o arquivo CLAUDE.md com as especificações deste repositório

#Detalhes
1. Product: esse projeto tem como objetivo a criação de um agente chamado ItinerAi, capaz de criar intinerários de viagens. Todas as interações com o agente serão feitas via terminal, não haverá interface gráfica. Funcionalidades do agente:
* Pesquisar pontos turísticos do destino informado
* Pesquisar eventos/shows no destino informado dentro do período de férias fornecido
* Criar um intinerário da viagem, detalhando a vaigem dia-a-dia
* Gerar um arquivo .md com o itinerário criado
2. Tech: Deve ser utilizado Python 3.12.9, LangGrafh, pydantic, Groq modelo llama-3.1-8b-instant, Autenticação via variável de ambiente `GROQ_API_KEY`
3. Structure: A estrutura de pastas deve ser baseada na estrutura proposta pela documentação do LangGraph em application-structure
4. Adicione quaisquer informações a mais relevantes para a implementação deste agente e conclusão dos objetivos deste projeto, dentro das limitações técnicas definidas

#Regra
Adicione a seguinte regra no arquivo: Durante implementações de funcionalidades neste projeto, é OBRIGATÓRIO dar prioridade nas funcionalidades/ferramentes já disponibilizadas pelo harness VSCode. Caso seja preciso a execução de comandos no terminal, é fundamental e de caráter OBRIGATÓRIO, sem exeções, descrever exatamente o que o comando proposto faz, qual o objetivo do mesmo e solicitar ao usuário sua aprovação.
```

---

## Configuração inicial de comunicação com a LLM (Groq)

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Configuração / Implementação

### Prompt original
```
#Instrução
Com base nos objetivos do projeto, adicione as configurações iniciais para permitir a comunicação com a LLM

#Detalhes
1. Criar os arquivos .env.example, requirements, gitignore
2. Criar os arquivos de configurações para a plataforma GROQ para permitir a comunicação com o modelo proposto
3. Neste estágio inicial, apenas deve ser possível se comunicar com a LLM via terminal, sem nenhuma ferramenta ou orientação para a LLM
```

---

## Contexto padrão do agente (system prompt e saudação inicial)

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrução
Adicione contexto padrão do agente

#Detalhes
1. O contexto padrão deve ser enviado a LLM em toda sessão para ganrantir que a LLM entenda o papel e comportamento padrão que o angete de ter
2. O agente  tem como objetivo a criação de intinerários para viagens
3. O agente deve ter um tom amigável e descontraído
4. O agente deve iniciar a conversa sempre com "Sou ItinerAi, o seu melhor companheiro de viagem. Qual o seu próximo destino?"
5. Não adicione qualquer validação nesta parte, a LLM apenas deve ficar ciente do contexto inicial do agente, papel e objetivos
```

---

## Ferramenta de busca de pontos turísticos (Wikipédia)

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrição
Implementar a ferramenta (tool) de busca de pontos turísticos no destino informado

#Detalhes
1. Adicione um nó no langraph para a ferramenta
2. A ferramenta deve sempre primeira a busca em 'https://en.wikipedia.org/wiki/Tourism_in_<destiny>'
3. Caso não encontrado, realizar a busca padrão da wikipédia 'https://en.wikipedia.org/wiki/<search-target>'
4. Caso, nada relevante seja encontrado, informar ao usuário que não foi possível encontrar informações do destino na Web
5. Pode criar uma ou mais ferramentas para esta funcionalidade
```

---

## Ferramenta de busca de eventos e festivais (Wikipédia)

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrução
Implemente a ferramenta de busca de eventos e festivais no destino informado

#Detalhes
1. A ferramenta deve fazer uma busca pela wikipédia https://en.wikipedia.org/wiki/
2. A busca deve se concentrar em eventos e festivais traducionais da região
3. Como wikipédia apresenta um texto estático, pouco atualizado, é obrigatório informar na resposta para sempre pesquisar as datas e horários dos festivais nos sites oficiais do envento
4. Essas informações deve ser adicionadas como sugestões ao intininerário, já que não são precisas/atualizadas com os exatos dias dos eventos
5. Realize os ajustes necessáriso para adicionar esta funcionalidade
6. Ajuste o arquivo CLAUDE.md, caso necessário
```

---

## <Resumo-do-Prompt>

* Data: <data>
* Autor: joaopuel
* Tipo: <Tipo-de-Prompt-Utilizado>

### Prompt original
```
<Prompt-original>
```
