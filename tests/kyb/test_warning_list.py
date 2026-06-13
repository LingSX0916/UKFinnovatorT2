"""FCA Warning List screening — firm / domain / individual / clone near-match."""
from backend.kyb.matching import Subject
from backend.kyb.warning_list import WarningList

wl = WarningList()


def test_exact_firm_is_red():
    hits = wl.screen(Subject(name="Quantum Yield Capital Ltd", subject_type="company"))
    assert any(h["verdict"] == "RED" for h in hits)


def test_existing_flat_list_firm():
    # reuses the repo's existing data/warning_list.json (back-compatible)
    assert wl.screen(Subject(name="CoinVault Pro", subject_type="company"))


def test_domain_match():
    hits = wl.screen(Subject(name="Some Co", subject_type="company",
                             identifiers=["https://goldsmith-capital-partners.com/invest"]))
    assert any(h["matched_fields"]["matched_on"] == "domain" for h in hits)


def test_individual_match():
    assert wl.screen(Subject(name="Marcus Delaney", subject_type="individual"))


def test_clone_near_match_is_amber():
    hits = wl.screen(Subject(name="Quantum Yield Capitol Limited", subject_type="company"))
    assert any(h["verdict"] == "AMBER" for h in hits)


def test_clean_miss():
    assert wl.screen(Subject(name="Acme Widgets Ltd", subject_type="company")) == []
