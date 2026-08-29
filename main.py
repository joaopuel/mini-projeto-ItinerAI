import sys

sys.stdout.reconfigure(encoding="utf-8")  # evita mojibake de acentos no console do Windows

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes de importar itinerai_agent.agent, pois
# nodes.py instancia ChatGroq() no import e precisa da env var já carregada

from langchain_core.messages import HumanMessage

from itinerai_agent.agent import graph
from itinerai_agent.utils.memory import TripMemory, load_trip_memory, save_trip_memory
from itinerai_agent.utils.state import AgentState


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


def main() -> None:
    print("ItinerAI: Sou ItinerAi, o seu melhor companheiro de viagem.")
    print("(digite 'sair' para encerrar)")

    resumed = _startup(load_trip_memory())
    if resumed is not None:
        state = resumed
        result = graph.invoke(state, {"recursion_limit": 50})
        state = AgentState.model_validate(result)
        _save_state(state)
        print(f"ItinerAI: {state.messages[-1].content}")
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
        # recursion_limit acima do default (25): o fan-out da busca
        # (dispatch_search → fetch_* → merge_pages) consome alguns supersteps a
        # mais por busca, e retries do ReAct somam.
        result = graph.invoke(state, {"recursion_limit": 50})
        state = AgentState.model_validate(result)
        _save_state(state)
        print(f"ItinerAI: {state.messages[-1].content}")


if __name__ == "__main__":
    main()
