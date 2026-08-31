from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from itinerai_agent.utils.notifications import NotificationResult


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


class WikipediaPageResult(BaseModel):
    """Resultado de um dos ramos paralelos da busca da Wikipédia
    (fan-out `fetch_tourism_page` / `fetch_destination_page` em nodes.py)."""

    kind: Literal["tourism", "destination"]
    found: bool = False
    # True quando a página não pôde ser acessada (falha de rede após os retries),
    # para distinguir "indisponível" de "página não existe / sem atrações".
    unavailable: bool = False
    source_url: str | None = None
    attractions: list[TouristAttraction] = Field(default_factory=list)


class PendingSearch(BaseModel):
    """Dados da tool call `search_tourist_attractions` em andamento, extraídos
    por `dispatch_search` para os nós do fan-out usarem sem reprocessar
    `messages`."""

    destination: str
    tool_call_id: str


def _merge_page_results(
    existing: dict[str, WikipediaPageResult] | None,
    new: dict[str, WikipediaPageResult] | None,
) -> dict[str, WikipediaPageResult]:
    """Reducer do campo `page_results`: mescla por chave (`tourism` /
    `destination`). Os dois ramos do fan-out sempre reescrevem sua própria
    chave a cada busca, então resultados de uma busca anterior (retry do
    ReAct ou novo turno) nunca sobrevivem — sem precisar de nó de reset."""
    return {**(existing or {}), **(new or {})}


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    # Correlação dos logs estruturados (T04/#15): UUID gerado por TURNO (uma
    # chamada `graph.invoke`) em `main.py` e propagado pelo estado. Nenhum nó o
    # escreve, então permanece constante durante o turno.
    run_id: str = ""
    destination: str | None = None
    # Duração da viagem em dias. Fica no estado (além de ser passada a
    # build_itinerary) para poder ser persistida pela memória e permitir a
    # retomada da conversa após uma falha — ver utils/memory.py.
    num_days: int | None = None
    tourist_attractions: list[TouristAttraction] = Field(default_factory=list)
    itinerary: Itinerary | None = None
    # Preenchido por `dispatch_search` no início do fan-out da busca da
    # Wikipédia; consumido pelos nós `fetch_*` e por `merge_pages`.
    pending_search: PendingSearch | None = None
    # Escrito concorrentemente pelos dois nós `fetch_*` (uma chave cada); o
    # reducer mescla por chave. Canal tipado, no mesmo espírito de `messages`.
    page_results: Annotated[
        dict[str, WikipediaPageResult], _merge_page_results
    ] = Field(default_factory=dict)
    # --- Envio do roteiro por e-mail via n8n (T14/#25) ---
    # Preenchido por `main.py` DEPOIS da aprovação explícita do usuário e da
    # validação do formato; é o que faz `route_entry` desviar o START para
    # `notify_recipient`. O nó o zera após o envio, para não repetir a chamada.
    recipient_email: str | None = None
    # Desfecho da oferta de envio (enviado, recusado, e-mail inválido, sem
    # configuração ou falha). Enquanto for `None` e houver itinerário, `main.py`
    # oferece o envio ao fim do turno; `call_tools` o zera a cada novo roteiro.
    notification: NotificationResult | None = None
