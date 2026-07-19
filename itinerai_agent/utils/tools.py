"""Tools do agente ItinerAI (busca de pontos turísticos, busca de eventos,
escrita do itinerário .md)."""

from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from itinerai_agent.utils.prompts import ATTRACTION_EXTRACTION_PROMPT
from itinerai_agent.utils.state import TouristAttraction

WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki"
_REQUEST_HEADERS = {"User-Agent": "ItinerAI/1.0 (https://github.com/joaopuel/mini-projeto-ItinerAI)"}
_MAX_PAGE_TEXT_CHARS = 8000

_extraction_llm = ChatGroq(model="llama-3.1-8b-instant")


class _ExtractedAttractions(BaseModel):
    attractions: list[TouristAttraction] = Field(default_factory=list)


class TouristAttractionSearchResult(BaseModel):
    destination: str
    source_url: str | None
    found: bool
    attractions: list[TouristAttraction] = Field(default_factory=list)


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
