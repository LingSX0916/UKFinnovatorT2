"""Risk engine — each factor, the precedence, and the cite-everything rule."""
from backend.kyb import risk


def _red_match(**kw):
    base = {"list": "UK_SANCTIONS", "verdict": "RED", "subject_name": "Ivan Petrov",
            "subject_type": "psc", "matched_designation_id": "RUS0001",
            "matched_name": "IVAN PETROV", "regime_name": "Russia",
            "matched_fields": {"name_score": 0.97}}
    base.update(kw)
    return base


def _live_psc():
    return [{"kind": "individual", "name": "Jane", "ceased_on": None}]


def test_sanctions_match_is_red():
    r = risk.assess_risk(company_number="1", pscs=_live_psc(), screening_matches=[_red_match()])
    assert r["overall_rating"] == "RED"
    assert r["sanctions_hit"] is True
    assert any(f["code"] == "SANCTIONS_MATCH" and f["triggered"] for f in r["factors"])


def test_ownership_and_control_red():
    r = risk.assess_risk(company_number="1", pscs=_live_psc(),
                         sanctioned_controllers=[{"name": "Ivan", "designation_id": "RUS9",
                                                  "ownership_band": "75-100%", "effective_pct": 80}])
    assert r["overall_rating"] == "RED"
    assert any(f["code"] == "OWNERSHIP_AND_CONTROL" and f["triggered"] for f in r["factors"])


def test_warning_list_red():
    r = risk.assess_risk(company_number="1", pscs=_live_psc(), warning_hits=["BadCo Ltd"])
    assert r["overall_rating"] == "RED"
    assert r["warning_list_hit"] is True


def test_high_risk_jurisdiction_amber():
    r = risk.assess_risk(company_number="1", pscs=_live_psc(),
                         company={"registered_office": {"country": "Iran"}})
    assert r["overall_rating"] == "AMBER"
    assert any(f["code"] == "HIGH_RISK_JURISDICTION" and f["triggered"] for f in r["factors"])


def test_opacity_when_no_psc():
    r = risk.assess_risk(company_number="1", pscs=[])
    assert any(f["code"] == "BENEFICIAL_OWNERSHIP_OPACITY" and f["triggered"] for f in r["factors"])


def test_clean_company_is_green():
    r = risk.assess_risk(company_number="1", pscs=_live_psc(),
                         company={"registered_office": {"country": "United Kingdom"}},
                         ownership={"max_depth": 1})
    assert r["overall_rating"] == "GREEN"


def test_red_precedence_over_amber():
    r = risk.assess_risk(company_number="1", pscs=[],
                         company={"registered_office": {"country": "Iran"}},
                         screening_matches=[_red_match()])
    assert r["overall_rating"] == "RED"  # RED factor wins regardless of AMBER count


def test_country_classification():
    assert risk.classify_country("DPRK")[0] == "North Korea"
    assert risk.classify_country("Burma")[0] == "Myanmar"
    assert risk.classify_country("Iran")[1] == "call_for_action"
    assert risk.classify_country("United Kingdom") is None


def test_warning_amber_near_match_is_amber_not_red():
    # a clone-style AMBER Warning List near-match must NOT force overall RED
    r = risk.assess_risk(company_number="1", pscs=_live_psc(), screening_matches=[{
        "list": "FCA_WARNING", "verdict": "AMBER", "subject_name": "Quantum Yield Capitol",
        "subject_type": "company", "matched_name": "Quantum Yield Capital Ltd", "score": 0.95}])
    assert r["overall_rating"] == "AMBER"
    codes = [f["code"] for f in r["factors"] if f["triggered"]]
    assert "WARNING_LIST_POSSIBLE" in codes
    assert "WARNING_LIST_MATCH" not in codes


def test_dismissed_red_match_drops_the_rating():
    dismissed = _red_match(decision="dismissed")
    r = risk.assess_risk(company_number="1", pscs=_live_psc(), screening_matches=[dismissed],
                         company={"registered_office": {"country": "United Kingdom"}},
                         ownership={"max_depth": 1})
    assert r["overall_rating"] == "GREEN"  # a dismissed false positive no longer reds


def test_every_factor_cites_a_provision():
    r = risk.assess_risk(company_number="1", pscs=[], screening_matches=[_red_match()],
                         company={"registered_office": {"country": "Iran"}})
    for f in r["factors"]:
        assert f["provision"], f"factor {f['code']} has no provision"
    assert r["citations"]
