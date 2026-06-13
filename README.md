# UKFinnovatorT2 — FCA Promotions Triage Console

**Challenge:** Cambridge Spark — Financial Regulation in an AI-Driven World  
**Theme:** Regulatory Compliance / RegTech  
**Hackathon:** UKFin+ Innovator, 13–14 June 2026

---

## The idea

An AI tool that reads a financial advert and instantly tells you if it breaks FCA rules, which rule it breaks, and whether the company behind it is a known scam.

**Why it matters:** AI now lets anyone produce thousands of slick financial adverts in minutes — fake celebrity crypto ads, dodgy finfluencer "get rich quick" posts. Someone has to check every one of those against the FCA rulebook. Today that checking is done by hand, slowly. It cannot keep up with machines making ads at scale.

**What the tool does:** Paste in an advert and in seconds it shows you:

- A red, amber, or green compliance status
- The exact rule it breaks (e.g. no risk warning → COBS 4)
- The precise words in the ad that triggered the breach
- Whether the company is on the FCA's official Warning List + Companies House check

**Who pays for it:** Not just the regulator — the firms. By law, any firm that signs off a financial advert must keep checking it stays compliant and re-confirm every 3 months. We automate that chore. Every regulated firm running ads is a potential customer.

---

## Stack

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
- **Backend:** Serverless API route (`/api/scan`) calling the Anthropic API
- **Deployment:** Vercel
- **Data:** Local `warninglist.json` (fictional scam firms for demo); FCA Financial Services Register API for live authorisation checks

---

## Getting started

```bash
git clone https://github.com/LingSX0916/UKFinnovatorT2.git
cd UKFinnovatorT2
npm install
```

Create a `.env.local` file:

```
ANTHROPIC_API_KEY=your_key_here
```

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Build sequence

| Step | Task | Time |
|------|------|------|
| 1 | Scaffold — Next.js app, header, textarea, Scan button, empty results area | 15 min |
| 2 | `/api/scan` route + rules engine system prompt | 60 min |
| 3 | Results card — RAG banner, per-rule rows with verdict pills and quoted evidence | 45 min |
| 4 | Batch triage view + aggregate dashboard (total scanned, % non-compliant, top breach) | 90 min |
| 5 | Warning List cross-check against `warninglist.json` | 30 min |
| 6 | Screenshot scanning via vision (image upload → transcribe → scan) | 45 min |
| 7 | Polish pass — loading states, empty states, footer citing rule sources | 30 min |

---

## Rules engine (8 FCA rules)

The system prompt encodes these rules and forces structured JSON output:

| Rule | Provision | What triggers a FAIL |
|------|-----------|----------------------|
| R1 — Authorisation | s21 FSMA 2000; COBS 4.10 | Promotion by an unauthorised person with no FCA-authorised firm named |
| R2 — Fair, clear and not misleading | COBS 4.2.1R | Guaranteed/overstated returns, "risk-free", unsubstantiated claims |
| R3 — Balanced presentation | COBS 4.5A; FG24/1 | Returns prominent, risk absent or buried; FOMO pressure tactics |
| R4 — Prominent risk warning | FG24/1 | Risk warning missing, truncated, or hidden behind "see more" |
| R5 — Standalone compliance | FG24/1 | Promotion relies on a bio link or separate page for key information |
| R6 — Crypto/high-risk prescribed warning | COBS 4.12A; FG23/3 | Crypto advert missing the exact prescribed FCA warning text |
| R7 — Identify as promotion + disclose affiliation | FG24/1 | Promotion disguised as neutral content; undisclosed paid endorsement |
| R8 — No false regulatory/protection claims | COBS 4.5A; Principle 7 | False "FCA approved" or "FSCS protected" or "capital guaranteed" |

**Verdict logic:**  
- **RED** — any FAIL on R1, R2, R6, or R8; or two or more FAILs anywhere  
- **AMBER** — one FAIL on R3, R4, R5, or R7; or multiple FLAGs  
- **GREEN** — all PASS or minor FLAGs only

---

## Demo adverts

Three fictional adverts engineered to exercise distinct rule paths:

**Green (clean PASS):** Authorised firm + FRN, balanced risk warning, no overstated returns, identified as a promotion.

**Amber (borderline):** Authorised firm, but past performance headlined ("18% last year"), FOMO language ("don't miss out, investors are piling in"), no "past performance is not a guide to future returns".

**Red (showstopper):** Unauthorised promotion, false "FCA approved", guaranteed returns ("300%", "zero risk"), no prescribed crypto warning, and the named firm ("CoinVault Pro") matches the Warning List — triggering the red alert badge.

---

## Pitch deck outline (6 slides, 5 minutes)

1. **Hook** — 19,766 promotions amended or withdrawn by the FCA in 2024 (+97.5%). Most reviewed by hand.
2. **The gap** — No AI-specific rulebook; manual review cannot scale while generative AI mass-produces scams.
3. **Live demo** — Clean PASS → borderline AMBER → red showstopper with Warning List badge + batch triage view.
4. **Maps to the rule** — FG24/1, COBS 4.2.1R, COBS 4.12A, s21 FSMA, Warning List.
5. **Adoption path** — FCA AI Lab, Supercharged Sandbox; FCA reviewed ~480,000 sites in 2024.
6. **What's next** — Live Warning List integration, vision on video reels, feedback loop into FCA enforcement queue.

---

## Key FCA references

- [FG24/1 Financial promotions on social media](https://www.fca.org.uk/publications/finalised-guidance/fg24-1-finalised-guidance-financial-promotions-social-media)
- [FG23/3 Cryptoasset promotions guidance](https://www.fca.org.uk/publications/fg23-3-finalised-non-handbook-guidance-cryptoasset-financial-promotions)
- [COBS 4 — Communicating with clients](https://www.handbook.fca.org.uk/handbook/COBS/4/)
- [COBS 4.2.1R — Fair, clear and not misleading](https://www.handbook.fca.org.uk/handbook/COBS/4/2.html)
- [COBS 4.12A — Restricted Mass Market Investments / crypto](https://www.handbook.fca.org.uk/handbook/COBS/4/12A.html)
- [s21 FSMA 2000 — Financial promotion restriction](https://www.legislation.gov.uk/ukpga/2000/8/section/21)
- [FG22/5 Consumer Duty guidance](https://www.fca.org.uk/publication/finalised-guidance/fg22-5.pdf)

---

## Team

Victor · Pallavi · Raghav · Utkarsh · Jiad · Brandon

GitHub: [CRaghav21](https://github.com/CRaghav21) · [PallaviPatil-2458](https://github.com/PallaviPatil-2458)
