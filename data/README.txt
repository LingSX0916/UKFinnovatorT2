Sample adverts used for testing and demo day.

Organised by compliance status:
  compliant/   — GREEN adverts that pass all FCA rules
  borderline/  — AMBER adverts from authorised firms that still breach specific rules
  scam/        — RED adverts: egregious breaches, fake approvals, guaranteed returns

Also contains:
  warning_list.json — ~15 fictional scam firm names used for the Warning List cross-check.
                      CoinVault Pro is in here so the red badge fires on the demo showstopper.

In production, this would point at the live FCA Warning List and the FCA Financial Services
Register API to confirm whether a named firm is actually authorised.
