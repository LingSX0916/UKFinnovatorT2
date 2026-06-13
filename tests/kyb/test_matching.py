"""The matching engine is the heart of the product — unit-tested hard, including
the adversarial false-positive guards."""
from backend.kyb.matching import (Subject, _name_score, _token_alignment, _verdict,
                                  RED_NAME_THRESHOLD)


# --- end-to-end against the sample list ---------------------------------------
def test_true_match_red(index):
    s = Subject(name="Mohammad Hassan Akhund", subject_type="individual",
                dob_year=1945, nationalities=["Afghanistan"], ref="o1")
    top = index.screen(s)[0]
    assert top.designation_id == "AFG0006"
    assert top.verdict == "RED"
    assert top.matched_fields["dob"] == "match"


def test_dob_mismatch_downgrades_to_amber(index):
    s = Subject(name="Mohammad Hassan Akhund", subject_type="individual",
                dob_year=1801, nationalities=["Afghanistan"], ref="o2")
    top = index.screen(s)[0]
    assert top.designation_id == "AFG0006"
    assert top.verdict == "AMBER"  # an explicitly conflicting DOB blocks RED


def test_name_only_is_amber(index):
    s = Subject(name="Mohammad Hassan Akhund", subject_type="individual", ref="o3")
    top = index.screen(s)[0]
    assert top.verdict == "AMBER"  # strong name, no corroboration -> AMBER, never RED


def test_transliteration_match(index):
    # diacritics must not defeat the match
    s = Subject(name="Mohámmad Hassán Akhünd", subject_type="individual",
                dob_year=1945, ref="o4")
    ids = [m.designation_id for m in index.screen(s)]
    assert "AFG0006" in ids


def test_alias_match_entity(index):
    s = Subject(name="Haji Alim Hawala", subject_type="company", ref="c1")
    ids = [m.designation_id for m in index.screen(s)]
    assert "AFG0001" in ids


def test_entity_matched_by_registration_number(index):
    # exact business-reg-number is decisive even with an unrelated name
    s = Subject(name="Totally Unrelated Holdings Ltd", subject_type="company",
                identifiers=["190950894"], ref="c2")
    top = index.screen(s)[0]
    assert top.designation_id == "BEL0065"
    assert top.verdict == "RED"
    assert top.matched_fields["identifier"] == "exact"


def test_clean_miss(index):
    s = Subject(name="Penelope Honeywell-Cadwallader", subject_type="individual", ref="o5")
    assert index.screen(s) == []


def test_non_latin_name_is_indexed_and_matchable(designations, index):
    # find a designation whose native-script name was transliterated into an alias
    target = next(d for d in designations
                  if any(n.name_type == "Non-Latin Name" for n in d.names))
    nl = next(n for n in target.names if n.name_type == "Non-Latin Name")
    # screening the transliterated form (what a same-script subject would normalize
    # to) must surface the designation — otherwise non-Latin designees are unmatchable
    stype = "individual" if target.group_type == "Individual" else "company"
    hit_ids = [m.designation_id for m in index.screen(
        Subject(name=nl.normalized_name, subject_type=stype, ref="nl"))]
    assert target.unique_id in hit_ids


# --- unit-level guards (independent of list size) -----------------------------
def test_common_name_never_reaches_red_on_name_alone():
    # even a perfect name + corroboration cannot RED a common name (only an
    # exact identifier can) — the core false-positive guard
    assert _verdict(1.0, has_corroboration=True, has_disconfirm=False,
                    exact_identifier=False, common=True) == "AMBER"
    assert _verdict(1.0, has_corroboration=True, has_disconfirm=False,
                    exact_identifier=True, common=True) == "RED"


def test_verdict_thresholds():
    assert _verdict(0.5, False, False, False, False) is None
    assert _verdict(0.88, False, False, False, False) == "AMBER"
    assert _verdict(RED_NAME_THRESHOLD, True, False, False, False) == "RED"
    assert _verdict(RED_NAME_THRESHOLD, True, True, False, False) == "AMBER"  # disconfirm blocks RED


def test_token_alignment_defuses_single_common_token():
    df = {"MOHAMMAD": 500, "HASSAN": 500, "AKHUND": 2}
    # mononym "HASSAN" vs a 3-token name: 1 aligned, common -> not distinctive
    aligned, distinctive, cov = _token_alignment(
        ["MOHAMMAD", "HASSAN", "AKHUND"], ["HASSAN"], df)
    assert aligned == 1 and distinctive is False
    # a distinctive token aligns
    aligned, distinctive, cov = _token_alignment(
        ["MOHAMMAD", "HASSAN", "AKHUND"], ["AKHUND"], df)
    assert aligned == 1 and distinctive is True and cov == 1.0


def test_name_score_avoids_substring_inflation():
    combined, jw, ts = _name_score("JOHN", "JOHNSON")
    assert combined < 0.93  # "John" must not be a strong match for "Johnson"
