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


class TraditionalEvent(BaseModel):
    """Evento/festival tradicional da região. Sem data exata: deve ser
    tratado como sugestão para o itinerário, a confirmar no site oficial."""

    name: str
    description: str
    location: str = ""
    """Local exato (bairro/endereço/área) ou provável do evento."""


class ItinerarySlot(BaseModel):
    """Um período de um dia do itinerário (manhã, tarde ou noite)."""

    period: str
    attractions: list[str] = Field(default_factory=list)


class ItineraryDay(BaseModel):
    """Um dia do itinerário, com as atrações agrupadas por período."""

    day: int
    area: str = ""
    slots: list[ItinerarySlot] = Field(default_factory=list)


class Itinerary(BaseModel):
    """Itinerário dia a dia montado a partir das atrações e eventos encontrados."""

    destination: str
    num_days: int
    days: list[ItineraryDay] = Field(default_factory=list)
    note: str | None = None
    event_suggestions: list[TraditionalEvent] = Field(default_factory=list)
    disclaimer: str = ""


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    destination: str | None = None
    tourist_attractions: list[TouristAttraction] = Field(default_factory=list)
    traditional_events: list[TraditionalEvent] = Field(default_factory=list)
    itinerary: Itinerary | None = None
