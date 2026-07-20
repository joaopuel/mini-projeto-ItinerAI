
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

## Correção de erro: argumento `period` inesperado na busca de eventos

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Correção de bug

### Prompt original
```
#Instrução
Ocorreu este erro durante a execução do agente. Investigue a causa e realize os ajustes necessários.
Descreva sua linha de pensamento durante os ajustes.

#Erro
ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem. Qual o seu próximo destino?
(digite 'sair' para encerrar)
Você: Existe algum festival ou evento interessante na alemanha em outubro?
Traceback (most recent call last):
  File "C:\git\mini-projeto-ItinerAI\main.py", line 38, in <module>
    main()
  File "C:\git\mini-projeto-ItinerAI\main.py", line 32, in main
    result = graph.invoke(state)
             ^^^^^^^^^^^^^^^^^^^
  File "C:\git\mini-projeto-ItinerAI\.venv\Lib\site-packages\langgraph\pregel\main.py", line 3913, in invoke
    for chunk in self.stream(
                 ^^^^^^^^^^^^
  File "C:\git\mini-projeto-ItinerAI\.venv\Lib\site-packages\langgraph\pregel\main.py", line 2967, in stream
    for _ in runner.tick(
             ^^^^^^^^^^^^
  File "C:\git\mini-projeto-ItinerAI\.venv\Lib\site-packages\langgraph\pregel\_runner.py", line 207, in tick
    run_with_retry(
  File "C:\git\mini-projeto-ItinerAI\.venv\Lib\site-packages\langgraph\pregel\_retry.py", line 617, in run_with_retry
    return task.proc.invoke(task.input, config)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\git\mini-projeto-ItinerAI\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 684, in invoke
    input = context.run(step.invoke, input, config, **kwargs)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\git\mini-projeto-ItinerAI\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 426, in invoke
    ret = self.func(*args, **kwargs)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\git\mini-projeto-ItinerAI\itinerai_agent\utils\nodes.py", line 35, in call_tools
    result = tool_fn(**call["args"])
             ^^^^^^^^^^^^^^^^^^^^^^^
TypeError: search_events_and_festivals() got an unexpected keyword argument 'period'
During task with name 'call_tools' and id '16763708-c53f-e3ac-3c2c-35c70aef9fa6'
```

---

## Ferramenta de construção de itinerário

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrução
Implementar ferramente de construção de itinerário

#Detalhes
1. Ajuste as ferramentas de busca de pontos turísticos e eventos para sempre retornar o local exato ou provável da atração
2. A nova ferramenta de contrução de intinerário deve receber as informações obtidas pelas buscas e o período da viagem
3. A ferramente deve dividir as atrações encontradas pelo total de dias diposponíveis
4. Deve ser sugerido no máximo 3 atrações por período do dia (dia, tarde e noite)
5. Caso encontradas poucas atrações pela duração da viagem, pode inserir mensagem do tipo: "Aproveite cada detalhe, há tempo suficiente para aproveitar as atrações nas suas férias) e, em últimos casos, sugerir repetir lugares para aproveitar ainda mais detalhes dos mesmos
6. As atrações devem ser agrupadas por proximodade visando a melhor eficiência da viagem
```

---

## Correção de erro: tool_use_failed na extração de pontos turísticos

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Correção de bug

### Prompt original
```
Investigue e ajuste este erro:

(.venv) PS C:\git\mini-projeto-ItinerAI> python main.py
ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem. Qual o seu próximo destino?
(digite 'sair' para encerrar)
Você: Vou para Lisboa por 3 dias
Traceback (most recent call last):
  ...
  File "C:\git\mini-projeto-ItinerAI\itinerai_agent\utils\tools.py", line 116, in _extract_attractions
    result = structured_llm.invoke(prompt)
  ...
groq.BadRequestError: Error code: 400 - {'error': {'message': "Failed to call a function.
Please adjust your prompt. See 'failed_generation' for more details.", 'type':
'invalid_request_error', 'code': 'tool_use_failed', 'failed_generation':
'<function=_ExtractedAttractions> {"attractions": [ ... modelo entrou em loop de
repetição e truncou o JSON ... ]'}}
```

---

## Correção de erro: tool_use_failed em build_itinerary (schema)

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Correção de bug

### Prompt original
```
Esse erro aconteceu, investigue e ajuste:

... (busca de pontos turísticos da Itália, depois:)
Você: Monte um roteiro para 1 semana na itália
Traceback (most recent call last):
  ...
  File "C:\git\mini-projeto-ItinerAI\itinerai_agent\utils\nodes.py", line 21, in call_llm
    response = _llm_with_tools.invoke([SystemMessage(content=AGENT_SYSTEM_PROMPT), *state.messages])
  ...
groq.BadRequestError: Error code: 400 - {'error': {'message': "Failed to call a function.
Please adjust your prompt. See 'failed_generation' for more details.", 'type':
'invalid_request_error', 'code': 'tool_use_failed', 'failed_generation':
'<function=build_itinerary>{"attractions": [ ... 16 pontos turísticos inline ... ],
"destination": "Itália", "num_days": 7}'}}
```

---

## Ferramenta de geração do arquivo .md do itinerário

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrução
Implementar ferramenta de criação de arquivo .md com o itinerário

#Detalhes
1. Criar a ferramenta para criar o arquivo .md em output/
2. O nome de cada arquivo deve ser referente ao destino + os dias de viagem
3. Caso já exista documeto com o mesmo nome, adicionar um número sequencial como no padrão do windows, como "(2)" para o segundo, "(3)" para o terceiro e assim sucessivamente
4. O agente não passa mais a logar o itinerário no terminal, apenas um aviso: "O arquivo  <file-name> com o itinerário para seu destino for cirado em output/
```

---

## Nó de validação de entrada (anti prompt injection, idioma e URLs)

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrução
Adicionar etapa/nó de validação

#Detalhes
1. Impedir prompt injection, proibir comandos como: "Ignorar prompts/instruções anteriores"
2. Impedir prompts em outros idiomas, a comunicação somente deve acontecer em português
3. Impedir acessar URLs/Links disponibilizados pelo usuários
4. Nesses casos, enviar uma mensagem informativa ao usuário
5. Atualizar arquivo CLAUDE.md com nova funcionalidade de validação
```

---

## Ajuste: validação somente por regex, sem LLM (6 idiomas)

* Data: 2026-07-19
* Autor: joaopuel
* Tipo: Ajuste / Implementação

### Prompt original
```
Antes mencionei para utilizar o sistemas híbrido de verificação usando regex e LLM. Mas altera para utilizar somente regex para detectar prompt injections nos 5 idiomais mais falados no mundo, inglês, mandarin, hindi, espanhol, francês + português. Evitando assim sobrecarregar ainda mais a LLM, que é um modelo mais fraco. Altere o plano.
```

---

## Validação de campos obrigatórios (destino e datas/duração)

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrução
Adicionar novas validações da entrada do usuário

#Detalhes
1. Após a entrada do usuário, além das validações de segurança é preciso validar se todos os campos necessários foram informados, como destino, datas ou duração da viagem em dias
2. Verificar as informações em sequência:
2.1. Qual o destino de sua viagem?
2.2. Quais são as datas de ida e de volta? Ou qual a duração (dias) da sua viagem?
3. Caso alguma das informações não tenha sido fornecida, solicitar ao usuário a informação
```

---

## Memória persistente do agente (SQLite)

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Implementação

### Prompt original
```
#Instrução
Adicione memória persistente do agente

#Detalhes
1. Utilize o SQLlite
2. Salve informações das últimas conversas, como destino, datas e quantidade de dias de viagem
3. As informações devem ser salvas assim logo depois do nó de validação, para que, caso ocorra algum erro na busca de atrações ou geração de intinerário, o processo possa ser iniciado novamente de forma mais fácil 
4. Atualize o CLAUDE.md com a nova funcionalidade
```

---

## Correção: memória sobrescrita e exibição da última viagem no início

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Correção de bug / Ajuste

### Prompt original
```
O salvamento de memória não funcionou. Interação com o agente:

ItinerAI: Parabéns! Seu itinerário para a Alemanha está pronto! Por favor, verifique o arquivo itinerario-alemanha-7-dias.md em output/ para ver o roteiro detalhado da sua viagem. Lembre-se de sempre verificar as informações de eventos e festivais no site oficial antes de confirmar. Boa viagem!
Você: sair
(.venv) PS C:\git\mini-projeto-ItinerAI> python main.py
ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem.
(digite 'sair' para encerrar)
ItinerAI: Qual o seu próximo destino?
Você: Qual foi meu último destino?
ItinerAI: Não posso encontrar informações sobre o seu último destino. Posso ajudar com outra coisa?
Você: sair


Analise o que pode ter acontecido e faça as alterações
```

---

## Remoção de ferramentas (busca de eventos/festivais e cálculo por datas)

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Refatoração / Remoção de funcionalidades

### Prompt original
```
#Instrução
Por se tratar de um modelo simples, o montante de ferramentas pode estar causando sobrecarga de contexto na LLM. Remova algumas funcionalidades.

#Detalhes
1. Remova a ferramenta de busca de eventos/festivais. Somente será trabalhado a busca de pontos turísticos.
2. Remova a ferramente que calcula a duração entre duas datas. Somente será informada a duração da viagem em dias.
3. Busque no projeto e remova quaisquer menções a estas funcionalidades
```

---

## Remoção dos períodos do dia (Manhã/Tarde/Noite) do itinerário

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Refatoração / Remoção de funcionalidades

### Prompt original
```
Para reduzir ainda mais o contexto do agente. Remova todas referências aos períodos "Manhã", "Tarde", "Noite" na contrução do itinerário.
```

---

## Ajuste do máximo de atrações por dia (3)

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Ajuste

### Prompt original
```
Altera também para que o máximo de atrações por dia ser apenas 3
```

---

## Correção: tool calls vazadas como texto pelo llama-3.1-8b

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Correção de bug

### Prompt original
```
O que pode estar acontecendo aqui?

ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem.
(digite 'sair' para encerrar)
ItinerAI: Encontrei uma viagem em andamento para Espanha. Deseja retomá-la? (s/n)
Você: não
ItinerAI: Qual o seu próximo destino?
Você: Monte um itinerário de 3 dias para a Inglaterra
ItinerAI: function=build_itinerary>{"destination": "Inglaterra", "num_days": 3}</function>

function=search_tourist_attractions>{"destination": "Inglaterra"}</function>
Você:
```

---

## Ajuste da apresentação: asteriscos para funcionalidades ausentes

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Documentação / Ajuste

### Prompt original
```
#Instrução
Ajuste a apresetação do projeto para apresentar correamtente as funcionalidade

#Detalhes
1. No arquivo, docs/appresentacao, adicione um aterisco vemelho nas menções a preferências do usuários e a ferramenta search_local_events. Essas funcionalidades não estão presentes nesta versão do agente para não sobrecarregar a LLM fraca
2. Também adicone dois ateriscos na ferramenta save_itinerary(), essa ferramente foi mesclada com a ferramenta build_itinerary para também não sobrecarregar o contexto
3. Adicione essas observações, mas não altere o restante da apresentação, pois o projeto já foi apresentado com a mesma
```

---

## Apresentação: três asteriscos nas informações de ida/volta

* Data: 2026-07-20
* Autor: joaopuel
* Tipo: Documentação / Ajuste

### Prompt original
```
Adicione também tres asteriscos nas informações de ida/volta, funcionalidade também removida para não sobrecarregar o contexto. Foi substiuido por apenas informar a duração da viagem em dias
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
