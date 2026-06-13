"""CLI: ingest the UK Sanctions List XML.

    python -m backend.kyb.ingest_uksl --file inputs/UK-Sanctions-List.xml
    python -m backend.kyb.ingest_uksl --file inputs/UK-Sanctions-List.xml --supabase

Prints the reconciliation report (parsed count, per-type breakdown, and any
element paths NOT in the known schema — which must be empty for 100% coverage),
plus the file SHA-256 and a sanctions_import provenance line. With --supabase it
upserts the designations into the sanctions_* tables (idempotent, keyed on the
UKSL Unique ID).
"""
from __future__ import annotations

import argparse
import sys

from . import uksl


def reconcile(path: str) -> dict:
    audit = uksl.audit_paths(path)
    sha = uksl.file_sha256(path)
    print("UK Sanctions List ingestion — reconciliation")
    print("=" * 52)
    print(f"file:               {path}")
    print(f"sha256:             {sha}")
    print(f"date generated:     {audit['date_generated']}")
    print(f"designations:       {audit['designation_count']}")
    for gt, n in sorted(audit["group_counts"].items()):
        print(f"  - {gt:<12} {n}")
    print(f"distinct UniqueIDs:  {audit['distinct_ids']}  "
          f"(duplicates: {len(audit['duplicate_ids'])}, empty: {audit['empty_ids']})")
    print(f"element paths seen: {len(audit['seen_paths'])}  (known: {len(uksl.KNOWN_PATHS)})")
    if audit["unmapped_paths"]:
        print("UNMAPPED PATHS (FAIL — schema drift, data would be dropped):")
        for p in sorted(audit["unmapped_paths"]):
            print(f"    ! {p}")
    else:
        print("unmapped paths:     0  ✓ every element type is mapped (100% field coverage)")
    cc = audit["child_counts"]
    print(f"source child records: names={cc['names']} (+{cc['non_latin_names']} non-latin) "
          f"dobs={cc['dobs']} passports={cc['passports']} national_ids={cc['national_ids']} "
          f"business_regs={cc['business_regs']} imos={cc['imos']}")
    audit["sha256"] = sha
    return audit


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ingest the UK Sanctions List XML.")
    ap.add_argument("--file", required=True, help="path to UK-Sanctions-List.xml")
    ap.add_argument("--supabase", action="store_true",
                    help="also upsert designations into the sanctions_* tables")
    args = ap.parse_args(argv)

    audit = reconcile(args.file)
    if audit["unmapped_paths"]:
        print("\nRefusing to ingest: unmapped elements would be silently dropped.", file=sys.stderr)
        return 2
    if audit["duplicate_ids"] or audit["empty_ids"]:
        print(f"\nRefusing to ingest: UniqueID integrity failed "
              f"(duplicates={audit['duplicate_ids'][:5]}, empty={audit['empty_ids']}) — "
              f"downstream keys on unique_id and rows would collapse.", file=sys.stderr)
        return 4

    if args.supabase:
        from . import store
        if not store.enabled():
            print("\n--supabase given but SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set.",
                  file=sys.stderr)
            return 3
        print("\nUpserting designations to Supabase (idempotent on unique_id)…")
        designations = uksl.load_uksl(args.file)
        n = store.upsert_designations(designations, source_file=args.file,
                                      file_sha256=audit["sha256"])
        print(f"upserted {n} designations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
