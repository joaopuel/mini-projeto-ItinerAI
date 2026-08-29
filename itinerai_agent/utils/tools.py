"""Tools do agente ItinerAI (busca de pontos turísticos e escrita do
itinerário .md)."""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import InjectedToolArg
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from itinerai_agent.utils.prompts import (
    ATTRACTION_EXTRACTION_PROMPT,
    ITINERARY_CLUSTERING_PROMPT,
)
from itinerai_agent.utils.state import (
    Itinerary,
    ItineraryDay,
    TouristAttraction,
    WikipediaPageResult,
)

WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki"
_REQUEST_HEADERS = {"User-Agent": "ItinerAI/1.0 (https://github.com/joaopuel/mini-projeto-ItinerAI)"}
_MAX_PAGE_TEXT_CHARS = 8000

MAX_ATTRACTIONS_PER_DAY = 3

ITINERARY_RELAXED_NOTE = (
    "Aproveite cada detalhe, há tempo suficiente para aproveitar as atrações nas suas férias."
)
ITINERARY_REVISIT_NOTE = (
    "Como há poucas atrações para tantos dias, sugerimos revisitar alguns lugares para "
    "curtir ainda mais os detalhes deles."
)
ITINERARY_OVERFLOW_NOTE = (
    "Havia mais atrações do que cabe na duração informada; priorizamos as principais em "
    "cada dia."
)

# Pasta onde os itinerários .md são gravados. Resolvida a partir da raiz do
# projeto (não do cwd), para funcionar de qualquer diretório de execução.
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"

# temperature=0 deixa a extração determinística e reduz muito o risco de o
# modelo entrar em loop de repetição e gerar um JSON malformado.
_extraction_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)


def _extract_json_payload(text: str) -> dict | list | None:
    """Extrai o primeiro objeto/array JSON de um texto. Tolera cercas de código
    (```json ... ```) e texto antes/depois do JSON."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _invoke_structured(schema: type[BaseModel], prompt: str) -> BaseModel | None:
    """Pede uma resposta JSON ao LLM de extração e valida contra `schema`.

    **Não** usa `ChatGroq.with_structured_output`: com o `openai/gpt-oss-120b`
    na Groq esse método força `tool_choice` e o modelo devolve o JSON como
    texto (não como tool call), o que a Groq rejeita com `tool_use_failed`
    ("model did not call a tool"). Aqui o formato do JSON é pedido no próprio
    prompt e a resposta é extraída do texto.

    Retorna `None` em qualquer falha (rede, JSON inválido/truncado, schema que
    não bate) — as tools degradam tratando como "nada encontrado" em vez de
    derrubar o agente.
    """
    try:
        response = _extraction_llm.invoke(prompt)
    except Exception:
        return None
    content = response.content if isinstance(response.content, str) else ""
    payload = _extract_json_payload(content)
    if payload is None:
        return None
    # O gpt-oss às vezes devolve só a lista, sem o objeto que a envolve.
    if isinstance(payload, list):
        field_names = list(schema.model_fields)
        if len(field_names) == 1:
            payload = {field_names[0]: payload}
    try:
        return schema.model_validate(payload)
    except Exception:
        return None


class _ExtractedAttractions(BaseModel):
    attractions: list[TouristAttraction] = Field(default_factory=list)


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


def fetch_page_attractions(
    title: str, destination: str, kind: Literal["tourism", "destination"]
) -> WikipediaPageResult:
    """Baixa uma página da Wikipédia e extrai suas atrações — a unidade de
    trabalho de cada ramo do fan-out da busca no grafo
    (`fetch_tourism_page` / `fetch_destination_page`).

    Determinística no fluxo de controle: em 404, página sem conteúdo ou
    falha de rede, devolve `found=False` (o outro ramo serve de fallback).
    A guarda de `Exception` só previne regressão — a política de resiliência
    (timeout/retry/backoff/log) é escopo da tarefa T02/#13.
    """
    try:
        fetched = _fetch_wikipedia_page(title)
    except Exception:
        return WikipediaPageResult(kind=kind, found=False)
    if fetched is None:
        return WikipediaPageResult(kind=kind, found=False)
    page_text, url = fetched
    attractions = _extract_attractions(destination, page_text)
    return WikipediaPageResult(
        kind=kind,
        found=bool(attractions),
        source_url=url,
        attractions=attractions,
    )


def search_tourist_attractions(destination: str) -> TouristAttractionSearchResult:
    """Busca pontos turísticos de um destino de viagem na Wikipédia.

    Tenta primeiro a página "Tourism in <destination>"; se ela não existir
    ou não render atrações, tenta a página padrão do destino. Retorna os
    pontos turísticos encontrados, ou found=False caso nenhuma página exista
    ou nada relevante seja encontrado.

    No grafo esta busca roda como um fan-out/fan-in paralelo
    (`fetch_tourism_page` ∥ `fetch_destination_page` → `merge_pages`); esta
    função é a especificação sequencial equivalente, mantida para referência
    e usada pelo `bind_tools` para montar o schema da ferramenta.
    """
    candidates: tuple[tuple[str, Literal["tourism", "destination"]], ...] = (
        (f"Tourism in {destination}", "tourism"),
        (destination, "destination"),
    )
    for title, kind in candidates:
        result = fetch_page_attractions(title, destination, kind)
        if result.attractions:
            return TouristAttractionSearchResult(
                destination=destination,
                source_url=result.source_url,
                found=True,
                attractions=result.attractions,
            )

    return TouristAttractionSearchResult(
        destination=destination,
        source_url=None,
        found=False,
        attractions=[],
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

    Regras: no máximo 3 atrações por dia; atrações próximas caem no mesmo dia;
    se houver poucas atrações para a duração, adiciona uma observação e, em
    último caso, repete lugares (revisitas) para não deixar nenhum dia vazio.
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
        names = [
            f"{attraction.name} (revisita)" if is_revisit else attraction.name
            for attraction, _area, is_revisit in day_placements
        ]
        days.append(
            ItineraryDay(
                day=day_index + 1, area=_dominant_area(day_placements), attractions=names
            )
        )
    return days, note


def assemble_itinerary(
    destination: str,
    num_days: int,
    attractions: list[TouristAttraction] | None = None,
) -> Itinerary:
    """Monta o modelo `Itinerary` dia a dia a partir das atrações.

    Função pura (sem I/O de arquivo): agrupa as atrações por proximidade e
    divide-as pelos `num_days` dias (no máximo 3 por dia). É o núcleo
    testável usado por `build_itinerary`.
    """
    attractions = attractions or []
    num_days = max(1, int(num_days))

    clustered = _cluster_by_proximity(destination, attractions)
    days, note = _distribute_across_days(clustered, num_days)

    return Itinerary(
        destination=destination,
        num_days=num_days,
        days=days,
        note=note,
    )


def render_itinerary_markdown(itinerary: Itinerary) -> str:
    """Renderiza um `Itinerary` como texto markdown para o arquivo .md.

    Função pura: produz título, observação (quando houver) e os dias com suas
    atrações. Todo o conteúdo em português.
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
        if day.attractions:
            lines += [f"- {name}" for name in day.attractions]
            lines.append("")
        else:
            lines += ["_Dia livre para descansar ou explorar por conta própria._", ""]

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
) -> ItineraryFileResult:
    """Monta o itinerário da viagem e grava um arquivo .md em `output/`.

    Forneça apenas `destination` e `num_days` (número inteiro de dias). As
    atrações já encontradas pela busca são fornecidas automaticamente — NÃO as
    repasse.

    As atrações são agrupadas por proximidade e divididas pelos `num_days`
    dias (no máximo 3 por dia). O arquivo é nomeado a partir do destino e da
    duração; se já existir um com o mesmo nome, ganha um número sequencial.
    Retorna a mensagem de confirmação com o nome do arquivo — o itinerário
    completo NÃO é exibido no terminal.

    `attractions` é injetado pelo grafo (a partir do estado) e por isso fica
    oculto do modelo via `InjectedToolArg`.
    """
    num_days = max(1, int(num_days))
    itinerary = assemble_itinerary(destination, num_days, attractions)

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
