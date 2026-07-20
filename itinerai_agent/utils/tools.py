"""Tools do agente ItinerAI (busca de pontos turísticos, busca de eventos,
escrita do itinerário .md)."""

import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import InjectedToolArg
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from itinerai_agent.utils.prompts import (
    ATTRACTION_EXTRACTION_PROMPT,
    EVENT_EXTRACTION_PROMPT,
    ITINERARY_CLUSTERING_PROMPT,
)
from itinerai_agent.utils.state import (
    Itinerary,
    ItineraryDay,
    ItinerarySlot,
    TouristAttraction,
    TraditionalEvent,
)

WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki"
_REQUEST_HEADERS = {"User-Agent": "ItinerAI/1.0 (https://github.com/joaopuel/mini-projeto-ItinerAI)"}
_MAX_PAGE_TEXT_CHARS = 8000

EVENT_DATES_DISCLAIMER = (
    "As informações de eventos e festivais vêm da Wikipédia, um texto estático e pouco "
    "atualizado: as datas e horários exatos não são confiáveis. Consulte sempre o site "
    "oficial de cada evento antes de confirmar e trate estas sugestões apenas como ideias "
    "para o itinerário, não como compromissos fixos."
)

ITINERARY_SLOTS = ("Manhã", "Tarde", "Noite")
MAX_ATTRACTIONS_PER_SLOT = 3
MAX_ATTRACTIONS_PER_DAY = len(ITINERARY_SLOTS) * MAX_ATTRACTIONS_PER_SLOT

ITINERARY_RELAXED_NOTE = (
    "Aproveite cada detalhe, há tempo suficiente para aproveitar as atrações nas suas férias."
)
ITINERARY_REVISIT_NOTE = (
    "Como há poucas atrações para tantos dias, sugerimos revisitar alguns lugares para "
    "curtir ainda mais os detalhes deles."
)
ITINERARY_OVERFLOW_NOTE = (
    "Havia mais atrações do que cabe no período informado; priorizamos as principais em "
    "cada dia."
)

# Pasta onde os itinerários .md são gravados. Resolvida a partir da raiz do
# projeto (não do cwd), para funcionar de qualquer diretório de execução.
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"

# temperature=0 deixa a extração determinística e reduz muito o risco de o
# modelo entrar em loop de repetição e gerar um tool call malformado.
_extraction_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)


def _invoke_structured(schema: type[BaseModel], prompt: str) -> BaseModel | None:
    """Invoca o LLM de extração pedindo saída estruturada no formato `schema`.

    Retorna `None` se o modelo falhar ao gerar uma resposta válida — por
    exemplo, quando entra em loop de repetição e produz um JSON truncado que a
    Groq rejeita com `tool_use_failed` (HTTP 400). Assim as tools degradam com
    elegância (tratam como "nada encontrado") em vez de derrubar o agente.
    """
    try:
        structured_llm = _extraction_llm.with_structured_output(schema)
        return structured_llm.invoke(prompt)
    except Exception:
        return None


class _ExtractedAttractions(BaseModel):
    attractions: list[TouristAttraction] = Field(default_factory=list)


class _ExtractedEvents(BaseModel):
    events: list[TraditionalEvent] = Field(default_factory=list)


class _ClusteredAttraction(BaseModel):
    name: str
    area: str = ""


class _ClusteredAttractions(BaseModel):
    attractions: list[_ClusteredAttraction] = Field(default_factory=list)


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


class ItineraryFileResult(BaseModel):
    """Resultado da geração do arquivo .md do itinerário. `message` é o aviso
    pronto para o usuário; `itinerary` guarda o roteiro completo (vai para o
    estado, não para o terminal)."""

    destination: str
    num_days: int
    file_name: str
    message: str
    itinerary: Itinerary


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
    result = _invoke_structured(_ExtractedAttractions, prompt)
    if result is None:
        return []

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
    result = _invoke_structured(_ExtractedEvents, prompt)
    if result is None:
        return []

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


def _cluster_by_proximity(
    destination: str, attractions: list[TouristAttraction]
) -> list[tuple[TouristAttraction, str]]:
    """Ordena as atrações agrupando as que ficam próximas, usando o LLM a
    partir do campo `location` de cada uma. Retorna pares (atração, área).

    É resiliente: qualquer atração que o LLM omita entra ao final na ordem
    original, e se a chamada falhar cai de volta na ordem/local originais.
    """
    if not attractions:
        return []
    if len(attractions) == 1:
        only = attractions[0]
        return [(only, only.location)]

    by_name = {attraction.name.strip().lower(): attraction for attraction in attractions}
    listing = "\n".join(
        f"- {attraction.name} (local: {attraction.location or 'não informado'})"
        for attraction in attractions
    )
    prompt = ITINERARY_CLUSTERING_PROMPT.format(destination=destination, attractions=listing)

    result = _invoke_structured(_ClusteredAttractions, prompt)

    ordered: list[tuple[TouristAttraction, str]] = []
    used: set[str] = set()
    if result is not None:
        for item in result.attractions:
            key = item.name.strip().lower()
            attraction = by_name.get(key)
            if attraction is not None and key not in used:
                used.add(key)
                ordered.append((attraction, item.area or attraction.location))

    for attraction in attractions:
        key = attraction.name.strip().lower()
        if key not in used:
            used.add(key)
            ordered.append((attraction, attraction.location))
    return ordered


def _dominant_area(placements: list[tuple[TouristAttraction, str, bool]]) -> str:
    """Retorna a área mais frequente entre as atrações de um dia."""
    areas = [area for _attraction, area, _is_revisit in placements if area]
    if not areas:
        return ""
    return Counter(areas).most_common(1)[0][0]


def _distribute_across_days(
    clustered: list[tuple[TouristAttraction, str]], num_days: int
) -> tuple[list[ItineraryDay], str | None]:
    """Distribui atrações já ordenadas por proximidade entre os dias da
    viagem. Função pura e determinística (sem LLM/rede).

    Regras: no máximo 3 atrações por período (manhã/tarde/noite) e 9 por dia;
    atrações próximas caem no mesmo dia; se houver poucas atrações para a
    duração, adiciona uma observação e, em último caso, repete lugares
    (revisitas) para não deixar nenhum dia vazio.
    """
    num_days = max(1, num_days)
    total = len(clustered)

    if total == 0:
        empty = [ItineraryDay(day=index + 1) for index in range(num_days)]
        return empty, "Não encontramos atrações para montar o roteiro deste destino."

    note: str | None = None
    placements: list[list[tuple[TouristAttraction, str, bool]]] = [[] for _ in range(num_days)]

    if total < num_days:
        # Poucas atrações: uma por dia, repetindo (revisitas) para preencher.
        for day_index in range(num_days):
            attraction, area = clustered[day_index % total]
            placements[day_index].append((attraction, area, day_index >= total))
        note = f"{ITINERARY_RELAXED_NOTE} {ITINERARY_REVISIT_NOTE}"
    else:
        # Divide a lista em blocos contíguos o mais uniforme possível,
        # respeitando o teto por dia.
        base, remainder = divmod(total, num_days)
        index = 0
        for day_index in range(num_days):
            size = min(base + (1 if day_index < remainder else 0), MAX_ATTRACTIONS_PER_DAY)
            for attraction, area in clustered[index : index + size]:
                placements[day_index].append((attraction, area, False))
            index += size
        # Reacomoda o que sobrou (quando algum dia bateu no teto) nos
        # primeiros dias com espaço; se nada couber, sinaliza excesso.
        for attraction, area in clustered[index:]:
            for day_placements in placements:
                if len(day_placements) < MAX_ATTRACTIONS_PER_DAY:
                    day_placements.append((attraction, area, False))
                    break
            else:
                note = ITINERARY_OVERFLOW_NOTE
        if note is None and total < num_days * 2:
            note = ITINERARY_RELAXED_NOTE

    days: list[ItineraryDay] = []
    for day_index, day_placements in enumerate(placements):
        slots: list[ItinerarySlot] = []
        for slot_index, slot_name in enumerate(ITINERARY_SLOTS):
            start = slot_index * MAX_ATTRACTIONS_PER_SLOT
            slot_placements = day_placements[start : start + MAX_ATTRACTIONS_PER_SLOT]
            if slot_placements:
                names = [
                    f"{attraction.name} (revisita)" if is_revisit else attraction.name
                    for attraction, _area, is_revisit in slot_placements
                ]
                slots.append(ItinerarySlot(period=slot_name, attractions=names))
        days.append(
            ItineraryDay(day=day_index + 1, area=_dominant_area(day_placements), slots=slots)
        )
    return days, note


def assemble_itinerary(
    destination: str,
    num_days: int,
    attractions: list[TouristAttraction] | None = None,
    events: list[TraditionalEvent] | None = None,
) -> Itinerary:
    """Monta o modelo `Itinerary` dia a dia a partir das atrações e eventos.

    Função pura (sem I/O de arquivo): agrupa as atrações por proximidade,
    divide-as pelos `num_days` dias (no máximo 3 por período), e adiciona os
    eventos como sugestões sem data fixa. É o núcleo testável usado por
    `build_itinerary`.
    """
    attractions = attractions or []
    events = events or []
    num_days = max(1, int(num_days))

    clustered = _cluster_by_proximity(destination, attractions)
    days, note = _distribute_across_days(clustered, num_days)

    return Itinerary(
        destination=destination,
        num_days=num_days,
        days=days,
        note=note,
        event_suggestions=events,
        disclaimer=EVENT_DATES_DISCLAIMER if events else "",
    )


def render_itinerary_markdown(itinerary: Itinerary) -> str:
    """Renderiza um `Itinerary` como texto markdown para o arquivo .md.

    Função pura: produz título, observação (quando houver), os dias com seus
    períodos e atrações, e a seção de sugestões de eventos/festivais fechando
    com o aviso (disclaimer). Todo o conteúdo em português.
    """
    day_word = "dia" if itinerary.num_days == 1 else "dias"
    lines: list[str] = [
        f"# Roteiro de viagem — {itinerary.destination}",
        "",
        f"*{itinerary.num_days} {day_word} de viagem*",
        "",
    ]

    if itinerary.note:
        lines += [f"> {itinerary.note}", ""]

    for day in itinerary.days:
        header = f"## Dia {day.day}"
        if day.area:
            header += f" — {day.area}"
        lines += [header, ""]
        if day.slots:
            for slot in day.slots:
                lines.append(f"### {slot.period}")
                lines += [f"- {name}" for name in slot.attractions]
                lines.append("")
        else:
            lines += ["_Dia livre para descansar ou explorar por conta própria._", ""]

    if itinerary.event_suggestions:
        lines += ["## Sugestões de eventos e festivais", ""]
        for event in itinerary.event_suggestions:
            local = f" ({event.location})" if event.location else ""
            lines.append(f"- **{event.name}**{local} — {event.description}")
        lines.append("")
        if itinerary.disclaimer:
            lines += [f"> {itinerary.disclaimer}", ""]

    return "\n".join(lines).rstrip() + "\n"


def _slugify(text: str) -> str:
    """Converte um texto em um slug ASCII seguro para nome de arquivo
    (minúsculas, sem acentos, palavras separadas por hífen)."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "destino"


def _itinerary_file_stem(destination: str, num_days: int) -> str:
    """Nome-base (sem extensão) do arquivo do itinerário: destino + dias."""
    day_word = "dia" if num_days == 1 else "dias"
    return f"itinerario-{_slugify(destination)}-{num_days}-{day_word}"


def _resolve_output_path(stem: str, output_dir: Path | None = None) -> Path:
    """Resolve o caminho do arquivo .md em `output_dir`, criando a pasta se
    preciso. Se já existir um arquivo com o mesmo nome, acrescenta um número
    sequencial no padrão do Windows: `stem (2).md`, `stem (3).md`, etc.

    `output_dir` cai para `OUTPUT_DIR` quando omitido (lido em tempo de
    chamada, o que também facilita os testes).
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = output_dir / f"{stem}.md"
    counter = 2
    while candidate.exists():
        candidate = output_dir / f"{stem} ({counter}).md"
        counter += 1
    return candidate


def build_itinerary(
    destination: str,
    num_days: int,
    attractions: Annotated[list[TouristAttraction] | None, InjectedToolArg] = None,
    events: Annotated[list[TraditionalEvent] | None, InjectedToolArg] = None,
) -> ItineraryFileResult:
    """Monta o itinerário da viagem e grava um arquivo .md em `output/`.

    Forneça apenas `destination` e `num_days` (número inteiro de dias). As
    atrações e os eventos já encontrados pelas buscas são fornecidos
    automaticamente — NÃO os repasse.

    As atrações são agrupadas por proximidade e divididas pelos `num_days`
    dias (no máximo 3 por período: manhã, tarde e noite); eventos e festivais
    entram como sugestões sem data fixa. O arquivo é nomeado a partir do
    destino e da duração; se já existir um com o mesmo nome, ganha um número
    sequencial. Retorna a mensagem de confirmação com o nome do arquivo — o
    itinerário completo NÃO é exibido no terminal.

    `attractions`/`events` são injetados pelo grafo (a partir do estado) e por
    isso ficam ocultos do modelo via `InjectedToolArg`.
    """
    num_days = max(1, int(num_days))
    itinerary = assemble_itinerary(destination, num_days, attractions, events)

    markdown = render_itinerary_markdown(itinerary)
    path = _resolve_output_path(_itinerary_file_stem(destination, num_days))
    path.write_text(markdown, encoding="utf-8")

    message = (
        f"O arquivo {path.name} com o itinerário para seu destino foi criado em output/"
    )
    return ItineraryFileResult(
        destination=destination,
        num_days=num_days,
        file_name=path.name,
        message=message,
        itinerary=itinerary,
    )
