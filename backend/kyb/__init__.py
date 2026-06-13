"""KYB & UK Sanctions Intelligence module.

The "is the company behind this advert legitimate?" pillar of the Triage
product. Given a UK company it answers: who really owns and controls it, what is
its filing behaviour, and are the company / its officers / its beneficial owners
on the UK Sanctions List or the FCA Warning List — with an explainable,
evidence-cited FCA/FATF risk rating.

Design rules (mirrors FCA.md, the promotions rules engine):
  * No verdict without evidence — every match carries the exact matched data,
    a confidence, and the regulatory provision it rests on.
  * The tool triages; a human decides — nothing auto-confirms a sanctions hit.
  * Truth over plausibility — we never fabricate a designation or a match.

The engines here (normalize, uksl, matching, risk, graph) are pure and
deterministic with no I/O inside the scoring functions, so they can be unit
tested hard. The API/store layers wire them to Companies House and Supabase.
"""

__all__ = [
    "normalize",
    "uksl",
    "matching",
    "risk",
    "warning_list",
    "graph",
    "companies_house",
    "screening",
]

__version__ = "0.1.0"
