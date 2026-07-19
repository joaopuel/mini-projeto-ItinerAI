from langchain_groq import ChatGroq

from itinerai_agent.utils.state import AgentState

_llm = ChatGroq(model="llama-3.1-8b-instant")


def call_llm(state: AgentState) -> dict:
    response = _llm.invoke(state.messages)
    return {"messages": [response]}
