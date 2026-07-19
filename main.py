import sys

sys.stdout.reconfigure(encoding="utf-8")  # evita mojibake de acentos no console do Windows

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes de importar itinerai_agent.agent, pois
# nodes.py instancia ChatGroq() no import e precisa da env var já carregada

from langchain_core.messages import HumanMessage

from itinerai_agent.agent import graph
from itinerai_agent.utils.state import AgentState


def main() -> None:
    print("ItinerAI — digite sua mensagem (ou 'sair' para encerrar)")
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
        result = graph.invoke(state)
        state = AgentState.model_validate(result)
        print(f"ItinerAI: {state.messages[-1].content}")


if __name__ == "__main__":
    main()
