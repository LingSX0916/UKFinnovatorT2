Recorded Companies House fixtures (SYNTHETIC demo data).

These let the KYB module run end-to-end — search -> dossier -> Run sanction check
-> RED/AMBER/GREEN — with NO Companies House API key and NO network, so the demo
and CI work offline. When COMPANIES_HOUSE_API_KEY is set, the client hits the live
API instead and ignores these files.

Each file is <company_number>.json and mirrors the CH API response shapes under
keys: "profile", "officers", "persons-with-significant-control",
"filing-history", "charges".

IMPORTANT — these UK companies are FICTIONAL and invented for the demo. Where a
fixture names a real UK-sanctioned party (e.g. as an ultimate beneficial owner),
it does so only to exercise the screening engine against the real UK Sanctions
List; it is NOT an assertion that any real person controls these invented firms.

Demo companies:
  SC900001  Northwind Trading (UK) Ltd  -> RED  (indirect UBO is a sanctioned individual; ownership & control)
  SC900002  Granite Nominees Ltd        -> (holding co in the chain above)
  00000002  Brightline Savings PLC      -> GREEN (clean)
  SC900003  Meridian Holdings Ltd       -> AMBER (PSC opacity + high-risk-jurisdiction officer)
