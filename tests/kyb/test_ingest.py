"""Golden / reconciliation tests — make the "100% field accuracy" claim demonstrable.

Runs against the committed 30-designation sample (CI, offline). If the full UKSL
file is available at $UKSL_FULL_XML, an extra test proves the same on all 6,194
designations.
"""
import os
from pathlib import Path

import pytest

from backend.kyb import uksl

SAMPLE = Path(__file__).parent / "fixtures" / "uksl_sample.xml"
SAMPLE_DESIGNATION_COUNT = 30


def test_sample_count_parity():
    audit = uksl.audit_paths(str(SAMPLE))
    assert audit["designation_count"] == SAMPLE_DESIGNATION_COUNT
    assert sum(audit["group_counts"].values()) == SAMPLE_DESIGNATION_COUNT


def test_no_unmapped_elements():
    """Every element path in the file must be in KNOWN_PATHS — a new FCDO element
    fails loudly here instead of being silently dropped."""
    audit = uksl.audit_paths(str(SAMPLE))
    assert audit["unmapped_paths"] == set(), f"unmapped: {audit['unmapped_paths']}"


def test_loaded_count_matches_audit():
    audit = uksl.audit_paths(str(SAMPLE))
    designations = uksl.load_uksl(str(SAMPLE))
    assert len(designations) == audit["designation_count"]


def test_entity_roundtrip_aliases_and_regnumber(by_id):
    # AFG0001 — entity with 8 aliases and a non-latin name
    e = by_id["AFG0001"]
    assert e.group_type == "Entity"
    assert e.primary_name == "HAJI KHAIRULLAH HAJI SATTAR MONEY EXCHANGE"
    aliases = [n for n in e.names if n.name_type == "Alias"]
    assert len(aliases) == 8
    # the native-script name is transliterated and indexed as a searchable alias
    assert any(n.name_type == "Non-Latin Name" for n in e.names)
    assert e.non_latin_names and e.non_latin_names[0]["name"]
    # entity honorific policy: rank/title words are KEPT for entities
    assert "HAJI" in e.names[0].normalized_name
    assert e.is_asset_frozen


def test_individual_roundtrip_dob_nationality_passport(by_id):
    # AFG0006 — many partial DOBs, nationality, passport, titles
    i = by_id["AFG0006"]
    assert i.group_type == "Individual"
    assert 1945 in i.dob_years
    assert "Afghanistan" in i.nationalities
    assert any(x.id_type == "passport" for x in i.identifiers)
    assert "Mullah" in i.titles


def test_business_registration_extracted(by_id):
    # BEL0065 — LLC Synesis, business registration numbers
    e = by_id["BEL0065"]
    assert any(x.id_type == "business_registration" for x in e.identifiers)
    assert "190950894" in e.identifier_norms


def test_ship_imo(by_id):
    s = by_id["DPR0075"]
    assert s.group_type == "Ship"
    assert any(x.id_type == "imo" for x in s.identifiers)


def test_raw_is_lossless(by_id):
    # the raw dict keeps the full record so nothing is silently dropped
    e = by_id["AFG0001"]
    assert e.raw.get("UniqueID") == "AFG0001"
    assert "Names" in e.raw


def test_unique_id_integrity():
    # count parity is backed by distinct-id parity (no duplicate / empty UniqueIDs)
    audit = uksl.audit_paths(str(SAMPLE))
    assert audit["distinct_ids"] == audit["designation_count"]
    assert audit["duplicate_ids"] == []
    assert audit["empty_ids"] == 0


def test_value_parity_child_records():
    # parsed child-record counts == source counts (not just designation count) —
    # proves names/aliases/DOBs/identifiers are loaded, not silently dropped
    audit = uksl.audit_paths(str(SAMPLE))
    designations = uksl.load_uksl(str(SAMPLE))
    parsed = uksl.parsed_child_counts(designations)
    src = audit["child_counts"]
    # parsed names include the transliterated non-Latin aliases
    assert parsed["names"] == src["names"] + src["non_latin_names"]
    for key in ("dobs", "passports", "national_ids", "business_regs", "imos"):
        assert parsed[key] == src[key], f"{key}: parsed {parsed[key]} != source {src[key]}"


@pytest.mark.skipif(not os.environ.get("UKSL_FULL_XML"),
                    reason="set UKSL_FULL_XML to the full UK-Sanctions-List.xml to run")
def test_full_file_count_parity():
    audit = uksl.audit_paths(os.environ["UKSL_FULL_XML"])
    assert audit["designation_count"] == 6194
    assert audit["unmapped_paths"] == set()
    assert audit["distinct_ids"] == 6194 and audit["empty_ids"] == 0
