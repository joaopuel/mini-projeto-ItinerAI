from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import END

from itinerai_agent.utils.prompts import AGENT_SYSTEM_PROMPT
from itinerai_agent.utils.state import AgentState
from itinerai_agent.utils.tools import (
    build_itinerary,
    search_events_and_festivals,
    search_tourist_attractions,
)

_TOOLS = [search_tourist_attractions, search_events_and_festivals, build_itinerary]
_TOOLS_BY_NAME = {tool.__name__: tool for tool in _TOOLS}

_llm = ChatGroq(model="llama-3.1-8b-instant")
_llm_with_tools = _llm.bind_tools(_TOOLS)


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
        elif call["name"] == "build_itinerary":
            update["itinerary"] = result.itinerary
            # Só o aviso volta para o LLM: o itinerário completo fica no arquivo
            # e não deve ser listado no terminal.
            tool_content = result.message
        else:
            tool_content = result.model_dump_json()

        tool_messages.append(ToolMessage(content=tool_content, tool_call_id=call["id"]))

    update["messages"] = tool_messages
    return update
