from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class TouristAttraction(BaseModel):
    name: str
    description: str


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    destination: str | None = None
    tourist_attractions: list[TouristAttraction] = Field(default_factory=list)
