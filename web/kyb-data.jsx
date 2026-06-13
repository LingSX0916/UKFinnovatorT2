/* ============================================================
   kyb-data.jsx — KYB console data layer: Companies House +
   sanctions screening API (same-origin Flask, /api/*).
   Exposes: KYB (api helpers), SCREEN_STEPS, DEMO_COMPANIES,
            ragOf, RAG_LABEL
   ============================================================ */

const SCREEN_STEPS = [
  "Loading company profile & officers",
  "Resolving ultimate beneficial owners",
  "Screening every subject against the UK Sanctions List",
  "Cross-referencing the FCA Warning List",
  "Applying the OFSI ownership & control rule",
  "Computing the FCA / FATF risk rating"
];

/* One-click demo companies (served from recorded CH fixtures offline). */
const DEMO_COMPANIES = [
  { number: "SC900001", name: "Northwind Trading (UK) Ltd", hint: "RED · sanctioned ultimate owner" },
  { number: "SC900003", name: "Meridian Holdings Ltd", hint: "AMBER · opacity + high-risk jurisdiction" },
  { number: "00000002", name: "Brightline Savings PLC", hint: "GREEN · clean" }
];

const RAG_LABEL = {
  RED: "Red · Prohibited / EDD",
  AMBER: "Amber · High risk / EDD",
  GREEN: "Green · Standard DD"
};

function ragOf(verdict) {
  return ({ RED: "red", AMBER: "amber", GREEN: "green" })[String(verdict || "").toUpperCase()] || "green";
}

async function _get(url) {
  const res = await fetch(url);
  if (!res.ok) {
    let msg = "HTTP " + res.status;
    try { const j = await res.json(); if (j.error) msg = j.error; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

async function _post(url, body) {
  const res = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {})
  });
  if (!res.ok) {
    let msg = "HTTP " + res.status;
    try { const j = await res.json(); if (j.error) msg = j.error; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

const KYB = {
  health: () => _get("/api/health"),
  search: (q) => _get("/api/company/search?q=" + encodeURIComponent(q)).then(d => d.items || []),
  dossier: (number) => _get("/api/company/" + encodeURIComponent(number)),
  screen: (number, runBy) => _post("/api/company/" + encodeURIComponent(number) + "/screen",
    { run_by: runBy || "compliance-officer", as_of: "2026-06-13" }),
  decide: (matchId, decision, note) => _post("/api/screening/match/" + encodeURIComponent(matchId) + "/decision",
    { decision, note, reviewer: "compliance-officer" }),
  exportUrl: (number, fmt) => "/api/company/" + encodeURIComponent(number) + "/export?format=" + (fmt || "json")
};

Object.assign(window, { KYB, SCREEN_STEPS, DEMO_COMPANIES, RAG_LABEL, ragOf });
