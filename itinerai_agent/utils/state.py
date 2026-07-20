from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class TouristAttraction(BaseModel):
    name: str
    description: str
    location: str = ""
    """Local exato (bairro/endereço/área) ou provável da atração. Usado para
    agrupar atrações próximas no mesmo dia do itinerário."""


class ItineraryDay(BaseModel):
    """Um dia do itinerário, com a lista de atrações a visitar."""

    day: int
    area: str = ""
    attractions: list[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    """Itinerário dia a dia montado a partir das atrações encontradas."""

    destination: str
    num_days: int
    days: list[ItineraryDay] = Field(default_factory=list)
    note: str | None = None


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    destination: str | None = None
    # Duração da viagem em dias. Fica no estado (além de ser passada a
    # build_itinerary) para poder ser persistida pela memória e permitir a
    # retomada da conversa após uma falha — ver utils/memory.py.
    num_days: int | None = None
    tourist_attractions: list[TouristAttraction] = Field(default_factory=list)
    itinerary: Itinerary | None = None
