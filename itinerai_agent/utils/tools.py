"""Tools do agente ItinerAI (busca de pontos turísticos, busca de eventos,
escrita do itinerário .md)."""

from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from itinerai_agent.utils.prompts import ATTRACTION_EXTRACTION_PROMPT, EVENT_EXTRACTION_PROMPT
from itinerai_agent.utils.state import TouristAttraction, TraditionalEvent

WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki"
_REQUEST_HEADERS = {"User-Agent": "ItinerAI/1.0 (https://github.com/joaopuel/mini-projeto-ItinerAI)"}
_MAX_PAGE_TEXT_CHARS = 8000

EVENT_DATES_DISCLAIMER = (
    "As informações de eventos e festivais vêm da Wikipédia, um texto estático e pouco "
    "atualizado: as datas e horários exatos não são confiáveis. Consulte sempre o site "
    "oficial de cada evento antes de confirmar e trate estas sugestões apenas como ideias "
    "para o itinerário, não como compromissos fixos."
)

_extraction_llm = ChatGroq(model="llama-3.1-8b-instant")


class _ExtractedAttractions(BaseModel):
    attractions: list[TouristAttraction] = Field(default_factory=list)


class _ExtractedEvents(BaseModel):
    events: list[TraditionalEvent] = Field(default_factory=list)


class TouristAttractionSearchResult(BaseModel):
    destination: str
    source_url: str | None
    found: bool
    attractions: list[TouristAttraction] = Field(default_factory=list)


class EventSearchResult(BaseModel):
    destination: str
    source_url: str | None
    found: bool
    events: list[TraditionalEvent] = Field(default_factory=list)
    disclaimer: str = EVENT_DATES_DISCLAIMER


def _fetch_wikipedia_page(title: str) -> tuple[str, str] | None:
    """Busca uma página da Wikipédia em inglês pelo título e retorna
    (texto_da_pagina, url), ou None se a página não existir."""
    url = f"{WIKIPEDIA_BASE_URL}/{quote(title.replace(' ', '_'))}"
    response = requests.get(url, headers=_REQUEST_HEADERS, timeout=10)
    if response.status_code == 404:
        return None
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.select_one("#mw-content-text")
    if content is None:
        return None

    paragraphs = [element.get_text(" ", strip=True) for element in content.find_all(["p", "li"])]
    page_text = "\n".join(paragraph for paragraph in paragraphs if paragraph)
    if not page_text:
        return None
    return page_text, url


def _extract_attractions(destination: str, page_text: str) -> list[TouristAttraction]:
    """Usa o LLM para extrair uma lista estruturada de pontos turísticos a
    partir do texto de uma página da Wikipédia."""
    prompt = ATTRACTION_EXTRACTION_PROMPT.format(
        destination=destination,
        page_text=page_text[:_MAX_PAGE_TEXT_CHARS],
    )
    structured_llm = _extraction_llm.with_structured_output(_ExtractedAttractions)
    result = structured_llm.invoke(prompt)

    seen_names: set[str] = set()
    unique_attractions = []
    for attraction in result.attractions:
        key = attraction.name.strip().lower()
        if key not in seen_names:
            seen_names.add(key)
            unique_attractions.append(attraction)
    return unique_attractions


def _extract_events(destination: str, page_text: str, period: str | None) -> list[TraditionalEvent]:
    """Usa o LLM para extrair uma lista estruturada de eventos/festivais
    tradicionais a partir do texto de uma página da Wikipédia."""
    period_context = (
        f'O usuário pretende viajar em: "{period}". Se a descrição de um evento '
        "mencionar explicitamente uma época/período do ano, deixe claro se ela "
        "coincide com esse período informado pelo usuário. Não exclua eventos "
        "cuja época não esteja explícita no texto nem estime se eles coincidem."
        if period
        else "O usuário não informou o período da viagem."
    )
    prompt = EVENT_EXTRACTION_PROMPT.format(
        destination=destination,
        page_text=page_text[:_MAX_PAGE_TEXT_CHARS],
        period_context=period_context,
    )
    structured_llm = _extraction_llm.with_structured_output(_ExtractedEvents)
    result = structured_llm.invoke(prompt)

    seen_names: set[str] = set()
    unique_events = []
    for event in result.events:
        key = event.name.strip().lower()
        if key not in seen_names:
            seen_names.add(key)
            unique_events.append(event)
    return unique_events


def search_tourist_attractions(destination: str) -> TouristAttractionSearchResult:
    """Busca pontos turísticos de um destino de viagem na Wikipédia.

    Tenta primeiro a página "Tourism in <destination>"; se ela não existir,
    tenta a página padrão do destino. Retorna os pontos turísticos
    encontrados, ou found=False caso nenhuma página exista ou nada relevante
    seja encontrado.
    """
    for title in (f"Tourism in {destination}", destination):
        fetched = _fetch_wikipedia_page(title)
        if fetched is None:
            continue
        page_text, url = fetched
        attractions = _extract_attractions(destination, page_text)
        if attractions:
            return TouristAttractionSearchResult(
                destination=destination,
                source_url=url,
                found=True,
                attractions=attractions,
            )

    return TouristAttractionSearchResult(
        destination=destination,
        source_url=None,
        found=False,
        attractions=[],
    )


def search_events_and_festivals(destination: str, period: str | None = None) -> EventSearchResult:
    """Busca eventos e festivais tradicionais de um destino de viagem na
    Wikipédia.

    Tenta, em ordem, as páginas "Festivals in <destination>" e "Culture of
    <destination>"; se nenhuma existir, tenta a página padrão do destino.
    `period` é opcional e descreve o período de férias informado pelo
    usuário (ex.: "outubro", "última semana de julho"); quando informado, é
    usado apenas como contexto para a extração — nunca para descartar
    eventos, já que a Wikipédia não traz datas confiáveis o suficiente para
    estimar se um evento coincide com o período. Como a Wikipédia é um texto
    estático e pouco atualizado, o resultado sempre traz um aviso
    (`disclaimer`) para o usuário confirmar dia e horário no site oficial de
    cada evento antes de incluí-lo no itinerário. Retorna found=False caso
    nenhuma página exista ou nada relevante seja encontrado.
    """
    for title in (f"Festivals in {destination}", f"Culture of {destination}", destination):
        fetched = _fetch_wikipedia_page(title)
        if fetched is None:
            continue
        page_text, url = fetched
        events = _extract_events(destination, page_text, period)
        if events:
            return EventSearchResult(
                destination=destination,
                source_url=url,
                found=True,
                events=events,
            )

    return EventSearchResult(
        destination=destination,
        source_url=None,
        found=False,
        events=[],
    )
