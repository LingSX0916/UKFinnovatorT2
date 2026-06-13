"""Normalization is shared by ingestion and matching — these lock its behaviour."""
from backend.kyb import normalize as N


def test_uppercase_depunctuate_collapse():
    assert N.normalize_name("  Acme,  Holdings!! ") == "ACME HOLDINGS"


def test_transliteration_strips_diacritics_and_scripts():
    assert N.normalize_name("Müller") == "MULLER"
    # Cyrillic -> Latin (so a Cyrillic source name and a Latin subject can match)
    assert "ALEKSEI" in N.normalize_name("Алексей") or "ALEKSEY" in N.normalize_name("Алексей")


def test_honorifics_dropped_but_not_to_nothing():
    assert N.normalize_name("Mullah Mohammad Hassan") == "MOHAMMAD HASSAN"
    # a name that is ONLY a title must not normalize to empty
    assert N.normalize_name("Mullah") == "MULLAH"


def test_corp_suffixes_dropped_only_when_requested():
    assert N.normalize_name("Acme Trading Ltd") == "ACME TRADING LTD"
    # only the legal-form suffix (LTD) is dropped, not ordinary words
    assert N.normalize_name("Acme Trading Ltd", drop_corp_suffixes=True) == "ACME TRADING"
    assert N.normalize_name("Synesis LLC", drop_corp_suffixes=True) == "SYNESIS"


def test_entity_keeps_rank_words_but_individual_drops_them():
    # rank/role words are legitimate company-name tokens for entities
    assert N.normalize_name("General Dynamics Corporation",
                            drop_corp_suffixes=True, drop_honorifics=False) == "GENERAL DYNAMICS"
    # ...but for an individual they are honorifics to drop
    assert N.normalize_name("General Reza Pahlavi", drop_honorifics=True) == "REZA PAHLAVI"


def test_identifier_normalization():
    assert N.normalize_identifier("GB 12 3456 78") == "GB12345678"
    assert N.normalize_identifier("07731902") == "07731902"


def test_identifier_token_extraction_requires_digit():
    toks = N.extract_identifier_tokens(
        "(УНН/ИНН): 190950894 (Belarus),\n7704734000/770301001 (Russia)")
    assert "190950894" in toks and "7704734000" in toks and "770301001" in toks
    # pure-alpha noise (country names) must be excluded
    assert "BELARUS" not in toks and "RUSSIA" not in toks


def test_partial_dob_parsing():
    assert N.parse_partial_dob("dd/mm/1945") == (1945, None, None)
    assert N.parse_partial_dob("12/03/1980") == (1980, 3, 12)
    assert N.parse_partial_dob("") == (None, None, None)


def test_uksl_date_parsing_rejects_partials():
    assert N.parse_uksl_date("29/06/2012") == "2012-06-29"
    assert N.parse_uksl_date("dd/mm/1945") is None
