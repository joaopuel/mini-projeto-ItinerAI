from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import END

from itinerai_agent.utils.memory import TripMemory, save_trip_memory
from itinerai_agent.utils.prompts import AGENT_SYSTEM_PROMPT
from itinerai_agent.utils.state import AgentState
from itinerai_agent.utils.tools import (
    build_itinerary,
    calculate_trip_days,
    search_events_and_festivals,
    search_tourist_attractions,
)
from itinerai_agent.utils.validation import validate_user_input

_TOOLS = [
    search_tourist_attractions,
    search_events_and_festivals,
    calculate_trip_days,
    build_itinerary,
]
_TOOLS_BY_NAME = {tool.__name__: tool for tool in _TOOLS}

_llm = ChatGroq(model="llama-3.1-8b-instant")
_llm_with_tools = _llm.bind_tools(_TOOLS)


def validate_input(state: AgentState) -> dict:
    # Porta de entrada do grafo: valida a última mensagem do usuário antes de
    # ela chegar ao LLM. Se violar uma regra (prompt injection, idioma em
    # script não-latino ou URL/link), responde direto com uma mensagem
    # informativa em português — sem deixar o conteúdo entrar no loop de tools.
    last_message = state.messages[-1]
    if not isinstance(last_message, HumanMessage):
        return {}
    refusal = validate_user_input(str(last_message.content))
    if refusal is not None:
        return {"messages": [AIMessage(content=refusal)]}
    return {}


def route_after_validation(state: AgentState) -> str:
    # Se a validação inseriu uma resposta (AIMessage), encerra o turno; caso
    # contrário, a última mensagem ainda é a do usuário e seguimos para
    # persistir a memória antes de chamar o LLM.
    if isinstance(state.messages[-1], AIMessage):
        return END
    return "persist_memory"


def persist_memory(state: AgentState) -> dict:
    # Roda logo após a validação (só no caminho válido): salva os dados da
    # viagem coletados até aqui (destino, datas, duração) na memória persistente.
    # Como acontece antes das buscas e da montagem do roteiro, se algo falhar
    # adiante a viagem já está salva e a conversa pode ser retomada no próximo
    # início. Não altera o estado.
    #
    # Só persiste quando já existe um destino: no começo de uma nova conversa o
    # estado ainda está vazio, e salvar aqui apagaria a última viagem guardada
    # (sobrescrevendo o registro único com tudo nulo).
    if state.destination is None:
        return {}
    save_trip_memory(
        TripMemory(
            destination=state.destination,
            start_date=state.start_date,
            end_date=state.end_date,
            num_days=state.num_days,
            completed=state.itinerary is not None,
        )
    )
    return {}


def call_llm(state: AgentState) -> dict:
    # Rede de segurança: se o LLM falhar ao gerar a resposta (ex.: uma tool
    # call malformada que a Groq rejeita com tool_use_failed), respondemos com
    # uma mensagem amigável em vez de derrubar o agente no terminal.
    try:
        response = _llm_with_tools.invoke(
            [SystemMessage(content=AGENT_SYSTEM_PROMPT), *state.messages]
        )
    except Exception:
        response = AIMessage(
            content=(
                "Desculpe, tive um problema ao processar seu pedido agora. Pode reformular "
                "ou tentar novamente em instantes?"
            )
        )
    return {"messages": [response]}


def should_call_tools(state: AgentState) -> str:
    last_message = state.messages[-1]
    if getattr(last_message, "tool_calls", None):
        return "call_tools"
    return END


def call_tools(state: AgentState) -> dict:
    last_message = state.messages[-1]

    tool_messages = []
    update: dict = {}
    for call in last_message.tool_calls:
        tool_fn = _TOOLS_BY_NAME[call["name"]]
        args = dict(call["args"])

        # A construção do itinerário usa as atrações/eventos já encontrados e
        # guardados no estado; injetamos aqui para o LLM não precisar
        # re-serializar essas listas (só fornece destination e num_days).
        if call["name"] == "build_itinerary":
            args["attractions"] = state.tourist_attractions
            args["events"] = state.traditional_events

        result = tool_fn(**args)

        if call["name"] == "search_tourist_attractions":
            update["destination"] = result.destination
            update["tourist_attractions"] = result.attractions
            tool_content = result.model_dump_json()
        elif call["name"] == "search_events_and_festivals":
            update["destination"] = result.destination
            update["traditional_events"] = result.events
            tool_content = result.model_dump_json()
        elif call["name"] == "calculate_trip_days":
            # Guarda datas e duração no estado (quando válidas) para que a
            # memória persistente possa salvá-las e permitir a retomada.
            if result.valid:
                update["start_date"] = result.start_date
                update["end_date"] = result.end_date
                update["num_days"] = result.num_days
            tool_content = result.model_dump_json()
        elif call["name"] == "build_itinerary":
            update["itinerary"] = result.itinerary
            update["num_days"] = result.num_days
            # Só o aviso volta para o LLM: o itinerário completo fica no arquivo
            # e não deve ser listado no terminal.
            tool_content = result.message
        else:
            tool_content = result.model_dump_json()

        tool_messages.append(ToolMessage(content=tool_content, tool_call_id=call["id"]))

    update["messages"] = tool_messages
    return update
