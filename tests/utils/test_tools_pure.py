"""Testes das funções puras / determinísticas de `itinerai_agent/utils/tools.py`
(agrupamento por proximidade, distribuição por dias, slug, nome de arquivo,
render markdown, extração de JSON)."""

import pytest

from itinerai_agent.utils import tools as T
from itinerai_agent.utils.state import Itinerary, ItineraryDay, TouristAttraction


def attr(name, loc="loc"):
    return TouristAttraction(name=name, description="d", location=loc)


# --- _extract_json_payload ------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"a": 1}', {"a": 1}),
        ("[1, 2, 3]", [1, 2, 3]),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('```\n{"a": 1}\n```', {"a": 1}),
        ('Aqui está: {"a": 1} pronto', {"a": 1}),
        ("nada de json aqui", None),
        ("", None),
    ],
)
def test_extract_json_payload(text, expected):
    assert T._extract_json_payload(text) == expected


# --- _dominant_area -----------------------------------------------------

def test_dominant_area_majority():
    placements = [
        (attr("a"), "Centro", False),
        (attr("b"), "Centro", False),
        (attr("c"), "Norte", False),
    ]
    assert T._dominant_area(placements) == "Centro"


def test_dominant_area_empty():
    assert T._dominant_area([(attr("a"), "", False)]) == ""


def test_dominant_area_tie_keeps_first_seen():
    placements = [(attr("a"), "A", False), (attr("b"), "B", False)]
    assert T._dominant_area(placements) == "A"


# --- _distribute_across_days -------------------------------------------

def test_distribute_zero_attractions():
    days, note = T._distribute_across_days([], 3)
    assert [d.day for d in days] == [1, 2, 3]
    assert all(d.attractions == [] and d.area == "" for d in days)
    assert note == "Não encontramos atrações para montar o roteiro deste destino."


def test_distribute_few_for_many_days_revisits():
    clustered = [(attr("A"), "X"), (attr("B"), "Y")]
    days, note = T._distribute_across_days(clustered, 5)
    assert [d.attractions for d in days] == [
        ["A"],
        ["B"],
        ["A (revisita)"],
        ["B (revisita)"],
        ["A (revisita)"],
    ]
    assert note == f"{T.ITINERARY_RELAXED_NOTE} {T.ITINERARY_REVISIT_NOTE}"


def test_distribute_overflow_caps_at_3_and_notes():
    clustered = [(attr(f"A{i}"), "Z") for i in range(7)]
    days, note = T._distribute_across_days(clustered, 2)
    assert [len(d.attractions) for d in days] == [3, 3]
    assert sum(len(d.attractions) for d in days) == 6
    assert note == T.ITINERARY_OVERFLOW_NOTE


def test_distribute_relaxed_note():
    clustered = [(attr(f"A{i}"), "Z") for i in range(4)]
    days, note = T._distribute_across_days(clustered, 3)
    assert [len(d.attractions) for d in days] == [2, 1, 1]
    assert note == T.ITINERARY_RELAXED_NOTE


def test_distribute_even_no_note():
    clustered = [(attr(f"A{i}"), "Z") for i in range(6)]
    days, note = T._distribute_across_days(clustered, 2)
    assert [len(d.attractions) for d in days] == [3, 3]
    assert note is None


def test_distribute_num_days_floor_1():
    days, _ = T._distribute_across_days([(attr("A"), "Z"), (attr("B"), "Z")], 0)
    assert len(days) == 1
    assert len(days[0].attractions) == 2


# --- assemble_itinerary ----------------------------------------------

def test_assemble_no_attractions():
    it = T.assemble_itinerary("Lisboa", 2, [])
    assert it.num_days == 2
    assert len(it.days) == 2
    assert it.note == "Não encontramos atrações para montar o roteiro deste destino."


def test_assemble_single_attraction_no_llm():
    it = T.assemble_itinerary("Lisboa", 1, [attr("A", "Centro")])
    assert it.days[0].attractions == ["A"]


def test_assemble_multi_attraction_llm_down(monkeypatch):
    monkeypatch.setattr(T, "_invoke_structured", lambda schema, prompt: None)
    it = T.assemble_itinerary("Lisboa", 2, [attr("A"), attr("B"), attr("C")])
    assert it.note == T.ITINERARY_RELAXED_NOTE
    assert [len(d.attractions) for d in it.days] == [2, 1]


# --- render_itinerary_markdown -------------------------------------

def test_render_singular_day_word():
    it = Itinerary(
        destination="Lisboa",
        num_days=1,
        days=[ItineraryDay(day=1, area="Centro", attractions=["Castelo"])],
    )
    out = T.render_itinerary_markdown(it)
    assert out.startswith("# Roteiro de viagem — Lisboa\n")
    assert "*1 dia de viagem*" in out
    assert "## Dia 1 — Centro" in out
    assert "- Castelo" in out
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


def test_render_plural_day_word():
    it = Itinerary(destination="Roma", num_days=3, days=[ItineraryDay(day=1)])
    assert "*3 dias de viagem*" in T.render_itinerary_markdown(it)


def test_render_note_line():
    it = Itinerary(
        destination="X", num_days=2, days=[ItineraryDay(day=1)], note="Atenção"
    )
    assert "> Atenção" in T.render_itinerary_markdown(it)


def test_render_day_without_area():
    it = Itinerary(destination="X", num_days=1, days=[ItineraryDay(day=2)])
    out = T.render_itinerary_markdown(it)
    assert "## Dia 2" in out
    assert "## Dia 2 — " not in out


def test_render_empty_day():
    it = Itinerary(
        destination="X", num_days=1, days=[ItineraryDay(day=2, attractions=[])]
    )
    assert "_Dia livre para descansar ou explorar por conta própria._" in (
        T.render_itinerary_markdown(it)
    )


# --- _slugify / _itinerary_file_stem -------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("São Paulo", "sao-paulo"),
        ("Rio de Janeiro", "rio-de-janeiro"),
        ("日本", "destino"),
        ("!!!", "destino"),
    ],
)
def test_slugify(text, expected):
    assert T._slugify(text) == expected


def test_file_stem_plural():
    assert T._itinerary_file_stem("Lisboa", 3) == "itinerario-lisboa-3-dias"


def test_file_stem_singular():
    assert T._itinerary_file_stem("São Paulo", 1) == "itinerario-sao-paulo-1-dia"


# --- _resolve_output_path -----------------------------------------

def test_resolve_first_file(tmp_path):
    out_dir = tmp_path / "out"
    assert T._resolve_output_path("foo", output_dir=out_dir) == out_dir / "foo.md"
    assert out_dir.is_dir()


def test_resolve_sequential_suffix(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "foo.md").write_text("x", encoding="utf-8")
    assert T._resolve_output_path("foo", output_dir=out_dir) == out_dir / "foo (2).md"
    (out_dir / "foo (2).md").write_text("x", encoding="utf-8")
    assert T._resolve_output_path("foo", output_dir=out_dir) == out_dir / "foo (3).md"


# --- build_itinerary (OUTPUT_DIR redirecionado pela fixture autouse) -

def test_build_itinerary_writes_md(tmp_path):
    res = T.build_itinerary("Lisboa", 1, [attr("A", "Centro")])
    assert res.file_name == "itinerario-lisboa-1-dia.md"
    assert res.message == (
        "O arquivo itinerario-lisboa-1-dia.md com o itinerário "
        "para seu destino foi criado em output/"
    )
    written = (tmp_path / "output" / "itinerario-lisboa-1-dia.md").read_text(
        encoding="utf-8"
    )
    assert written.startswith("# Roteiro de viagem — Lisboa")
    assert res.itinerary.destination == "Lisboa"


def test_build_itinerary_num_days_floor():
    assert T.build_itinerary("Lisboa", 0, None).num_days == 1


def test_build_itinerary_sequential_file():
    T.build_itinerary("Lisboa", 1, [attr("A")])
    res = T.build_itinerary("Lisboa", 1, [attr("A")])
    assert res.file_name == "itinerario-lisboa-1-dia (2).md"


# --- _cluster_by_proximity ---------------------------------------

def test_cluster_empty():
    assert T._cluster_by_proximity("X", []) == []


def test_cluster_single_no_llm():
    a = attr("A", "Centro")
    assert T._cluster_by_proximity("X", [a]) == [(a, "Centro")]


def test_cluster_llm_down_keeps_order(monkeypatch):
    monkeypatch.setattr(T, "_invoke_structured", lambda schema, prompt: None)
    a, b = attr("A", "L1"), attr("B", "L2")
    assert T._cluster_by_proximity("X", [a, b]) == [(a, "L1"), (b, "L2")]


def test_cluster_llm_orders_and_backfills(monkeypatch):
    clustered = T._ClusteredAttractions(
        attractions=[
            T._ClusteredAttraction(name="B", area="Zona Sul"),
            T._ClusteredAttraction(name="ghost", area="X"),
            T._ClusteredAttraction(name="B", area="dup"),
        ]
    )
    monkeypatch.setattr(T, "_invoke_structured", lambda schema, prompt: clustered)
    a, b = attr("A", "LA"), attr("B", "LB")
    assert T._cluster_by_proximity("X", [a, b]) == [(b, "Zona Sul"), (a, "LA")]


def test_cluster_area_fallback_to_location(monkeypatch):
    clustered = T._ClusteredAttractions(
        attractions=[T._ClusteredAttraction(name="A", area="")]
    )
    monkeypatch.setattr(T, "_invoke_structured", lambda schema, prompt: clustered)
    a, b = attr("A", "Centro"), attr("B", "Norte")
    result = T._cluster_by_proximity("X", [a, b])
    assert result[0] == (a, "Centro")
