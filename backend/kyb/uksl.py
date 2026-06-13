"""UK Sanctions List (UKSL) ingestion — parse the FCDO XML to normalized records.

The UKSL became the single UK sanctions list on 28 January 2026 (the OFSI
Consolidated List closed). Each designation carries a Unique ID and, for legacy
entries, an OFSI Group ID. A designation is an Individual, an Entity or a Ship.

This module is parsed against the *actual* structure of the published XML (see
KNOWN_PATHS, transcribed from the real file), not against assumptions. Two things
make the "100% field accuracy" claim demonstrable rather than asserted:

  1. `raw` keeps a lossless dict of every element/text in the source record, so
     nothing is ever silently dropped.
  2. `audit_paths()` returns every element path seen in the file minus KNOWN_PATHS.
     The golden test (tests/kyb/test_ingest.py) asserts that set is empty and that
     the parsed designation count equals the count in the file — so if the FCDO
     adds a new element, ingestion fails loudly instead of dropping data.

Pure parsing only: no DB writes here. The optional Supabase upsert lives in
`store.py`; the CLI that wires them together is `ingest_uksl.py`.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field

from lxml import etree

from . import normalize as N

# ---------------------------------------------------------------------------
# Schema contract: every element path that may appear *under* a <Designation>.
# Transcribed from the real UK-Sanctions-List.xml (6,194 designations). The golden
# test asserts the file contains no path outside this set — a new FCDO element
# therefore breaks CI loudly rather than being ingested as a silent gap.
# ---------------------------------------------------------------------------
SANCTION_INDICATOR_TAGS = (
    "AssetFreeze", "ArmsEmbargo", "TargetedArmsEmbargo", "CharteringOfShips",
    "ClosureOfRepresentativeOffices", "CrewServicingOfShipsAndAircraft", "Deflag",
    "PreventionOfBusinessArrangements", "ProhibitionOfPortEntry", "TravelBan",
    "PreventionOfCharteringOfShips", "PreventionOfCharteringOfShipsAndAircraft",
    "TechnicalAssistanceRelatedToAircraft", "TrustServicesSanctions",
    "DirectorDisqualificationSanction",
)

KNOWN_PATHS: frozenset[str] = frozenset({
    # top-level scalars
    "LastUpdated", "DateDesignated", "UniqueID", "OFSIGroupID", "UNReferenceNumber",
    "RegimeName", "IndividualEntityShip", "DesignationSource", "SanctionsImposed",
    "OtherInformation", "UKStatementofReasons",
    # names
    "Names", "Names/Name", "Names/Name/Name1", "Names/Name/Name2", "Names/Name/Name3",
    "Names/Name/Name4", "Names/Name/Name5", "Names/Name/Name6", "Names/Name/NameType",
    "Names/Name/AliasStrength",
    # non-latin names
    "NonLatinNames", "NonLatinNames/NonLatinName",
    "NonLatinNames/NonLatinName/NameNonLatinScript",
    "NonLatinNames/NonLatinName/NonLatinScriptType",
    "NonLatinNames/NonLatinName/NonLatinScriptLanguage",
    # titles
    "Titles", "Titles/Title",
    # contact
    "Addresses", "Addresses/Address", "Addresses/Address/AddressLine1",
    "Addresses/Address/AddressLine2", "Addresses/Address/AddressLine3",
    "Addresses/Address/AddressLine4", "Addresses/Address/AddressLine5",
    "Addresses/Address/AddressLine6", "Addresses/Address/AddressPostalCode",
    "Addresses/Address/AddressCountry",
    "PhoneNumbers", "PhoneNumbers/PhoneNumber",
    "EmailAddresses", "EmailAddresses/EmailAddress",
    "Websites", "Websites/Website",
    # sanctions imposed indicators
    "SanctionsImposedIndicators",
    *(f"SanctionsImposedIndicators/{t}" for t in SANCTION_INDICATOR_TAGS),
    # individual
    "IndividualDetails", "IndividualDetails/Individual",
    "IndividualDetails/Individual/DOBs", "IndividualDetails/Individual/DOBs/DOB",
    "IndividualDetails/Individual/BirthDetails",
    "IndividualDetails/Individual/BirthDetails/Location",
    "IndividualDetails/Individual/BirthDetails/Location/CountryOfBirth",
    "IndividualDetails/Individual/BirthDetails/Location/TownOfBirth",
    "IndividualDetails/Individual/Genders", "IndividualDetails/Individual/Genders/Gender",
    "IndividualDetails/Individual/Nationalities",
    "IndividualDetails/Individual/Nationalities/Nationality",
    "IndividualDetails/Individual/Positions",
    "IndividualDetails/Individual/Positions/Position",
    "IndividualDetails/Individual/PassportDetails",
    "IndividualDetails/Individual/PassportDetails/Passport",
    "IndividualDetails/Individual/PassportDetails/Passport/PassportNumber",
    "IndividualDetails/Individual/PassportDetails/Passport/PassportAdditionalInformation",
    "IndividualDetails/Individual/NationalIdentifierDetails",
    "IndividualDetails/Individual/NationalIdentifierDetails/NationalIdentifier",
    "IndividualDetails/Individual/NationalIdentifierDetails/NationalIdentifier/NationalIdentifierNumber",
    "IndividualDetails/Individual/NationalIdentifierDetails/NationalIdentifier/NationalIdentifierAdditionalInformation",
    # entity
    "EntityDetails", "EntityDetails/Entity",
    "EntityDetails/Entity/BusinessRegistrationNumbers",
    "EntityDetails/Entity/BusinessRegistrationNumbers/BusinessRegistrationNumber",
    "EntityDetails/Entity/TypeOfEntities",
    "EntityDetails/Entity/TypeOfEntities/TypeOfEntity",
    "EntityDetails/Entity/ParentCompanies",
    "EntityDetails/Entity/ParentCompanies/ParentCompany",
    "EntityDetails/Entity/Subsidiaries",
    "EntityDetails/Entity/Subsidiaries/Subsidiary",
    # ship
    "ShipDetails", "ShipDetails/Ship",
    "ShipDetails/Ship/IMONumbers", "ShipDetails/Ship/IMONumbers/IMONumber",
    "ShipDetails/Ship/CurrentOwnerOperators",
    "ShipDetails/Ship/CurrentOwnerOperators/CurrentOwnerOperator",
    "ShipDetails/Ship/PreviousOwnerOperators",
    "ShipDetails/Ship/PreviousOwnerOperators/PreviousOwnerOperator",
    "ShipDetails/Ship/CurrentBelievedFlagOfShips",
    "ShipDetails/Ship/CurrentBelievedFlagOfShips/CurrentBelievedFlagOfShip",
    "ShipDetails/Ship/PreviousFlags", "ShipDetails/Ship/PreviousFlags/PreviousFlag",
    "ShipDetails/Ship/TypeOfShipDetails", "ShipDetails/Ship/TypeOfShipDetails/TypeOfShip",
    "ShipDetails/Ship/TonnageOfShipDetails",
    "ShipDetails/Ship/TonnageOfShipDetails/TonnageOfShip",
    "ShipDetails/Ship/LengthOfShipDetails",
    "ShipDetails/Ship/LengthOfShipDetails/LengthOfShip",
    "ShipDetails/Ship/YearsBuilt", "ShipDetails/Ship/YearsBuilt/YearBuilt",
})


# ---------------------------------------------------------------------------
# Normalized record shapes
# ---------------------------------------------------------------------------
@dataclass
class SanctionName:
    name_type: str               # "Primary Name" | "Primary Name Variation" | "Alias"
    alias_strength: str | None   # "Good quality a.k.a" | "Low quality a.k.a" | None
    full_name: str               # assembled display name (Name1..Name6)
    normalized_name: str         # uppercased, de-punctuated, transliterated
    parts: list[str] = field(default_factory=list)

    @property
    def is_primary(self) -> bool:
        return self.name_type.lower().startswith("primary name") and "variation" not in self.name_type.lower()


@dataclass
class SanctionDOB:
    raw: str
    year: int | None
    month: int | None
    day: int | None


@dataclass
class SanctionIdentifier:
    id_type: str                 # passport | national_id | business_registration | imo
    value: str
    normalized: str
    additional_info: str | None = None


@dataclass
class Designation:
    unique_id: str
    group_type: str              # Individual | Entity | Ship
    regime_name: str
    ofsi_group_id: str | None = None
    un_reference_number: str | None = None
    designation_source: str | None = None
    sanctions_imposed: list[str] = field(default_factory=list)
    uk_statement_of_reasons: str | None = None
    other_information: str | None = None
    date_designated: str | None = None   # ISO YYYY-MM-DD or None
    last_updated: str | None = None
    names: list[SanctionName] = field(default_factory=list)
    non_latin_names: list[dict] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    addresses: list[dict] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)  # address countries (for geo risk)
    dobs: list[SanctionDOB] = field(default_factory=list)
    nationalities: list[str] = field(default_factory=list)
    genders: list[str] = field(default_factory=list)
    positions: list[str] = field(default_factory=list)
    birth_country: str | None = None
    birth_town: str | None = None
    identifiers: list[SanctionIdentifier] = field(default_factory=list)
    type_of_entities: list[str] = field(default_factory=list)
    parent_companies: list[str] = field(default_factory=list)
    subsidiaries: list[str] = field(default_factory=list)
    ship: dict | None = None
    raw: dict = field(default_factory=dict)

    # -- derived helpers used by the matcher (kept on the record so the matcher
    #    stays pure and just reads pre-normalized fields) --
    @property
    def primary_name(self) -> str:
        for n in self.names:
            if n.is_primary:
                return n.full_name
        return self.names[0].full_name if self.names else self.unique_id

    @property
    def normalized_names(self) -> list[str]:
        return [n.normalized_name for n in self.names if n.normalized_name]

    @property
    def dob_years(self) -> set[int]:
        return {d.year for d in self.dobs if d.year}

    @property
    def nationalities_norm(self) -> set[str]:
        return {N.normalize_name(x) for x in self.nationalities if x}

    @property
    def identifier_norms(self) -> set[str]:
        out: set[str] = set()
        for ident in self.identifiers:
            if ident.normalized:
                out.add(ident.normalized)
            if ident.id_type == "business_registration":
                out |= N.extract_identifier_tokens(ident.value)
        return out

    @property
    def is_asset_frozen(self) -> bool:
        return any(s.lower().startswith("asset freeze") for s in self.sanctions_imposed)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _findtext(el, path: str) -> str | None:
    found = el.find(path)
    t = _text(found) if found is not None else ""
    return t or None


def _alltext(el, path: str) -> list[str]:
    return [t for t in (_text(x) for x in el.findall(path)) if t]


def _el_to_obj(el):
    """Element -> python object (text leaf, or nested dict, with repeated tags
    collapsed to lists). Captures all element nesting and text content — the scope
    is element text, not XML attributes/mixed content (the UKSL file carries no
    data-bearing attributes; only namespace declarations on the root)."""
    children = list(el)
    if not children:
        return _text(el) or None
    obj: dict = {}
    for c in children:
        key = etree.QName(c).localname
        val = _el_to_obj(c)
        if key in obj:
            if not isinstance(obj[key], list):
                obj[key] = [obj[key]]
            obj[key].append(val)
        else:
            obj[key] = val
    return obj


def _assemble_name(name_el) -> tuple[str, list[str]]:
    parts = [t for t in (_findtext(name_el, f"Name{i}") for i in range(1, 7)) if t]
    return (" ".join(parts), parts)


def _parse_designation(el) -> Designation:
    group_type = _findtext(el, "IndividualEntityShip") or "Unknown"

    is_individual = group_type == "Individual"

    def _norm(text: str) -> str:
        # entities keep honorific/rank words and drop corp suffixes; individuals
        # drop honorifics and keep everything else (see normalize.normalize_name)
        return N.normalize_name(text, drop_corp_suffixes=not is_individual,
                                drop_honorifics=is_individual)

    names: list[SanctionName] = []
    for name_el in el.findall("Names/Name"):
        full, parts = _assemble_name(name_el)
        if not full:
            continue
        names.append(SanctionName(
            name_type=_findtext(name_el, "NameType") or "Alias",
            alias_strength=_findtext(name_el, "AliasStrength"),
            full_name=full,
            normalized_name=_norm(full),
            parts=parts,
        ))

    # Non-Latin (Cyrillic/Arabic/Han) names are transliterated and added as
    # searchable aliases. Without this a designee held only in native script — or a
    # subject screened under their native-script name — is silently unmatchable, a
    # false negative on exactly the high-risk regimes (Russia/Iran/Afghanistan).
    non_latin = []
    for nl in el.findall("NonLatinNames/NonLatinName"):
        nl_name = _findtext(nl, "NameNonLatinScript")
        non_latin.append({
            "name": nl_name,
            "type": _findtext(nl, "NonLatinScriptType"),
            "language": _findtext(nl, "NonLatinScriptLanguage"),
        })
        norm = _norm(nl_name) if nl_name else ""
        if norm:
            names.append(SanctionName(
                name_type="Non-Latin Name", alias_strength=None,
                full_name=nl_name, normalized_name=norm, parts=[nl_name]))

    addresses, countries = [], []
    for addr in el.findall("Addresses/Address"):
        a = {
            **{f"line{i}": _findtext(addr, f"AddressLine{i}") for i in range(1, 7)},
            "postal_code": _findtext(addr, "AddressPostalCode"),
            "country": _findtext(addr, "AddressCountry"),
        }
        addresses.append(a)
        if a["country"]:
            countries.append(a["country"])

    dobs = []
    for d in _alltext(el, "IndividualDetails/Individual/DOBs/DOB"):
        y, m, day = N.parse_partial_dob(d)
        dobs.append(SanctionDOB(raw=d, year=y, month=m, day=day))

    identifiers: list[SanctionIdentifier] = []
    for p in el.findall("IndividualDetails/Individual/PassportDetails/Passport"):
        num = _findtext(p, "PassportNumber")
        if num:
            identifiers.append(SanctionIdentifier(
                "passport", num, N.normalize_identifier(num),
                _findtext(p, "PassportAdditionalInformation")))
    for nid in el.findall(
            "IndividualDetails/Individual/NationalIdentifierDetails/NationalIdentifier"):
        num = _findtext(nid, "NationalIdentifierNumber")
        if num:
            identifiers.append(SanctionIdentifier(
                "national_id", num, N.normalize_identifier(num),
                _findtext(nid, "NationalIdentifierAdditionalInformation")))
    for br in _alltext(el, "EntityDetails/Entity/BusinessRegistrationNumbers/BusinessRegistrationNumber"):
        identifiers.append(SanctionIdentifier(
            "business_registration", br, N.normalize_identifier(br)))
    for imo in _alltext(el, "ShipDetails/Ship/IMONumbers/IMONumber"):
        identifiers.append(SanctionIdentifier("imo", imo, N.normalize_identifier(imo)))

    ship = None
    ship_el = el.find("ShipDetails/Ship")
    if ship_el is not None:
        ship = {
            "imo_numbers": _alltext(ship_el, "IMONumbers/IMONumber"),
            "current_owner_operators": _alltext(ship_el, "CurrentOwnerOperators/CurrentOwnerOperator"),
            "previous_owner_operators": _alltext(ship_el, "PreviousOwnerOperators/PreviousOwnerOperator"),
            "current_flags": _alltext(ship_el, "CurrentBelievedFlagOfShips/CurrentBelievedFlagOfShip"),
            "previous_flags": _alltext(ship_el, "PreviousFlags/PreviousFlag"),
            "type_of_ship": _alltext(ship_el, "TypeOfShipDetails/TypeOfShip"),
            "tonnage": _alltext(ship_el, "TonnageOfShipDetails/TonnageOfShip"),
            "length": _alltext(ship_el, "LengthOfShipDetails/LengthOfShip"),
            "years_built": _alltext(ship_el, "YearsBuilt/YearBuilt"),
        }

    sanctions_imposed = [
        s.strip() for s in (_findtext(el, "SanctionsImposed") or "").split("|") if s.strip()
    ]

    return Designation(
        unique_id=_findtext(el, "UniqueID") or "",
        group_type=group_type,
        regime_name=_findtext(el, "RegimeName") or "",
        ofsi_group_id=_findtext(el, "OFSIGroupID"),
        un_reference_number=_findtext(el, "UNReferenceNumber"),
        designation_source=_findtext(el, "DesignationSource"),
        sanctions_imposed=sanctions_imposed,
        uk_statement_of_reasons=_findtext(el, "UKStatementofReasons"),
        other_information=_findtext(el, "OtherInformation"),
        date_designated=N.parse_uksl_date(_findtext(el, "DateDesignated") or ""),
        last_updated=N.parse_uksl_date(_findtext(el, "LastUpdated") or ""),
        names=names,
        non_latin_names=non_latin,
        titles=_alltext(el, "Titles/Title"),
        addresses=addresses,
        countries=countries,
        dobs=dobs,
        nationalities=_alltext(el, "IndividualDetails/Individual/Nationalities/Nationality"),
        genders=_alltext(el, "IndividualDetails/Individual/Genders/Gender"),
        positions=_alltext(el, "IndividualDetails/Individual/Positions/Position"),
        birth_country=_findtext(el, "IndividualDetails/Individual/BirthDetails/Location/CountryOfBirth"),
        birth_town=_findtext(el, "IndividualDetails/Individual/BirthDetails/Location/TownOfBirth"),
        identifiers=identifiers,
        type_of_entities=_alltext(el, "EntityDetails/Entity/TypeOfEntities/TypeOfEntity"),
        parent_companies=_alltext(el, "EntityDetails/Entity/ParentCompanies/ParentCompany"),
        subsidiaries=_alltext(el, "EntityDetails/Entity/Subsidiaries/Subsidiary"),
        ship=ship,
        raw=_el_to_obj(el) or {},
    )


def parse_uksl(path: str):
    """Stream <Designation> records from the UKSL XML as Designation objects.

    Memory-safe via iterparse + element clearing — the 21 MB / 6,194-record file
    is parsed without loading it all at once.
    """
    context = etree.iterparse(path, events=("end",), tag="Designation")
    for _event, el in context:
        yield _parse_designation(el)
        el.clear()
        # drop preceding siblings to keep memory flat
        while el.getprevious() is not None:
            del el.getparent()[0]


def load_uksl(path: str) -> list[Designation]:
    return list(parse_uksl(path))


def descendant_paths(el, prefix: str = "") -> set[str]:
    """All descendant element paths under `el`, relative to it."""
    paths: set[str] = set()
    for child in el:
        tag = etree.QName(child).localname
        p = f"{prefix}/{tag}" if prefix else tag
        paths.add(p)
        paths |= descendant_paths(child, p)
    return paths


def _raw_child_counts(el) -> dict:
    """Count source child-records under one <Designation> (non-empty names etc.)."""
    def _nonempty_names(node):
        return sum(1 for n in node.findall("Names/Name")
                   if any(_text(n.find(f"Name{i}")) for i in range(1, 7)))
    return {
        "names": _nonempty_names(el),
        "non_latin_names": sum(1 for nl in el.findall("NonLatinNames/NonLatinName")
                               if _findtext(nl, "NameNonLatinScript")),
        "dobs": len(el.findall("IndividualDetails/Individual/DOBs/DOB")),
        "passports": sum(1 for p in el.findall(
            "IndividualDetails/Individual/PassportDetails/Passport") if _findtext(p, "PassportNumber")),
        "national_ids": sum(1 for x in el.findall(
            "IndividualDetails/Individual/NationalIdentifierDetails/NationalIdentifier")
            if _findtext(x, "NationalIdentifierNumber")),
        "business_regs": len(_alltext(
            el, "EntityDetails/Entity/BusinessRegistrationNumbers/BusinessRegistrationNumber")),
        "imos": len(_alltext(el, "ShipDetails/Ship/IMONumbers/IMONumber")),
    }


def parsed_child_counts(designations: list[Designation]) -> dict:
    """The same tallies computed from PARSED objects, so the golden test can assert
    parsed == source for every child-record class (not just designation count)."""
    out = {"names": 0, "dobs": 0, "passports": 0, "national_ids": 0,
           "business_regs": 0, "imos": 0}
    for d in designations:
        out["names"] += len(d.names)  # incl. transliterated non-Latin aliases
        out["dobs"] += len(d.dobs)
        for it in d.identifiers:
            key = {"passport": "passports", "national_id": "national_ids",
                   "business_registration": "business_regs", "imo": "imos"}.get(it.id_type)
            if key:
                out[key] += 1
    return out


def audit_paths(path: str) -> dict:
    """Reconciliation audit used by the golden test.

    Returns the total designation count, the per-type breakdown, every element path
    seen under any <Designation>, the set of paths NOT in KNOWN_PATHS (must be empty
    for the field-coverage claim), per-class source child counts, and UniqueID
    integrity (duplicates / empties) — so count parity is backed by VALUE parity and
    distinct-id parity, not just row count.
    """
    count = 0
    group_counts: dict[str, int] = {}
    seen: set[str] = set()
    date_generated = None
    unique_ids: list[str] = []
    child_counts = {"names": 0, "non_latin_names": 0, "dobs": 0, "passports": 0,
                    "national_ids": 0, "business_regs": 0, "imos": 0}
    context = etree.iterparse(path, events=("end",), tag=("Designation", "DateGenerated"))
    for _event, el in context:
        if etree.QName(el).localname == "DateGenerated":
            date_generated = _text(el)
            el.clear()
            continue
        count += 1
        gt = _findtext(el, "IndividualEntityShip") or "Unknown"
        group_counts[gt] = group_counts.get(gt, 0) + 1
        unique_ids.append(_findtext(el, "UniqueID") or "")
        seen |= descendant_paths(el)
        for k, v in _raw_child_counts(el).items():
            child_counts[k] += v
        el.clear()
    dup = [uid for uid, c in Counter(unique_ids).items() if uid and c > 1]
    return {
        "designation_count": count,
        "group_counts": group_counts,
        "seen_paths": seen,
        "unmapped_paths": seen - KNOWN_PATHS,
        "date_generated": date_generated,
        "child_counts": child_counts,
        "distinct_ids": len(set(unique_ids)),
        "duplicate_ids": dup,
        "empty_ids": sum(1 for u in unique_ids if not u),
    }


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
