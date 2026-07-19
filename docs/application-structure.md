> ## Índice da documentação
> Acesse o índice completo da documentação em: https://docs.langchain.com/llms.txt
> Use este arquivo para descobrir todas as páginas disponíveis antes de explorar mais.

# Estrutura da aplicação

Uma aplicação LangGraph consiste em um ou mais grafos, um arquivo de configuração (`langgraph.json`), um arquivo que especifica as dependências e um arquivo `.env` opcional que especifica as variáveis de ambiente.

Este guia mostra uma estrutura típica de uma aplicação e como fornecer a configuração necessária para implantar uma aplicação com o [LangSmith Deployment](/langsmith/deployment).

<Info>
  O LangSmith Deployment é uma plataforma de hospedagem gerenciada para implantar e escalar agentes LangGraph. Ele cuida da infraestrutura, do escalonamento e das questões operacionais para que você possa implantar seus agentes stateful de longa duração diretamente a partir do seu repositório. Saiba mais na [documentação de Deployment](/langsmith/deployment).
</Info>

## Conceitos-chave

Para implantar usando o LangSmith, as seguintes informações devem ser fornecidas:

1. Um [arquivo de configuração do LangGraph](#configuration-file-concepts) (`langgraph.json`) que especifica as dependências, os grafos e as variáveis de ambiente a serem usados pela aplicação.
2. Os [grafos](#graphs) que implementam a lógica da aplicação.
3. Um arquivo que especifica as [dependências](#dependencies) necessárias para executar a aplicação.
4. As [variáveis de ambiente](#environment-variables) necessárias para a execução da aplicação.

## Estrutura de arquivos

Abaixo estão exemplos de estruturas de diretório para aplicações:

<Tabs>
  <Tab title="Python (requirements.txt)">
    ```plaintext theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    my-app/
    ├── my_agent # todo o código do projeto fica aqui
    │   ├── utils # utilitários para o seu grafo
    │   │   ├── __init__.py
    │   │   ├── tools.py # ferramentas para o seu grafo
    │   │   ├── nodes.py # funções de nó para o seu grafo
    │   │   └── state.py # definição do estado do seu grafo
    │   ├── __init__.py
    │   └── agent.py # código para construir o seu grafo
    ├── .env # variáveis de ambiente
    ├── requirements.txt # dependências do pacote
    └── langgraph.json # arquivo de configuração do LangGraph
    ```
  </Tab>

  <Tab title="Python (pyproject.toml)">
    ```plaintext theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    my-app/
    ├── my_agent # todo o código do projeto fica aqui
    │   ├── utils # utilitários para o seu grafo
    │   │   ├── __init__.py
    │   │   ├── tools.py # ferramentas para o seu grafo
    │   │   ├── nodes.py # funções de nó para o seu grafo
    │   │   └── state.py # definição do estado do seu grafo
    │   ├── __init__.py
    │   └── agent.py # código para construir o seu grafo
    ├── .env # variáveis de ambiente
    ├── langgraph.json  # arquivo de configuração do LangGraph
    └── pyproject.toml # dependências do projeto
    ```
  </Tab>
</Tabs>

<Note>
  A estrutura de diretórios de uma aplicação LangGraph pode variar dependendo da linguagem de programação e do gerenciador de pacotes utilizados.
</Note>

<a id="configuration-file-concepts" />

## Arquivo de configuração

O arquivo `langgraph.json` é um arquivo JSON que especifica as dependências, os grafos, as variáveis de ambiente e outras configurações necessárias para implantar uma aplicação LangGraph.

Consulte a [referência do arquivo de configuração do LangGraph](/langsmith/cli#configuration-file) para detalhes sobre todas as chaves suportadas no arquivo JSON.

<Tip>
  A [LangGraph CLI](/langsmith/cli) usa por padrão o arquivo de configuração `langgraph.json` no diretório atual.
</Tip>

### Exemplos

* As dependências envolvem um pacote local personalizado e o pacote `langchain_openai`.
* Um único grafo será carregado a partir do arquivo `./your_package/your_file.py` com a variável `variable`.
* As variáveis de ambiente são carregadas a partir do arquivo `.env`.

```json theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
{
  "dependencies": ["langchain_openai", "./your_package"],
  "graphs": {
    "my_agent": "./your_package/your_file.py:agent"
  },
  "env": "./.env"
}
```

## Dependências

Uma aplicação LangGraph pode depender de outros pacotes Python.

Em geral, você precisará especificar as seguintes informações para que as dependências sejam configuradas corretamente:

1. Um arquivo no diretório que especifica as dependências (por exemplo, `requirements.txt`, `pyproject.toml` ou `package.json`).

2. Uma chave `dependencies` no [arquivo de configuração do LangGraph](#configuration-file-concepts) que especifica as dependências necessárias para executar a aplicação LangGraph.

3. Quaisquer binários ou bibliotecas de sistema adicionais podem ser especificados usando a chave `dockerfile_lines` no [arquivo de configuração do LangGraph](#configuration-file-concepts).

## Grafos

Use a chave `graphs` no [arquivo de configuração do LangGraph](#configuration-file-concepts) para especificar quais grafos estarão disponíveis na aplicação LangGraph implantada.

Você pode especificar um ou mais grafos no arquivo de configuração. Cada grafo é identificado por um nome (que deve ser único) e um caminho para (1) o grafo compilado ou (2) uma função que define um grafo.

## Variáveis de ambiente

Se você estiver trabalhando localmente com uma aplicação LangGraph implantada, é possível configurar as variáveis de ambiente na chave `env` do [arquivo de configuração do LangGraph](#configuration-file-concepts).

Para uma implantação em produção, normalmente você vai querer configurar as variáveis de ambiente no ambiente de implantação.

***

<div className="source-links">
  <Callout icon="terminal-2">
    [Conecte esta documentação](/use-these-docs) ao Claude, VSCode e outros via MCP para respostas em tempo real.
  </Callout>

  <Callout icon="edit">
    [Edite esta página no GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langgraph/application-structure.mdx) ou [reporte um problema](https://github.com/langchain-ai/docs/issues/new/choose).
  </Callout>
</div>
