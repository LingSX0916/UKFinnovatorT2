/* ============================================================
   data.jsx — incoming complaints (from the public "Report a
   financial promotion" form) + the agent that auto-triages
   and categorises each one.
   Exposes: COMPLAINTS, INCOMING, SCAN_STEPS, analyseAdvert,
            relTime
   ============================================================ */

const SCAN_STEPS = [
  "Reading complaint & advert copy",
  "Checking for prominent risk warnings (COBS 4.2)",
  "Testing 'fair, clear & not misleading' (COBS 4.5)",
  "Scanning for guaranteed-return & performance claims",
  "Cross-referencing the FCA Warning List",
  "Verifying Companies House & the FS Register",
  "Assigning category & RAG priority"
];

/* ---- Rulebook (markdown) — the same FCA.md the backend feeds to the model.
   Fetched here only to show the rule count on the board's agent strip. ---- */
let RULEBOOK_TEXT = "";
const RULEBOOK = { loaded: false, rules: 8, file: "FCA.md", error: false };
async function loadRulebook() {
  if (RULEBOOK.loaded || RULEBOOK_TEXT) return RULEBOOK_TEXT;
  try {
    const res = await fetch("FCA.md");
    RULEBOOK_TEXT = await res.text();
    // rule headings look like "#### ⭐ R1. …" or "#### R6. …"
    RULEBOOK.rules = (RULEBOOK_TEXT.match(/^####\s+(?:⭐\s+)?R\d+\./gm) || []).length || 8;
    RULEBOOK.loaded = true;
  } catch (e) {
    RULEBOOK.error = true;
    console.warn("Could not load rulebook md:", e);
  }
  return RULEBOOK_TEXT;
}

/* ---- Backend endpoints ---- */
const SCAN_ENDPOINT = "/scan";              // OpenAI gpt-4o grounded in FCA.md
const COMPLAINTS_ENDPOINT = "/complaints";  // Supabase-backed persistence (via Flask)

// Load previously persisted complaints (each already carries its analysis).
async function fetchSavedComplaints() {
  try {
    const res = await fetch(COMPLAINTS_ENDPOINT);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.complaints) ? data.complaints : [];
  } catch (e) {
    console.warn("Could not load saved complaints:", e);
    return [];
  }
}

// Persist one triaged complaint card. No-op (silent) if persistence is off.
async function saveComplaint(card) {
  try {
    await fetch(COMPLAINTS_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(card)
    });
  } catch (e) {
    console.warn("Could not save complaint:", e);
  }
}

/* The backend returns the FCA.md rules-engine contract (v2.0):
     { overall_verdict: "RED"|"AMBER"|"GREEN", summary, warning_list_hit,
       product_type, communicator_status,
       rules:[{rule_id,name,triggered,severity:"RED"|"AMBER"|"GREEN",provision,evidence,explanation,suggested_fix}],
       warning_list_hits:[]  // added by api.py from the local Warning List }
   The mapper is tolerant of the earlier PASS/FAIL/FLAG schema too, so a change
   of rulebook never silently blanks the UI. */

// is this rule a breach to surface? (new: triggered bool; old: FAIL/FLAG verdict)
function ruleIsBreach(r) {
  if (typeof r.triggered === "boolean") return r.triggered;
  if (r.verdict) return r.verdict === "FAIL" || r.verdict === "FLAG";
  return true; // listed with neither flag → assume it is a breach
}
// map a rule to the UI severity (high/medium/low)
function ruleSeverity(r) {
  const sev = String(r.severity || "").toUpperCase();
  if (sev === "RED") return "high";
  if (sev === "AMBER") return "medium";
  if (sev === "GREEN") return "low";
  if (r.verdict === "FAIL") return new Set(["R1", "R2", "R6", "R8"]).has(r.rule_id || r.id) ? "high" : "medium";
  return "low";
}

function mapBackendToAnalysis(res, advert, company) {
  const rag = ({ RED: "red", AMBER: "amber", GREEN: "green" })[
    String(res.overall_verdict || res.overall_status || "").toUpperCase()
  ] || "amber";
  const rules = Array.isArray(res.rules) ? res.rules : [];

  // breaches = every triggered/failed rule, most severe first
  const sevRank = { high: 0, medium: 1, low: 2 };
  const breaches = rules
    .filter(ruleIsBreach)
    .map(r => ({
      rule: String(r.provision || r.rule_id || r.id || "—"),
      title: String(r.name || "Possible breach"),
      severity: ruleSeverity(r),
      explanation: String(r.explanation || r.reason || ""),
      quote: typeof r.evidence === "string" ? r.evidence : ""
    }))
    .sort((a, b) => sevRank[a.severity] - sevRank[b.severity])
    .slice(0, 5);

  const top = breaches[0];

  // authorisation: prefer communicator_status, else infer from R6/R1
  const commStatus = String(res.communicator_status || "").toLowerCase();
  const r6 = rules.find(r => (r.rule_id || r.id) === "R6");
  const r1 = rules.find(r => (r.rule_id || r.id) === "R1");
  let authStatus = "unknown";
  if (commStatus) {
    authStatus = commStatus.includes("unauthorised") ? "not_authorised"
      : (commStatus.includes("authorised") || commStatus.includes("approved")) ? "authorised"
      : "unknown";
  } else if (r6 && ruleIsBreach(r6)) {
    authStatus = "not_authorised";
  } else if (r1) {
    authStatus = r1.verdict === "PASS" ? "authorised" : r1.verdict === "FAIL" ? "not_authorised" : "unknown";
  }
  const authNote = r6 && r6.explanation ? String(r6.explanation)
    : r1 && (r1.explanation || r1.reason) ? String(r1.explanation || r1.reason)
    : commStatus ? `Communicator reported as ${commStatus}.`
    : "Authorisation not assessed.";

  const hits = Array.isArray(res.warning_list_hits) ? res.warning_list_hits : [];
  const firms = Array.isArray(res.named_firms) ? res.named_firms : [];
  const name = (company && company.trim()) || firms[0] || "Unidentified promoter";

  const warnStatus = hits.length ? "match" : (name && name !== "Unidentified promoter" ? "clear" : "unknown");
  const warnNote = hits.length
    ? `On the FCA Warning List — matched: ${hits.join(", ")}.`
    : (warnStatus === "clear"
        ? "No match against the loaded Warning List. Confirm on the live FCA register before action."
        : "No firm name identified to check against the Warning List.");

  const category = rag === "green"
    ? "Compliant — no action"
    : (top && top.title) || (rag === "red" ? "Serious breach" : "Needs amendment");

  const action = rag === "red"
    ? "Escalate for enforcement review; recommend Warning List entry."
    : rag === "amber"
      ? "Request amendments from the promoter within 14 days."
      : "Close — no action required. Log for trend monitoring.";

  // risk score derived from breach severity, floored/capped by the RAG band
  const highCount = breaches.filter(b => b.severity === "high").length;
  const medCount = breaches.filter(b => b.severity === "medium").length;
  const lowCount = breaches.length - highCount - medCount;
  let score = Math.min(100, highCount * 30 + medCount * 15 + lowCount * 5);
  if (rag === "red") score = Math.max(score, 80);
  if (rag === "green") score = Math.min(score, 12);
  if (hits.length) score = Math.max(score, 92);

  return {
    rag, category,
    verdict: String(res.summary || res.overall_summary || "Assessment complete."),
    action, score, breaches,
    company: {
      name,
      warningList: { status: warnStatus, note: warnNote },
      companiesHouse: { status: "unknown", note: "Not checked against Companies House in this triage." },
      authorised: { status: authStatus, note: authNote }
    },
    advert, source: "ai"
  };
}

/* ---- Scripted fallback (used only if the AI call fails) ---- */
function fallbackAnalysis(advert, company) {
  const t = advert.toLowerCase();
  const has = (re) => re.test(t);
  const grab = (re) => (advert.match(re) || [""])[0].trim();
  const guaranteed = has(/guarantee|risk-free|risk free|no risk/);
  const celeb = has(/elon|musk|bbc|as seen on|backed by|featured by|martin lewis/);
  const pressure = has(/spots left|only \d|before it'?s gone|act now|limited|withdraw|don'?t miss/);
  const hasWarning = has(/capital at risk|value of investments|may get back less/);
  const authorised = has(/authorised and regulated|frn|financial conduct authority/);

  const breaches = [];
  if (!hasWarning) breaches.push({ rule: "COBS 4.2.1R", title: "No risk warning", severity: "high",
    explanation: "The promotion fails to give a clear and prominent indication that capital is at risk.", quote: "" });
  if (guaranteed) breaches.push({ rule: "COBS 4.5.2R", title: "Guaranteed / risk-free claim", severity: "high",
    explanation: "Describing returns as guaranteed or risk-free is misleading and prohibited.", quote: grab(/[^.\n]*(guarantee|risk-free|risk free|no risk)[^.\n]*/i) });
  if (celeb) breaches.push({ rule: "s.21 FSMA / COBS 4.5", title: "Unsubstantiated endorsement", severity: "high",
    explanation: "Implying endorsement by a public figure or broadcaster without basis is misleading and a common scam indicator.", quote: grab(/[^.\n]*(elon|musk|bbc|as seen on|backed by|featured by|martin lewis)[^.\n]*/i) });
  if (pressure) breaches.push({ rule: "COBS 4.5.2R", title: "Pressure selling", severity: "medium",
    explanation: "Artificial urgency and scarcity pressure consumers into hasty decisions.", quote: grab(/[^.\n]*(spots left|only \d|before it'?s gone|act now|limited)[^.\n]*/i) });

  let rag = "green", score = 10, category = "Compliant — no action",
      verdict = "Appears compliant — required risk disclosures and authorisation present.",
      action = "Close — no action required.";
  if (breaches.length) {
    const high = breaches.some(b => b.severity === "high");
    rag = high ? "red" : "amber";
    score = high ? 86 : 52;
    category = celeb || guaranteed ? "Unauthorised business — suspected scam" : !hasWarning ? "Inadequate risk warning" : "Pressure selling";
    verdict = high ? "High-risk promotion with serious breaches and likely scam indicators." : "Non-compliant promotion requiring amendment.";
    action = high ? "Escalate for enforcement & add firm to Warning List review." : "Request amendments from the promoter within 14 days.";
  }
  return {
    rag, category, verdict, action, score, breaches,
    company: {
      name: company || "Unidentified promoter",
      warningList: { status: (guaranteed || celeb) ? "match" : "unknown",
        note: (guaranteed || celeb) ? "Scam-pattern match — recommend manual check against the FCA Warning List." : "No automated match; manual confirmation recommended." },
      companiesHouse: { status: authorised ? "active" : "unknown",
        note: authorised ? "Named entity appears active (verify the company number)." : "Could not confirm a registration from the advert." },
      authorised: { status: authorised ? "authorised" : "not_authorised",
        note: authorised ? "Advert states FCA authorisation with an FRN — verify on the FS Register." : "No FCA authorisation or FRN disclosed in the promotion." }
    },
    advert, source: "fallback"
  };
}

async function analyseAdvert(advert, company, context, image) {
  try {
    const res = await fetch(SCAN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ advert, advertText: advert, promoter: company || "", context: context || "", image: image || null })
    });
    if (!res.ok) throw new Error("scan failed: HTTP " + res.status);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return mapBackendToAnalysis(data, advert, company);
  } catch (err) {
    console.warn("AI triage failed, using fallback:", err);
    const fb = fallbackAnalysis(advert, company);
    fb.error = true;
    return fb;
  }
}

/* ---- relative time helper ---- */
function relTime(min) {
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} hr${h > 1 ? "s" : ""} ago`;
  return `${Math.floor(h / 24)} day${h >= 48 ? "s" : ""} ago`;
}

/* ============================================================
   SEEDED COMPLAINTS — already triaged by the agent
   ============================================================ */
function A(o) { // analysis builder with sensible defaults
  return Object.assign({ source: "seed", error: false }, o);
}

const COMPLAINTS = [
  {
    ref: "FP-2026-04918", mins: 4, reporterType: "Member of the public",
    channels: ["Social media (Instagram)"], promoter: "Quantum Yield Capital Ltd",
    authorisedClaim: "No", productTypes: ["Crypto", "Investments"],
    whenSeen: "12 Jun 2026, ~20:40", whereSeen: "Sponsored Instagram reel, @quantumyield.ai",
    reason: "It claims Elon Musk is behind it and promises guaranteed 40% a month. My uncle nearly put in £5,000.",
    advert: `🚀 ELON-BACKED CRYPTO IS HERE 🚀

QuantumYield AI turned £250 into £18,400 for early users in just 6 weeks. As seen on BBC & featured by Elon Musk.

Our algorithm GUARANTEES a minimum 40% monthly return — completely risk-free. The banks don't want you to know about this.

⏰ Only 50 spots left. Deposit today and withdraw your profits instantly. No experience needed.`,
    analysis: A({ rag: "red", score: 94, category: "Unauthorised business — suspected scam",
      verdict: "Multiple serious breaches plus strong scam indicators — fake endorsement and guaranteed returns.",
      action: "Escalate to Unauthorised Business dept; recommend Warning List entry and asset-firm takedown.",
      breaches: [
        { rule: "s.21 FSMA", title: "Unauthorised financial promotion", severity: "high", explanation: "No authorised person has approved this promotion and the firm appears unauthorised — an offence under s.21 FSMA.", quote: "" },
        { rule: "COBS 4.5.2R", title: "Guaranteed, risk-free return claim", severity: "high", explanation: "Returns described as guaranteed and risk-free are misleading and prohibited for an investment promotion.", quote: "GUARANTEES a minimum 40% monthly return — completely risk-free" },
        { rule: "COBS 4.5.2R", title: "Fake celebrity / broadcaster endorsement", severity: "high", explanation: "Implying endorsement by Elon Musk and the BBC without basis is misleading and a hallmark of investment fraud.", quote: "As seen on BBC & featured by Elon Musk" },
        { rule: "COBS 4.2.1R", title: "Pressure selling & no risk warning", severity: "medium", explanation: "Artificial scarcity with no balanced indication that capital is at risk.", quote: "Only 50 spots left. Deposit today and withdraw your profits instantly." }
      ],
      company: { name: "Quantum Yield Capital Ltd",
        warningList: { status: "match", note: "Name and aliases match two existing unauthorised-firm alerts." },
        companiesHouse: { status: "not_found", note: "No active UK registration found for this exact name." },
        authorised: { status: "not_authorised", note: "Not on the Financial Services Register; not authorised to promote investments." } },
      advert: "" })
  },
  {
    ref: "FP-2026-04915", mins: 23, reporterType: "Member of the public",
    channels: ["Social media (TikTok)"], promoter: "Apex Trading Mentors",
    authorisedClaim: "Unsure", productTypes: ["Investments", "Financial advice"],
    whenSeen: "12 Jun 2026, afternoon", whereSeen: "TikTok video, @apexmentors",
    reason: "A 'finfluencer' says he'll teach me to make £30k a month trading. Seems too good to be true.",
    advert: `Tired of the 9-5? 💸

I went from broke to £30k/month trading forex and now I'm teaching 12 students to do the same. My signals have a 94% win rate.

Most people will scroll past this and stay poor. The 1% take action.

DM me "FREEDOM" and I'll send you my free starter pack. Spots are limited — serious people only.

Capital at risk. This is not financial advice.`,
    analysis: A({ rag: "amber", score: 58, category: "Unbalanced promotion / pressure selling",
      verdict: "A risk warning is present but the promotion is unbalanced, with unverifiable performance claims and pressure tactics.",
      action: "Request substantiation of the 94% claim and amendments; monitor for unauthorised advice.",
      breaches: [
        { rule: "COBS 4.5.2R", title: "Unsubstantiated performance claim", severity: "medium", explanation: "A '94% win rate' and specific income figures are presented without evidence or balance.", quote: "My signals have a 94% win rate" },
        { rule: "COBS 4.2.1R", title: "Unbalanced / pressure selling", severity: "medium", explanation: "Shaming language and scarcity undermine a fair, clear and not misleading communication despite the small-print warning.", quote: "Most people will scroll past this and stay poor. The 1% take action." }
      ],
      company: { name: "Apex Trading Mentors",
        warningList: { status: "unknown", note: "No current Warning List entry; trading-style name not yet matched." },
        companiesHouse: { status: "unknown", note: "Trading name only — no incorporated entity identified in the complaint." },
        authorised: { status: "unknown", note: "Authorisation could not be confirmed; possible unauthorised advice." } },
      advert: "" })
  },
  {
    ref: "FP-2026-04902", mins: 67, reporterType: "Firm (compliance)",
    channels: ["Website", "Search engine advert"], promoter: "Goldsmith Capital Partners (clone)",
    authorisedClaim: "Yes", productTypes: ["Investments", "Pensions"],
    whenSeen: "11 Jun 2026", whereSeen: "Paid Google result → goldsmith-capital-partners.com",
    reason: "This website is using our FRN and firm name but it is not us. We believe it is a clone.",
    advert: `Goldsmith Capital Partners — FCA Authorised (FRN 142087)

Secure 8.4% fixed annual returns with our Capital Growth Bond. Fully covered by the FSCS. Trusted by over 12,000 UK investors.

Transfer your pension today and lock in your rate before the offer closes on 30 June.`,
    analysis: A({ rag: "red", score: 90, category: "Clone firm — suspected scam",
      verdict: "Likely clone of an authorised firm misusing a genuine FRN, with misleading 'fixed return' and FSCS claims.",
      action: "Escalate to clone-firm response; publish a Warning List alert and notify the genuine firm.",
      breaches: [
        { rule: "s.21 FSMA", title: "Clone of an authorised firm", severity: "high", explanation: "The site appears to misuse a genuine firm's name and FRN to lend false legitimacy — a clone scam.", quote: "Goldsmith Capital Partners — FCA Authorised (FRN 142087)" },
        { rule: "COBS 4.5.2R", title: "Misleading 'fixed return' & FSCS claim", severity: "high", explanation: "Presenting a fixed return as secure and implying full FSCS cover misrepresents the risk.", quote: "Secure 8.4% fixed annual returns with our Capital Growth Bond. Fully covered by the FSCS." },
        { rule: "COBS 4.2.1R", title: "Pension-transfer pressure", severity: "medium", explanation: "Urging a pension transfer against a deadline with no risk balance is high-harm pressure selling.", quote: "Transfer your pension today and lock in your rate before the offer closes" }
      ],
      company: { name: "Goldsmith Capital Partners (clone)",
        warningList: { status: "match", note: "Matches an open clone-firm investigation for this FRN." },
        companiesHouse: { status: "active", note: "Genuine entity active (No. 07731902); the website is not operated by it." },
        authorised: { status: "not_authorised", note: "The cloned website is not the authorised firm; FRN is being misused." } },
      advert: "" })
  },
  {
    ref: "FP-2026-04887", mins: 142, reporterType: "Member of the public",
    channels: ["Mobile app"], promoter: "Swiftli Pay Ltd",
    authorisedClaim: "Yes", productTypes: ["Buy Now Pay Later", "Consumer credit"],
    whenSeen: "11 Jun 2026", whereSeen: "Checkout screen in the Swiftli shopping app",
    reason: "It pushes 'pay later' really hard at checkout and I couldn't find any mention of what happens if you miss a payment.",
    advert: `Split it. Smile more. 😊

Pay in 4 interest-free instalments with Swiftli — the smarter way to shop. No fees, ever.

Most shoppers choose Swiftli at checkout. Tap to pay later and keep your cash.`,
    analysis: A({ rag: "amber", score: 47, category: "Inadequate risk information",
      verdict: "Trivialises credit and omits the consequences of missed payments and affordability information.",
      action: "Request addition of missed-payment consequences and balanced prominence; 14-day amend.",
      breaches: [
        { rule: "CONC 3 / COBS 4.2.1R", title: "Omits missed-payment consequences", severity: "medium", explanation: "A credit promotion must not omit the risks; there is no mention of what happens if instalments are missed.", quote: "No fees, ever." },
        { rule: "COBS 4.2.1R", title: "Trivialising credit", severity: "low", explanation: "Light, emotive framing encourages borrowing without conveying that this is a credit agreement.", quote: "Split it. Smile more." }
      ],
      company: { name: "Swiftli Pay Ltd",
        warningList: { status: "clear", note: "No Warning List match." },
        companiesHouse: { status: "active", note: "Active and registered (No. 11920455)." },
        authorised: { status: "authorised", note: "Authorised for consumer credit; check BNPL permissions scope." } },
      advert: "" })
  },
  {
    ref: "FP-2026-04861", mins: 320, reporterType: "Member of the public",
    channels: ["Newspaper"], promoter: "Northbridge Investments plc",
    authorisedClaim: "Yes", productTypes: ["Investments"],
    whenSeen: "10 Jun 2026", whereSeen: "Full-page ad, weekend money section",
    reason: "Reporting just in case — wanted to check it's legitimate before I invest my ISA allowance.",
    advert: `Open a Stocks & Shares ISA with Northbridge Investments.

Invest from £100 a month in a diversified range of funds. Capital at risk — the value of investments can go down as well as up and you may get back less than you invest.

Tax treatment depends on your individual circumstances and may change in the future. This is not financial advice; if you are unsure, seek independent advice.

Northbridge Investments plc is authorised and regulated by the Financial Conduct Authority (FRN 482910).`,
    analysis: A({ rag: "green", score: 8, category: "Compliant — no action",
      verdict: "Appears compliant: prominent risk warning, balanced tone and clear FCA authorisation.",
      action: "Close — no action required. Log for trend monitoring.",
      breaches: [],
      company: { name: "Northbridge Investments plc",
        warningList: { status: "clear", note: "No Warning List match." },
        companiesHouse: { status: "active", note: "Active and registered (No. 03482910)." },
        authorised: { status: "authorised", note: "Authorised and regulated by the FCA; FRN 482910 verified." } },
      advert: "" })
  }
];
// attach advert text into each analysis so highlights resolve
COMPLAINTS.forEach(c => { c.analysis.advert = c.advert; });

/* a complaint that ARRIVES live and is triaged by the agent on load */
const INCOMING = {
  ref: "FP-2026-04921", mins: 0, reporterType: "Member of the public",
  channels: ["Social media (Facebook)"], promoter: "BritWealth Recovery",
  authorisedClaim: "No", productTypes: ["Investments", "Claims management"],
  whenSeen: "13 Jun 2026, just now", whereSeen: "Facebook group 'UK Crypto Refunds'",
  reason: "They messaged me saying they can recover the money I lost in a scam, but they want a £400 fee upfront.",
  advert: `LOST MONEY TO A SCAM? WE CAN GET IT BACK. 💷

BritWealth Recovery has helped 4,000+ victims reclaim 100% of their losses — GUARANTEED or your money back.

Government-approved recovery specialists. We've recovered over £30M.

Pay a small £400 release fee and we'll wire your full refund within 48 hours. Act now — your case expires in 24 hours.`
};

/* raw complaints sitting in the INBOX for the background agent to triage live */
const INBOX = [
  {
    ref: "FP-2026-04920", mins: 6, reporterType: "Member of the public",
    channels: ["Search engine advert"], promoter: "Sterling Bridge Bonds",
    authorisedClaim: "Unsure", productTypes: ["Investments"],
    whenSeen: "13 Jun 2026", whereSeen: "Top Google result for 'best fixed savings'",
    reason: "Advertises 9% guaranteed savings which seems way above the high street. Is this real?",
    advert: `Earn 9.2% FIXED every year — guaranteed.\n\nSterling Bridge Mini-Bonds pay a fixed 9.2% annual income, paid monthly. Your capital is secure and your returns are locked in for 3 years.\n\nThousands of UK savers have already switched. Open in 5 minutes — limited March allocation remaining.`
  },
  {
    ref: "FP-2026-04919", mins: 11, reporterType: "Firm (compliance)",
    channels: ["Social media (Instagram)"], promoter: "@luxe.trades",
    authorisedClaim: "No", productTypes: ["Crypto", "Investments"],
    whenSeen: "13 Jun 2026", whereSeen: "Instagram story, swipe-up link",
    reason: "A 19-year-old 'trader' flexing supercars telling kids to copy his crypto trades for a fee.",
    advert: `STOP being broke. \u{1F4B0}\n\nI made £42,000 last month copy-trading crypto from my phone. My VIP signals group is now OPEN.\n\nJust £99/month and you mirror every trade I make. Last month members 10x'd their accounts.\n\nLink in bio — first 100 only. No risk, just gains. \u{1F680}`
  },
  {
    ref: "FP-2026-04917", mins: 18, reporterType: "Member of the public",
    channels: ["Email / post"], promoter: "Meridian Life Cover",
    authorisedClaim: "Yes", productTypes: ["Insurance"],
    whenSeen: "12 Jun 2026", whereSeen: "Direct email",
    reason: "Over-50s life insurance email. Wanted it checked but looks fairly standard to me.",
    advert: `Over 50? Get guaranteed acceptance life cover from £7 a month.\n\nNo medical needed. Leave a cash gift to your loved ones. Plus a free £75 gift card just for taking out a policy.\n\nMeridian Life Cover is authorised and regulated by the Financial Conduct Authority. Over 24 months your premiums may total more than the cash sum paid out; this is not a savings plan. Terms apply.`
  }
];

Object.assign(window, { COMPLAINTS, INBOX, INCOMING, SCAN_STEPS, analyseAdvert, relTime, loadRulebook, RULEBOOK, fetchSavedComplaints, saveComplaint });
