"""C2 — fluxo principal ponta a ponta: destino + duração → busca → roteiro →
arquivo `.md` gravado em disco (T08/#19, §4.1/§4.7).

Funciona também como teste de ACEITAÇÃO: as asserções são as regras de produto
do `CLAUDE.md` — o padrão do nome do arquivo, o teto de 3 atrações por dia, o
agrupamento por proximidade e, sobretudo, o fato de o roteiro **não** ser
exibido no terminal.

Só o LLM e o HTTP da Wikipédia são dublados. Os nós, as arestas condicionais, o
fan-out/fan-in, o reducer de `page_results`, as tools e a escrita do arquivo
rodam de verdade.
"""

from langchain_core.messages import AIMessage, ToolMessage

from itinerai_agent.utils import audit, tools
from itinerai_agent.utils.state import TouristAttraction

from .conftest import wikipedia_html

# Duas atrações por área, em três áreas: com 3 dias de viagem o agrupamento por
# proximidade deve render um dia por área.
ATRACOES = [
    TouristAttraction(
        name="Torre de Belém",
        description="Fortaleza manuelina do século XVI à beira do Tejo.",
        location="Belém",
    ),
    TouristAttraction(
        name="Mosteiro dos Jerónimos",
        description="Mosteiro manuelino classificado como Património Mundial.",
        location="Belém",
    ),
    TouristAttraction(
        name="Castelo de São Jorge",
        description="Castelo mouro com vista para toda a cidade.",
        location="Alfama",
    ),
    TouristAttraction(
        name="Sé de Lisboa",
        description="Catedral românica, a igreja mais antiga da cidade.",
        location="Alfama",
    ),
    TouristAttraction(
        name="Elevador de Santa Justa",
        description="Elevador de ferro do início do século XX.",
        location="Baixa",
    ),
    TouristAttraction(
        name="Praça do Comércio",
        description="Praça ribeirinha da Baixa Pombalina.",
        location="Baixa",
    ),
]

PAGINA_TURISMO = wikipedia_html(
    "Lisboa é a capital de Portugal e o seu principal destino turístico.",
    "A cidade reúne monumentos manuelinos, miradouros e bairros históricos.",
)

RESPOSTA_FINAL = "Pronto! Criei o arquivo com o seu roteiro na pasta output/."

ARQUIVO_ESPERADO = "itinerario-lisboa-3-dias.md"


def _search_call(call_id: str = "search-1") -> dict:
    return {
        "name": "search_tourist_attractions",
        "args": {"destination": "Lisboa"},
        "id": call_id,
        "type": "tool_call",
    }


def _build_call(call_id: str = "build-1") -> dict:
    return {
        "name": "build_itinerary",
        "args": {"destination": "Lisboa", "num_days": 3},
        "id": call_id,
        "type": "tool_call",
    }


def _roteiro_do_llm() -> tuple[AIMessage, ...]:
    """As três respostas do LLM, uma por passagem em `call_llm`: pede a busca,
    pede a montagem do roteiro e encerra com uma resposta sem tool call — que é
    a condição de parada de `route_after_llm`."""
    return (
        AIMessage(content="", tool_calls=[_search_call()]),
        AIMessage(content="", tool_calls=[_build_call()]),
        AIMessage(content=RESPOSTA_FINAL),
    )


def _rodar_fluxo(scripted_llm, fake_wikipedia, fake_extraction, run_graph, run_id):
    """Instala os duplos e roda um turno completo do fluxo principal.

    Só a página `Tourism in Lisboa` existe; a página `Lisboa` devolve 404, para
    que a preferência de `merge_pages` pela página de turismo seja verificável."""
    llm = scripted_llm(*_roteiro_do_llm())
    wikipedia = fake_wikipedia({"Tourism_in_Lisboa": PAGINA_TURISMO})
    fake_extraction(ATRACOES)

    state = run_graph("Quero viajar para Lisboa por 3 dias", run_id=run_id)
    return state, llm, wikipedia


def test_fluxo_principal_gera_o_arquivo_do_roteiro(
    scripted_llm, fake_wikipedia, fake_extraction, run_graph
):
    state, llm, _wikipedia = _rodar_fluxo(
        scripted_llm, fake_wikipedia, fake_extraction, run_graph, "e2e-fluxo-principal"
    )

    # --- o artefato que o usuário veio buscar --------------------------------
    arquivo = tools.OUTPUT_DIR / ARQUIVO_ESPERADO
    assert arquivo.exists()
    conteudo = arquivo.read_text(encoding="utf-8")
    assert conteudo.count("## Dia ") == 3
    assert "Torre de Belém" in conteudo

    # --- regras de produto do CLAUDE.md --------------------------------------
    assert state.destination == "Lisboa"
    assert state.itinerary is not None
    assert state.itinerary.num_days == 3
    assert len(state.itinerary.days) == 3
    # Teto de 3 atrações por dia.
    assert all(len(dia.attractions) <= 3 for dia in state.itinerary.days)
    # Agrupamento por proximidade: um dia por área, na ordem das atrações.
    assert [dia.area for dia in state.itinerary.days] == ["Belém", "Alfama", "Baixa"]

    # O roteiro fica NO ARQUIVO: o terminal recebe apenas o aviso.
    assert state.messages[-1].content == RESPOSTA_FINAL
    assert "## Dia" not in state.messages[-1].content
    # Condição de parada: a última mensagem não pede mais nenhuma tool.
    assert not getattr(state.messages[-1], "tool_calls", None)

    # Um roteiro novo reabre a oferta de envio por e-mail (T14/#25).
    assert state.notification is None
    assert llm.call_count == 3


def test_fluxo_principal_percorre_o_fan_out_e_deixa_trilha(
    scripted_llm, fake_wikipedia, fake_extraction, run_graph
):
    """Asserções de TOPOLOGIA: é o que os testes unitários não alcançam, porque
    cada peça isolada passa mesmo com a montagem errada."""
    state, _llm, wikipedia = _rodar_fluxo(
        scripted_llm, fake_wikipedia, fake_extraction, run_graph, "e2e-fan-out"
    )

    # Os dois ramos do fan-out rodaram — é a paralelização exigida pelo §4.2.
    assert wikipedia.requested("Tourism_in_Lisboa")
    assert wikipedia.requested("/Lisboa")

    # O reducer `_merge_page_results` foi aplicado no fan-in: uma chave por ramo.
    assert set(state.page_results) == {"tourism", "destination"}
    assert state.page_results["tourism"].attractions
    assert state.page_results["destination"].found is False
    # `merge_pages` escolheu a página de turismo (a que rendeu atrações).
    assert state.tourist_attractions == ATRACOES

    # Nenhuma tool call fica sem resposta: toda `AIMessage` com tool call tem a
    # `ToolMessage` correspondente. É o defeito que
    # `_drop_premature_build_itinerary` previne e que só aparece na sequência
    # completa — isoladamente, cada nó devolve a mensagem certa.
    ids_pedidos = {
        call["id"]
        for message in state.messages
        for call in getattr(message, "tool_calls", None) or []
    }
    ids_respondidos = {
        message.tool_call_id
        for message in state.messages
        if isinstance(message, ToolMessage)
    }
    assert ids_pedidos == ids_respondidos

    # Trilha de auditoria (T05/#16) do mesmo run_id: os nós do fan-out e a tool.
    trilha = {(s.step, s.step_type) for s in audit.load_audit_trail("e2e-fan-out")}
    assert {
        ("dispatch_search", "node"),
        ("fetch_tourism_page", "node"),
        ("fetch_destination_page", "node"),
        ("merge_pages", "node"),
        ("build_itinerary", "tool"),
    } <= trilha


def test_segundo_roteiro_ganha_sufixo_sequencial(
    scripted_llm, fake_wikipedia, fake_extraction, run_graph
):
    """Regra de nomeação de `_resolve_output_path`, ponta a ponta: um roteiro
    novo para o mesmo destino e duração não sobrescreve o anterior."""
    _rodar_fluxo(
        scripted_llm, fake_wikipedia, fake_extraction, run_graph, "e2e-arquivo-1"
    )
    _rodar_fluxo(
        scripted_llm, fake_wikipedia, fake_extraction, run_graph, "e2e-arquivo-2"
    )

    assert (tools.OUTPUT_DIR / ARQUIVO_ESPERADO).exists()
    assert (tools.OUTPUT_DIR / "itinerario-lisboa-3-dias (2).md").exists()
