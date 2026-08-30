import functools
import json
import logging
import re
import time
from uuid import uuid4

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq
from langgraph.graph import END

from itinerai_agent.utils import audit
from itinerai_agent.utils.config import GROQ_MODEL, GROQ_TEMPERATURE
from itinerai_agent.utils.logging_config import run_id_var
from itinerai_agent.utils.memory import TripMemory, save_trip_memory
from itinerai_agent.utils.prompts import AGENT_SYSTEM_PROMPT
from itinerai_agent.utils.state import AgentState, PendingSearch, WikipediaPageResult
from itinerai_agent.utils.tools import (
    TouristAttractionSearchResult,
    build_itinerary,
    fetch_page_attractions,
    search_tourist_attractions,
)
from itinerai_agent.utils.validation import (
    FOREIGN_LANGUAGE_MESSAGE,
    INJECTION_MESSAGE,
    URL_MESSAGE,
    validate_user_input,
)

logger = logging.getLogger(__name__)

# Mapeia a mensagem de recusa (constante de `validation.py`) → o motivo do
# bloqueio, para o log. Opção deliberada: zero mudança em `validation.py` (cujo
# design é "não alterar sem alinhar") — só importamos as 3 constantes.
_VALIDATION_REASONS = {
    INJECTION_MESSAGE: "prompt_injection",
    FOREIGN_LANGUAGE_MESSAGE: "non_latin_script",
    URL_MESSAGE: "url",
}

_TOOLS = [
    search_tourist_attractions,
    build_itinerary,
]
_TOOLS_BY_NAME = {tool.__name__: tool for tool in _TOOLS}

_llm = ChatGroq(model=GROQ_MODEL, temperature=GROQ_TEMPERATURE)
_llm_with_tools = _llm.bind_tools(_TOOLS)


def _logged_node(fn):
    """Instrumenta um nó do grafo: loga `node_start` / `node_end` (e
    `node_error` + traceback, re-levantando), **mede a latência** (T05/#16) e
    grava uma linha na trilha de auditoria, e publica o `run_id` do turno no
    `ContextVar`, para as chamadas mais profundas (`tools.py`) o herdarem —
    inclusive nos ramos paralelos do fan-out, que rodam em threads próprias."""

    @functools.wraps(fn)
    def wrapper(state: AgentState) -> dict:
        run_id = getattr(state, "run_id", "") or "-"
        token = run_id_var.set(run_id)
        start = time.perf_counter()
        try:
            logger.info("node_start", extra={"node": fn.__name__})
            try:
                result = fn(state)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    "node_error",
                    extra={
                        "node": fn.__name__,
                        "error": type(exc).__name__,
                        "duration_ms": round(duration_ms, 1),
                    },
                    exc_info=True,
                )
                audit.try_record(
                    run_id, fn.__name__, "node", "error", duration_ms, type(exc).__name__
                )
                raise
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "node_end",
                extra={"node": fn.__name__, "duration_ms": round(duration_ms, 1)},
            )
            audit.try_record(run_id, fn.__name__, "node", "ok", duration_ms)
            return result
        finally:
            run_id_var.reset(token)

    return wrapper


def _logged_router(fn):
    """Instrumenta uma função de roteamento: loga `routing_decision` com o nome
    do router e a decisão retornada."""

    @functools.wraps(fn)
    def wrapper(state: AgentState) -> str:
        token = run_id_var.set(getattr(state, "run_id", "") or "-")
        try:
            decision = fn(state)
            logger.info(
                "routing_decision",
                extra={"router": fn.__name__, "decision": str(decision)},
            )
            return decision
        finally:
            run_id_var.reset(token)

    return wrapper


def _summarize_args(raw: dict) -> dict:
    """Resumo seguro dos argumentos de uma tool para o log: strings longas são
    truncadas e coleções viram `<tipo len=N>`. Recebe só os argumentos vindos do
    LLM (ex.: destination, num_days) — nunca a lista de atrações injetada pelo
    grafo em `call_tools`."""
    summary: dict = {}
    for key, value in raw.items():
        if isinstance(value, str):
            summary[key] = value if len(value) <= 120 else value[:120] + "…"
        elif isinstance(value, (int, float, bool)) or value is None:
            summary[key] = value
        elif hasattr(value, "__len__"):
            summary[key] = f"<{type(value).__name__} len={len(value)}>"
        else:
            summary[key] = f"<{type(value).__name__}>"
    return summary


def _log_page_fetched(node: str, result: WikipediaPageResult) -> None:
    """Loga `page_fetched` para um ramo do fan-out da busca (só metadados)."""
    logger.info(
        "page_fetched",
        extra={
            "node": node,
            "kind": result.kind,
            "found": result.found,
            "unavailable": result.unavailable,
            "attraction_count": len(result.attractions),
        },
    )


# Modelos menores às vezes "vazam" as tool calls no formato nativo do Llama
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


def _drop_premature_build_itinerary(calls: list[dict]) -> list[dict]:
    """Quando `search_tourist_attractions` e `build_itinerary` são pedidos no
    mesmo lote, descarta o `build_itinerary` — a busca precisa rodar antes (e o
    grafo roteia a busca para o fan-out, que responde só ao tool_call_id da
    busca). O modelo re-emite o `build_itinerary` no turno seguinte, já com as
    atrações no estado. Vale para tool calls vazados como texto e para tool
    calls estruturados."""
    names = {call["name"] for call in calls}
    if "search_tourist_attractions" in names:
        return [call for call in calls if call["name"] != "build_itinerary"]
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
        logger.warning("leaked_tool_calls_unrecoverable")
        return AIMessage(
            content=(
                "Desculpe, me atrapalhei ao preparar seu pedido. Pode reformular ou tentar "
                "novamente em instantes?"
            )
        )
    kept = _drop_premature_build_itinerary(calls)
    logger.info(
        "leaked_tool_calls_recovered",
        extra={"count": len(kept), "tools": [call["name"] for call in kept]},
    )
    return AIMessage(content="", tool_calls=kept)


@_logged_node
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
        logger.info(
            "validation_blocked",
            extra={
                "node": "validate_input",
                "reason": _VALIDATION_REASONS.get(refusal, "unknown"),
            },
        )
        return {"messages": [AIMessage(content=refusal)]}
    return {}


@_logged_router
def route_after_validation(state: AgentState) -> str:
    # Se a validação inseriu uma resposta (AIMessage), encerra o turno; caso
    # contrário, a última mensagem ainda é a do usuário e seguimos para
    # persistir a memória antes de chamar o LLM.
    if isinstance(state.messages[-1], AIMessage):
        return END
    return "persist_memory"


@_logged_node
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
    logger.info(
        "memory_persisted",
        extra={
            "node": "persist_memory",
            "has_num_days": state.num_days is not None,
            "completed": state.itinerary is not None,
        },
    )
    return {}


@_logged_node
def call_llm(state: AgentState) -> dict:
    # Rede de segurança: se o LLM falhar ao gerar a resposta (ex.: uma tool
    # call malformada que a Groq rejeita com tool_use_failed), respondemos com
    # uma mensagem amigável em vez de derrubar o agente no terminal.
    try:
        response = _llm_with_tools.invoke(
            [SystemMessage(content=AGENT_SYSTEM_PROMPT), *state.messages]
        )
    except Exception as exc:
        logger.warning("llm_exception_fallback", extra={"node": "call_llm"})
        audit.try_record(
            state.run_id, "llm_agent", "tool", "fallback", error=type(exc).__name__
        )
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
    message = _repair_leaked_response(response)
    # Mesmo lote com busca + montagem do roteiro (tool calls estruturados):
    # mantém só a busca — ela roda antes (o grafo a roteia para o fan-out, que
    # responde apenas ao tool_call_id da busca).
    calls = getattr(message, "tool_calls", None)
    if calls:
        kept = _drop_premature_build_itinerary(calls)
        if len(kept) != len(calls):
            message = AIMessage(content=message.content, tool_calls=kept, id=message.id)
    final_calls = getattr(message, "tool_calls", None)
    if final_calls:
        logger.info(
            "llm_decision",
            extra={
                "node": "call_llm",
                "outcome": "tool_calls",
                "tools": [call["name"] for call in final_calls],
            },
        )
    else:
        logger.info(
            "llm_decision",
            extra={"node": "call_llm", "outcome": "plain_answer"},
        )
    return {"messages": [message]}


@_logged_router
def route_after_llm(state: AgentState) -> str:
    # 3 saídas: sem tool call → fim do turno (condição de parada); busca de
    # atrações → fan-out paralelo das páginas da Wikipédia (dispatch_search);
    # qualquer outra tool → call_tools.
    last_message = state.messages[-1]
    calls = getattr(last_message, "tool_calls", None)
    if not calls:
        return END
    if any(call["name"] == "search_tourist_attractions" for call in calls):
        return "dispatch_search"
    return "call_tools"


@_logged_node
def call_tools(state: AgentState) -> dict:
    # A busca de atrações NÃO passa por aqui: `route_after_llm` a roteia sempre
    # para o fan-out `dispatch_search → fetch_* → merge_pages`. Este nó trata as
    # demais ferramentas (hoje, só `build_itinerary`).
    last_message = state.messages[-1]

    tool_messages = []
    update: dict = {}
    for call in last_message.tool_calls:
        tool_fn = _TOOLS_BY_NAME[call["name"]]
        args = dict(call["args"])
        # Resumo dos argumentos ANTES da injeção da lista de atrações (que fica
        # oculta do modelo e não deve ir para o log).
        logged_args = _summarize_args(call["args"])

        # A construção do itinerário usa as atrações já encontradas e guardadas
        # no estado; injetamos aqui para o LLM não precisar re-serializar essa
        # lista (só fornece destination e num_days).
        if call["name"] == "build_itinerary":
            args["attractions"] = state.tourist_attractions

        tool_start = time.perf_counter()
        try:
            result = tool_fn(**args)
        except Exception as exc:
            tool_ms = (time.perf_counter() - tool_start) * 1000
            logger.error(
                "tool_executed",
                extra={
                    "node": "call_tools",
                    "tool": call["name"],
                    "tool_args": logged_args,
                    "status": "error",
                    "error": type(exc).__name__,
                    "duration_ms": round(tool_ms, 1),
                },
            )
            audit.try_record(
                state.run_id, call["name"], "tool", "error", tool_ms, type(exc).__name__
            )
            raise
        tool_ms = (time.perf_counter() - tool_start) * 1000
        logger.info(
            "tool_executed",
            extra={
                "node": "call_tools",
                "tool": call["name"],
                "tool_args": logged_args,
                "status": "ok",
                "duration_ms": round(tool_ms, 1),
            },
        )
        audit.try_record(state.run_id, call["name"], "tool", "ok", tool_ms)

        if call["name"] == "build_itinerary":
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


def _pending_search_call(message: BaseMessage) -> dict | None:
    """Encontra a tool call `search_tourist_attractions` numa AIMessage."""
    for call in getattr(message, "tool_calls", None) or []:
        if call["name"] == "search_tourist_attractions":
            return call
    return None


def _require_pending_search(state: AgentState) -> PendingSearch:
    # `dispatch_search` sempre preenche `pending_search` antes dos nós do
    # fan-out; o assert transforma uma violação de invariante do grafo num
    # erro claro em vez de um AttributeError obscuro.
    pending = state.pending_search
    assert pending is not None, "dispatch_search precisa rodar antes de fetch_*/merge_pages"
    return pending


@_logged_node
def dispatch_search(state: AgentState) -> dict:
    # Origem única do fan-out da busca: extrai destino e tool_call_id da tool
    # call pedida pelo LLM e guarda em `pending_search`, para os nós `fetch_*` e
    # `merge_pages` não reprocessarem `messages`.
    call = _pending_search_call(state.messages[-1])
    destination = str((call["args"] if call else {}).get("destination", "")).strip()
    tool_call_id = call["id"] if call else ""
    logger.info(
        "search_dispatched",
        extra={"node": "dispatch_search", "destination": destination},
    )
    return {
        "pending_search": PendingSearch(destination=destination, tool_call_id=tool_call_id)
    }


@_logged_node
def fetch_tourism_page(state: AgentState) -> dict:
    # Ramo paralelo 1: página "Tourism in <destino>".
    pending = _require_pending_search(state)
    result = fetch_page_attractions(
        f"Tourism in {pending.destination}", pending.destination, "tourism"
    )
    _log_page_fetched("fetch_tourism_page", result)
    return {"page_results": {"tourism": result}}


@_logged_node
def fetch_destination_page(state: AgentState) -> dict:
    # Ramo paralelo 2: página "<destino>".
    pending = _require_pending_search(state)
    result = fetch_page_attractions(
        pending.destination, pending.destination, "destination"
    )
    _log_page_fetched("fetch_destination_page", result)
    return {"page_results": {"destination": result}}


@_logged_node
def merge_pages(state: AgentState) -> dict:
    # Fan-in determinístico (sem LLM): prioriza a página "Tourism in <destino>"
    # quando ela rendeu atrações; senão a página do destino; senão found=False.
    # Reproduz a ordem de fallback de search_tourist_attractions e devolve o
    # mesmo TouristAttractionSearchResult (mesmo formato de ToolMessage que
    # call_tools produzia para a busca).
    pending = _require_pending_search(state)
    results = state.page_results
    tourism = results.get("tourism")
    destination_page = results.get("destination")

    if tourism is not None and tourism.attractions:
        chosen = tourism
        chosen_kind = "tourism"
    elif destination_page is not None and destination_page.attractions:
        chosen = destination_page
        chosen_kind = "destination"
    else:
        chosen = None
        chosen_kind = "none"

    # Se não achamos atrações E algum ramo caiu por indisponibilidade da
    # Wikipédia (falha de rede após os retries), sinaliza `unavailable` para o
    # LLM avisar "problema técnico" em vez de "destino sem informação".
    pages = [page for page in (tourism, destination_page) if page is not None]
    unavailable = chosen is None and any(page.unavailable for page in pages)

    result = TouristAttractionSearchResult(
        destination=pending.destination,
        source_url=chosen.source_url if chosen else None,
        found=chosen is not None,
        unavailable=unavailable,
        attractions=chosen.attractions if chosen else [],
    )
    logger.info(
        "search_merged",
        extra={
            "node": "merge_pages",
            "chosen": chosen_kind,
            "found": result.found,
            "unavailable": result.unavailable,
            "attraction_count": len(result.attractions),
        },
    )
    return {
        "destination": result.destination,
        "tourist_attractions": result.attractions,
        "messages": [
            ToolMessage(content=result.model_dump_json(), tool_call_id=pending.tool_call_id)
        ],
    }
