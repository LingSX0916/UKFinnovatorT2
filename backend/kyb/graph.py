"""UBO / ownership graph builder.

Builds a directed ownership graph from Companies House PSC data. For each
corporate / legal-person PSC it tries to resolve the owning company (by
registration number, then by name) and recurses into *its* PSCs — this is how
indirect / ultimate beneficial owners are found. Effective ownership is
multiplied down each chain so a beneficial owner exceeding 25% (PSC threshold) or
50% (control) can be flagged.

Cycle detection (companies can own each other) and a max depth bound keep the
traversal finite. The screener colours each node by its sanctions result; if any
node with >50% effective control is a sanctions match, the company is "caught by
ownership and control" (OFSI) even if not separately listed.
"""
from __future__ import annotations

import re

from .matching import Subject

DEFAULT_MAX_DEPTH = 5

# Map a PSC "nature of control" to a conservative lower-bound ownership % and
# whether it is a control right irrespective of %.
_PCT_RE = re.compile(r"(\d+)-to-(\d+)-percent")
_CONTROL_NATURES = (
    "right-to-appoint-and-remove-directors",
    "significant-influence-or-control",
)


def parse_natures(natures: list[str] | None) -> tuple[int, int, bool]:
    """Return (lower_bound_percent, upper_bound_percent, is_control_right).

    A CH band like 'ownership-of-shares-50-to-75-percent' means the true holding is
    strictly >50% — so for the OFSI ownership-and-control test we evaluate against
    the band's UPPER edge ('could exceed 50%'), while the conservative lower edge is
    kept for the displayed effective-% figure.
    """
    natures = natures or []
    lower = upper = 0
    control = False
    for n in natures:
        n = (n or "").lower()
        m = _PCT_RE.search(n)
        if m:
            lower = max(lower, int(m.group(1)))
            upper = max(upper, int(m.group(2)))
        if any(c in n for c in _CONTROL_NATURES):
            control = True
    return (lower, upper, control)


def ownership_band(lower: int) -> str:
    return {75: "75-100%", 50: "50-75%", 25: "25-50%"}.get(lower, f"{lower}%+" if lower else "—")


def _resolve_company(client, psc: dict) -> str | None:
    """Resolve a corporate/legal PSC to a UK company number, if we can."""
    ident = psc.get("identification") or {}
    reg = ident.get("registration_number")
    if reg and client._load_fixture(str(reg).upper()) is not None:
        return str(reg).upper()
    # try CH search by name (best-effort; fixtures match by substring)
    name = psc.get("name") or ""
    if name:
        for hit in client.search_companies(name, limit=3):
            num = hit.get("company_number")
            if num and (hit.get("company_name", "").lower() == name.lower()):
                return num
    if reg:
        # live CH: assume the registration number IS the company number for UK RLEs
        prof = client.get_profile(str(reg))
        if prof:
            return prof["company_number"]
    return None


def build_ownership_graph(client, company_number: str, *, max_depth: int = DEFAULT_MAX_DEPTH) -> dict:
    profile = client.get_profile(company_number) or {"company_number": company_number, "name": company_number}
    root_id = f"company:{company_number}"
    nodes: dict[str, dict] = {
        root_id: {
            "id": root_id, "kind": "company", "name": profile.get("name") or company_number,
            "company_number": company_number, "depth": 0, "effective_pct": 100,
            "is_target": True, "screening": None,
        }
    }
    edges: list[dict] = []
    subjects: list[Subject] = []
    foreign_rle = False
    visited: set[str] = {company_number.upper()}
    max_seen_depth = 0

    def walk(number: str, parent_id: str, parent_pct: float, parent_pct_max: float, depth: int):
        nonlocal foreign_rle, max_seen_depth
        if depth > max_depth:
            return
        for psc in client.get_pscs(number):
            if psc.get("kind") == "statement" or not (psc.get("name")):
                continue
            kind = psc.get("kind") or "individual"
            lower, upper, control = parse_natures(psc.get("natures_of_control"))
            # conservative lower-edge effective % for display; upper-edge for the
            # OFSI "could exceed 50%" control test
            eff = parent_pct * (lower or 0) / 100.0 if parent_pct else 0
            eff_max = parent_pct_max * (upper or 0) / 100.0 if parent_pct_max else 0
            node_id = psc["id"]
            max_seen_depth = max(max_seen_depth, depth)

            is_corporate = "corporate" in kind or "legal" in kind
            node = {
                "id": node_id,
                "kind": "entity" if is_corporate else "individual",
                "name": psc.get("name"),
                "depth": depth,
                "ownership_band": ownership_band(lower),
                "lower_pct": lower,
                "effective_pct": round(eff, 1),
                "effective_pct_max": round(eff_max, 1),
                # OFSI ownership & control: an explicit control right, OR an
                # effective holding that could exceed 50% down this chain
                "is_control": control or eff_max > 50,
                "natures_of_control": psc.get("natures_of_control") or [],
                "ceased": bool(psc.get("ceased_on")),
                "screening": None,
            }
            nodes[node_id] = node
            edges.append({
                "from": node_id, "to": parent_id,
                "ownership_band": node["ownership_band"],
                "effective_pct": node["effective_pct"],
                "natures_of_control": node["natures_of_control"],
                "is_direct": depth == 1,
                "depth": depth,
            })

            # build a screening Subject for this owner
            if is_corporate:
                ident = psc.get("identification") or {}
                country = ident.get("country_registered")
                if country and country.strip().lower() not in {"england", "wales", "scotland",
                                                                "united kingdom", "uk", "northern ireland", "england/wales"}:
                    foreign_rle = True
                resolved = _resolve_company(client, psc)
                ids = [ident["registration_number"]] if ident.get("registration_number") else []
                if resolved and resolved not in ids:
                    ids.append(resolved)
                subjects.append(Subject(
                    name=psc["name"], subject_type="entity", ref=node_id,
                    identifiers=ids, country=country))
                # ONE node per corporate owner: if we can resolve it to a UK
                # company, attach its own PSCs to THIS node (no duplicate company
                # node) so the chain reads owner -> owner -> beneficial owner.
                if resolved:
                    node["company_number"] = resolved
                    node["registration_number"] = ident.get("registration_number") or resolved
                    if resolved.upper() not in visited:
                        visited.add(resolved.upper())
                        walk(resolved, node_id, eff or parent_pct,
                             eff_max or parent_pct_max, depth + 1)
            else:
                subjects.append(Subject(
                    name=psc["name"], subject_type="psc", ref=node_id,
                    dob_year=psc.get("dob_year"),
                    nationalities=[psc["nationality"]] if psc.get("nationality") else [],
                    country=psc.get("country_of_residence")))

    walk(company_number, root_id, 100.0, 100.0, 1)

    return {
        "company_number": company_number,
        "nodes": list(nodes.values()),
        "edges": edges,
        "subjects": subjects,
        "max_depth": max_seen_depth,
        "foreign_rle": foreign_rle,
    }
