import logging
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")  # evita mojibake de acentos no console do Windows

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes de importar itinerai_agent.agent, pois
# utils/config.py e nodes.py/tools.py leem GROQ_API_KEY / GROQ_MODEL /
# GROQ_TEMPERATURE / WIKIPEDIA_TIMEOUT no import

from itinerai_agent.utils.logging_config import configure_logging, new_run_id, run_id_var

configure_logging()  # pluga o handler JSON + arquivo antes de importar o grafo
# (a biblioteca só tem o NullHandler); é a aplicação que configura o logging

from langchain_core.messages import HumanMessage

from itinerai_agent.agent import graph
from itinerai_agent.utils import audit
from itinerai_agent.utils.memory import TripMemory, load_trip_memory, save_trip_memory
from itinerai_agent.utils.notifications import NotificationResult
from itinerai_agent.utils.state import AgentState
from itinerai_agent.utils.validation import INVALID_EMAIL_MESSAGE, is_valid_email

logger = logging.getLogger("itinerai_agent.cli")


def _save_state(state: AgentState) -> None:
    """Mantém a memória persistente sincronizada com o estado atual da conversa.

    Roda ao fim de cada turno; o nó `persist_memory` salva no início do turno
    (antes das buscas), então este save complementa capturando o que foi
    descoberto no próprio turno — datas, duração e a conclusão do itinerário.

    Só salva quando já existe um destino, para não apagar a última viagem
    guardada com um registro vazio (ex.: uma conversa nova sem destino ainda)."""
    if state.destination is None:
        return
    save_trip_memory(
        TripMemory(
            destination=state.destination,
            num_days=state.num_days,
            completed=state.itinerary is not None,
        )
    )


def _trip_description(memory: TripMemory) -> str:
    """Descrição curta da viagem salva para exibir ao usuário (destino +
    duração, quando houver)."""
    description = memory.destination or ""
    if memory.num_days:
        description += f" ({memory.num_days} dias)"
    return description


def _resume_message(memory: TripMemory) -> str:
    """Mensagem sintética que reafirma a viagem salva, para o agente retomar a
    busca/roteiro sem o usuário precisar redigitar destino e duração."""
    parts = [f"Quero retomar minha viagem para {memory.destination}"]
    if memory.num_days:
        parts.append(f"com duração de {memory.num_days} dias")
    return ", ".join(parts) + "."


def _prompt_yes_no(question: str) -> bool:
    """Faz uma pergunta sim/não determinística no terminal (sem passar pelo LLM)."""
    print(f"ItinerAI: {question}")
    try:
        answer = input("Você: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False
    return answer in {"s", "sim", "y", "yes"}


def _prompt_text(question: str) -> str | None:
    """Faz uma pergunta aberta determinística no terminal (sem passar pelo LLM).

    Devolve `None` quando o usuário interrompe (Ctrl+C / EOF), para o chamador
    distinguir **cancelamento** de resposta malformada — nunca de
    consentimento."""
    print(f"ItinerAI: {question}")
    try:
        return input("Você: ").strip()
    except (KeyboardInterrupt, EOFError):
        return None


def _startup(memory: TripMemory | None) -> AgentState | None:
    """Mostra a última viagem salva (concluída ou não) e oferece retomá-la/
    refazê-la. Retorna um `AgentState` pré-preenchido (destino/datas/dias + uma
    mensagem de retomada) se o usuário aceitar, ou `None` para começar do zero
    (inclusive quando não há registro ou ele não tem destino)."""
    if memory is None or not memory.destination:
        return None

    description = _trip_description(memory)
    if memory.completed:
        question = f"Sua última viagem foi para {description}. Deseja refazer o roteiro dela? (s/n)"
    else:
        question = f"Encontrei uma viagem em andamento para {description}. Deseja retomá-la? (s/n)"

    if not _prompt_yes_no(question):
        return None

    return AgentState(
        destination=memory.destination,
        num_days=memory.num_days,
        messages=[HumanMessage(content=_resume_message(memory))],
    )


def _run_turn(state: AgentState) -> AgentState:
    """Executa um turno da conversa: gera o `run_id` do turno, invoca o grafo,
    persiste a memória e imprime a resposta. Os eventos `run_start`/`run_end`
    delimitam o turno nos logs estruturados — todos com o mesmo `run_id`, que
    também é publicado no `ContextVar` para o `copy_context()` do fan-out da
    busca já herdá-lo.

    `recursion_limit` acima do default (25): o fan-out da busca
    (dispatch_search → fetch_* → merge_pages) consome alguns supersteps a mais
    por busca, e retries do ReAct somam.
    """
    state.run_id = new_run_id()
    token = run_id_var.set(state.run_id)
    start = time.perf_counter()
    try:
        logger.info(
            "run_start",
            extra={
                "messages": len(state.messages),
                "has_destination": state.destination is not None,
            },
        )
        result = graph.invoke(state, {"recursion_limit": 50})
        turn_ms = (time.perf_counter() - start) * 1000  # só o graph.invoke
        state = AgentState.model_validate(result)
        _save_state(state)
        last_message = state.messages[-1]
        logger.info(
            "run_end",
            extra={
                "last_message_type": type(last_message).__name__,
                "itinerary_ready": state.itinerary is not None,
                "duration_ms": round(turn_ms, 1),
            },
        )
        audit.try_record(state.run_id, "graph_invoke", "turn", "ok", turn_ms)
        print(f"ItinerAI: {last_message.content}")
        return state
    except Exception as exc:
        turn_ms = (time.perf_counter() - start) * 1000
        audit.try_record(
            state.run_id, "graph_invoke", "turn", "error", turn_ms, type(exc).__name__
        )
        logger.exception("run_error", extra={"duration_ms": round(turn_ms, 1)})
        raise
    finally:
        run_id_var.reset(token)


def _record_offer_outcome(state: AgentState, status: str) -> AgentState:
    """Grava no estado um desfecho da oferta de envio que **não passa pelo
    grafo** (`declined`, `cancelled`, `invalid_email`) e emite os dois sinais de
    observabilidade que o nó `notify_recipient` emitiria se tivesse rodado.

    O `run_id` é o do turno anterior — o que gerou o itinerário —, que é
    exatamente o que correlaciona a oferta com o roteiro que a motivou."""
    state.notification = NotificationResult(status=status)
    logger.info(f"notification_{status}", extra={"run_id": state.run_id})
    audit.try_record(state.run_id, f"notification_{status}", "turn", "ok")
    return state


def _offer_email(state: AgentState) -> AgentState:
    """Oferece o envio do roteiro por e-mail ao fim do turno em que ele ficou
    pronto (T14/#25).

    O envio para um serviço externo é uma ação irreversível, então o §4.5 exige
    **aprovação humana explícita**: nada sai daqui sem um "s" e um endereço
    bem-formado. A pergunta e a validação são determinísticas, sem passar pelo
    LLM — no mesmo espírito de `validation.py`.

    Só age quando existe um itinerário e a oferta ainda não teve desfecho neste
    roteiro (`state.notification is None`; `call_tools` zera o campo a cada novo
    roteiro). Quando o usuário aprova, grava o e-mail no estado e roda mais um
    turno: `route_entry` desvia o START direto para o nó `notify_recipient`.

    Os desfechos que NÃO chegam ao grafo (recusa, cancelamento, e-mail inválido)
    são registrados aqui no log e na trilha de auditoria. Sem isso, a ausência de
    registro seria indistinguível de "o agente nunca perguntou" — e é justamente
    a recusa que evidencia o limite de autonomia do §4.5."""
    if state.itinerary is None or state.notification is not None:
        return state

    if not _prompt_yes_no("Deseja receber o roteiro por e-mail? (s/n)"):
        # Recusa: nenhuma chamada externa acontece.
        return _record_offer_outcome(state, "declined")

    email = _prompt_text("Para qual e-mail devo enviar?")
    if email is None:
        # Ctrl+C / EOF durante a coleta: cancelamento, não endereço malformado.
        return _record_offer_outcome(state, "cancelled")
    if not is_valid_email(email):
        # Formato inválido: recusa o envio sem acionar o webhook.
        print(f"ItinerAI: {INVALID_EMAIL_MESSAGE}")
        return _record_offer_outcome(state, "invalid_email")

    state.recipient_email = email
    return _run_turn(state)


def main() -> None:
    print("ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem.")
    print("(digite 'sair' para encerrar)")

    resumed = _startup(load_trip_memory())
    if resumed is not None:
        state = _offer_email(_run_turn(resumed))
    else:
        print("ItinerAI: Qual o seu próximo destino?")
        state = AgentState()

    while True:
        try:
            user_input = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando.")
            break
        if user_input.lower() in {"sair", "exit", "quit"}:
            break
        if not user_input:
            continue

        state.messages.append(HumanMessage(content=user_input))
        state = _offer_email(_run_turn(state))


if __name__ == "__main__":
    main()
