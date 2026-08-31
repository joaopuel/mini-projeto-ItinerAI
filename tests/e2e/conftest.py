"""Fixtures dos testes E2E sobre o grafo compilado (T08/#19).

Estes testes exercitam `graph.invoke` de ponta a ponta com apenas DOIS duplos,
ambos na fronteira externa do sistema: o LLM (Groq) e o HTTP da Wikipédia. Todo
o resto roda de verdade — nós, arestas condicionais, fan-out/fan-in, o reducer
de `page_results`, as tools e a escrita do arquivo `.md`.

O `tests/conftest.py` da raiz já injeta a `GROQ_API_KEY` dummy antes de qualquer
import e isola o disco (`MEMORY_DB_PATH`, `AUDIT_DB_PATH`, `OUTPUT_DIR`) num
`tmp_path` por teste; nada disso é repetido aqui.
"""

import types

import pytest
from langchain_core.messages import HumanMessage

from itinerai_agent.agent import graph
from itinerai_agent.utils import nodes as N
from itinerai_agent.utils import tools as T
from itinerai_agent.utils.state import AgentState, TouristAttraction

# --- duplo do LLM do agente -------------------------------------------------


class ScriptedLLM:
    """Duplo de `nodes._llm_with_tools`: devolve uma resposta por passagem em
    `call_llm`, na ordem do roteiro.

    A fila por ordem de chamada é segura AQUI porque `call_llm` é um nó único e
    sequencial do grafo — ao contrário dos ramos do fan-out, que rodam em
    threads (ver `FakeWikipedia`, chaveado por URL).

    `call_count` é a asserção central do cenário adversarial: provar que o LLM
    **não** foi chamado é mais forte do que conferir o texto da recusa.
    """

    def __init__(self, responses=()):
        self._queue = list(responses)
        self.calls: list[object] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def invoke(self, messages):
        # O registro vem ANTES do raise: mesmo uma chamada indevida (fila
        # vazia) precisa aparecer no `call_count`, porque `call_llm` engole a
        # exceção no seu `except Exception` e devolveria a mensagem de fallback.
        self.calls.append(messages)
        if not self._queue:
            raise AssertionError(
                f"LLM chamado {self.call_count}x — mais do que o roteiro previa"
            )
        return self._queue.pop(0)


@pytest.fixture
def scripted_llm(monkeypatch):
    """Instala um `ScriptedLLM` no lugar de `nodes._llm_with_tools`.

    Chamar sem argumentos instala um roteiro VAZIO: qualquer chamada ao LLM
    passa a ser, por si só, a falha do teste."""

    def _install(*responses) -> ScriptedLLM:
        llm = ScriptedLLM(responses)
        monkeypatch.setattr(N, "_llm_with_tools", llm)
        return llm

    return _install


# --- duplo do HTTP da Wikipédia ---------------------------------------------


def _http_response(status: int, text: str = ""):
    """Resposta HTTP falsa, no mesmo formato do helper de
    `tests/utils/test_tools_resilience.py`."""
    return types.SimpleNamespace(
        status_code=status, text=text, raise_for_status=lambda: None
    )


class FakeWikipedia:
    """Duplo de `tools.requests.get` **chaveado pela URL**, nunca pela ordem das
    chamadas.

    Os dois ramos do fan-out (`fetch_tourism_page` ∥ `fetch_destination_page`)
    rodam em threads do `ThreadPoolExecutor` do LangGraph: um
    `Mock(side_effect=[a, b])` dependeria de qual thread chega primeiro e seria
    intermitente. O despacho por URL é determinístico e thread-safe.

    Uma URL sem correspondência vira 404 — que é como `_fetch_wikipedia_page`
    representa "a página não existe" (sem exceção, sem retry).
    """

    def __init__(self, pages: dict[str, str]):
        # Casa por fragmento, na ordem de inserção: registre o título mais
        # específico primeiro ("Tourism_in_Lisboa" antes de "Lisboa").
        self._pages = pages
        self.urls: list[str] = []

    def __call__(self, url, **kwargs):
        self.urls.append(url)
        for fragment, html in self._pages.items():
            if fragment in url:
                return _http_response(200, html)
        return _http_response(404)

    def requested(self, fragment: str) -> bool:
        """Indica se alguma URL pedida contém o fragmento."""
        return any(fragment in url for url in self.urls)


@pytest.fixture
def fake_wikipedia(monkeypatch):
    """Instala um `FakeWikipedia` no lugar de `requests.get` (visto de
    `tools.py`)."""

    def _install(pages: dict[str, str]) -> FakeWikipedia:
        fake = FakeWikipedia(pages)
        monkeypatch.setattr(T.requests, "get", fake)
        return fake

    return _install


def wikipedia_html(*paragraphs: str) -> str:
    """HTML mínimo no formato que `_fetch_wikipedia_page` espera: um
    `#mw-content-text` com parágrafos.

    O conteúdo em si é irrelevante (a extração é dublada); o que este HTML
    exercita é o parsing real com BeautifulSoup."""
    body = "".join(f"<p>{text}</p>" for text in paragraphs)
    return f'<html><body><div id="mw-content-text">{body}</div></body></html>'


# --- duplo da extração estruturada ------------------------------------------


@pytest.fixture
def fake_extraction(monkeypatch):
    """Substitui `tools._invoke_structured` por um despacho pelo `schema`.

    Há DOIS call sites no caminho do fluxo principal, com schemas diferentes:
    `_extract_attractions` (uma vez por ramo do fan-out) e
    `_cluster_by_proximity`, lá dentro de `build_itinerary`. Um duplo de
    resposta única atenderia o primeiro e quebraria o agrupamento por
    proximidade — daí o despacho.

    É uma função pura, portanto segura nas threads do fan-out.
    """

    def _install(attractions: list[TouristAttraction]) -> None:
        def fake_invoke_structured(schema, prompt):
            if schema is T._ExtractedAttractions:
                return schema(attractions=list(attractions))
            if schema is T._ClusteredAttractions:
                # Mantém a ordem dada e usa `location` como área, para o
                # agrupamento por proximidade ficar previsível no roteiro.
                return schema(
                    attractions=[
                        T._ClusteredAttraction(name=item.name, area=item.location)
                        for item in attractions
                    ]
                )
            return None

        monkeypatch.setattr(T, "_invoke_structured", fake_invoke_structured)

    return _install


# --- invocação do grafo -----------------------------------------------------


@pytest.fixture
def run_graph():
    """Roda um turno completo do grafo compilado, como `main.py` faz.

    O `recursion_limit=50` espelha `main.py` (o fan-out consome supersteps
    extras por busca). O `run_id` no estado é o que `_logged_node` publica no
    `ContextVar`, e é o que permite cruzar as asserções com a trilha de
    auditoria (T05/#16)."""

    def _run(user_message: str, run_id: str, **state_fields) -> AgentState:
        state = AgentState(
            run_id=run_id,
            messages=[HumanMessage(content=user_message)],
            **state_fields,
        )
        result = graph.invoke(state, {"recursion_limit": 50})
        return AgentState.model_validate(result)

    return _run
