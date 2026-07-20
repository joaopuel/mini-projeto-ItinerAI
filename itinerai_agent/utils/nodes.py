import json
import re
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import END

from itinerai_agent.utils.memory import TripMemory, save_trip_memory
from itinerai_agent.utils.prompts import AGENT_SYSTEM_PROMPT
from itinerai_agent.utils.state import AgentState
from itinerai_agent.utils.tools import (
    build_itinerary,
    search_tourist_attractions,
)
from itinerai_agent.utils.validation import validate_user_input

_TOOLS = [
    search_tourist_attractions,
    build_itinerary,
]
_TOOLS_BY_NAME = {tool.__name__: tool for tool in _TOOLS}

_llm = ChatGroq(model="llama-3.1-8b-instant")
_llm_with_tools = _llm.bind_tools(_TOOLS)

# O llama-3.1-8b-instant às vezes "vaza" as tool calls no formato nativo do Llama
# (<function=nome>{json}</function>) como TEXTO da resposta, em vez de gerar
# tool_calls estruturados — a Groq não parseia, o campo tool_calls fica vazio e o
# texto cru acabaria impresso no terminal. Este regex recupera essas chamadas.
_LEAKED_TOOL_CALL_RE = re.compile(
    r"<function=([A-Za-z_]\w*)>?\s*(\{.*?\})\s*</function>",
    re.DOTALL,
)


def _parse_leaked_tool_calls(content: str) -> list[dict]:
    """Extrai tool calls que o LLM emitiu como texto (formato <function=...>) e as
    devolve como dicts de tool_call válidos. Ignora, com tolerância, nomes
    desconhecidos e JSON malformado (comum quando o modelo trunca a saída)."""
    calls: list[dict] = []
    for match in _LEAKED_TOOL_CALL_RE.finditer(content):
        name, raw_args = match.group(1), match.group(2)
        if name not in _TOOLS_BY_NAME:
            continue
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            continue
        if isinstance(args, dict):
            calls.append(
                {"name": name, "args": args, "id": f"leaked_{uuid4().hex}", "type": "tool_call"}
            )
    return calls


def _repair_leaked_response(response: AIMessage) -> AIMessage:
    """Conserta uma resposta em que o LLM vazou as tool calls como texto.

    Se já houver tool_calls estruturados, devolve a resposta intacta. Caso
    contrário, tenta recuperar as chamadas vazadas: descarta um `build_itinerary`
    prematuro quando há busca no mesmo lote (a busca precisa rodar antes) e, se
    nada for recuperável, troca o texto cru por um aviso amigável em vez de
    exibir o `<function=...>` ao usuário."""
    if getattr(response, "tool_calls", None):
        return response
    content = response.content if isinstance(response.content, str) else ""
    if "<function=" not in content:
        return response
    calls = _parse_leaked_tool_calls(content)
    if not calls:
        return AIMessage(
            content=(
                "Desculpe, me atrapalhei ao preparar seu pedido. Pode reformular ou tentar "
                "novamente em instantes?"
            )
        )
    names = {call["name"] for call in calls}
    if "search_tourist_attractions" in names:
        calls = [call for call in calls if call["name"] != "build_itinerary"]
    return AIMessage(content="", tool_calls=calls)


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
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Desculpe, tive um problema ao processar seu pedido agora. Pode "
                        "reformular ou tentar novamente em instantes?"
                    )
                )
            ]
        }
    # O modelo fraco às vezes vaza as tool calls como texto (formato
    # <function=...>): recupera-as para o grafo executá-las, em vez de imprimir o
    # texto cru no terminal.
    return {"messages": [_repair_leaked_response(response)]}


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

        # A construção do itinerário usa as atrações já encontradas e guardadas
        # no estado; injetamos aqui para o LLM não precisar re-serializar essa
        # lista (só fornece destination e num_days).
        if call["name"] == "build_itinerary":
            args["attractions"] = state.tourist_attractions

        result = tool_fn(**args)

        if call["name"] == "search_tourist_attractions":
            update["destination"] = result.destination
            update["tourist_attractions"] = result.attractions
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
