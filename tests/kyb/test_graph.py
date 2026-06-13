"""UBO ownership graph — band parsing and the OFSI >50% control determination."""
from backend.kyb.graph import parse_natures, build_ownership_graph


class FakeClient:
    """Minimal CH client stub for graph tests (no network, no fixtures)."""
    def __init__(self, pscs):
        self._pscs = pscs

    def get_profile(self, number):
        return {"company_number": number, "name": f"{number} Ltd"}

    def get_pscs(self, number):
        return self._pscs.get(number, [])

    def search_companies(self, query, *, limit=3):
        return []

    def _load_fixture(self, number):
        return None


def test_parse_natures_returns_band_and_control():
    assert parse_natures(["ownership-of-shares-50-to-75-percent"]) == (50, 75, False)
    assert parse_natures(["ownership-of-shares-75-to-100-percent"]) == (75, 100, False)
    assert parse_natures(["right-to-appoint-and-remove-directors"])[2] is True


def test_50_to_75_band_is_a_controller():
    # a CH "50-to-75-percent" PSC owns strictly >50% -> OFSI control must fire
    psc = [{"id": "p1", "name": "Ivan Petrov",
            "kind": "individual-person-with-significant-control",
            "natures_of_control": ["ownership-of-shares-50-to-75-percent"]}]
    g = build_ownership_graph(FakeClient({"X1": psc}), "X1")
    node = next(n for n in g["nodes"] if n["id"] == "p1")
    assert node["is_control"] is True
    assert node["effective_pct"] == 50.0      # conservative lower-edge display
    assert node["effective_pct_max"] == 75.0  # upper edge drove the control test


def test_25_to_50_band_is_not_a_controller():
    psc = [{"id": "p2", "name": "Minor Holder",
            "kind": "individual-person-with-significant-control",
            "natures_of_control": ["ownership-of-shares-25-to-50-percent"]}]
    g = build_ownership_graph(FakeClient({"X2": psc}), "X2")
    node = next(n for n in g["nodes"] if n["id"] == "p2")
    assert node["is_control"] is False  # 25-50% is below the control threshold
