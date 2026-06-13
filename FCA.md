# 🏗️ FCA Financial Promotions Triage — Rules Engine and Model Training Reference

**Version.** 2.0
**Date.** 13 June 2026
**Scope of demo.** Investments and cryptoassets. The engine is modular and extends to credit, mortgages, insurance and banking by swapping the relevant sourcebook.

---

## 0. 📖 How to train the model with this file

This file is the system-prompt grounding for the triage model. It is built so the model can learn the exact line between compliant and non-compliant.

- **The teaching material is the minimal pairs.** Every rule below has a 🔴 or 🟠 non-compliant example and a 🟢 compliant example of the same thing. Paste these pairs into the system prompt. A model learns a boundary far better from a matched pass and fail than from a definition.
- **The phrase bank in section 8** tells the model which words to flag and, just as important, which look risky but are fine. This stops the model over-firing.
- **The decision logic in section 9** tells the model how to turn per-rule verdicts into one overall verdict.
- **The model must always cite the provision and quote the exact offending phrase.** No verdict without evidence. That is the transparency the brief asks for.

---

## 1. 🚦 The verdict scale

Every advert resolves to one of three verdicts.

| Verdict | Plain meaning | Legal status |
|---|---|---|
| 🔴 **RED** | Illegal, or a breach so severe the advert cannot run. Showstopper. | Unlawful under s21 FSMA, or a fundamental breach of the master rule or the crypto and high-risk regime |
| 🟠 **AMBER** | Lawful but breaks the financial promotion rules. Fixable. | Lawful under s21 but non-compliant with COBS rules on prominence, balance or performance |
| 🟢 **GREEN** | Compliant on a standalone basis. | Lawful and compliant |

**The distinction that wins marks.** An **illegal** promotion breaches s21, for example an unauthorised influencer with no approval and no exemption. A **non-compliant** promotion is lawful under s21 but breaks a COBS rule, for example an authorised firm whose risk warning is hidden. **Confidence high**, drawn straight from FG24/1 paragraphs 2.6 and 2.7. The whole pitch rests on the model holding this line.

---

## 2. ⚡ Compliant vs non-compliant at a glance

One row per rule. This is the gestalt the model should hold in mind. Detail and examples follow in section 6.

| ID | 🟢 Compliant looks like | 🔴🟠 Non-compliant looks like | Severity |
|---|---|---|---|
| R1 | Capital at risk, you could lose all you invest | Guaranteed, risk-free, zero risk, capital protected | 🔴 |
| R2 | Authorised and regulated by the FCA, FRN shown, and true | FCA approved, FCA endorsed, when untrue or implying endorsement | 🔴 |
| R3 | Crypto or high-risk advert carries the correct prescribed warning | Crypto or high-risk advert with no prescribed warning at all | 🔴 |
| R4 | Free research tools for all users | Cashback, sign-up bonus, free crypto, refer a friend reward | 🔴 |
| R5 | Firm is on the FCA Register | Firm, domain or person matches the FCA Warning List | 🔴 |
| R6 | Promotion approved by a named authorised firm | Unauthorised poster, no approver, no exemption | 🔴 |
| R7 | Mini-bond shown only to certified sophisticated investors | Mini-bond or unlisted fund mass-marketed to ordinary retail | 🔴 |
| R8 | Warning fully visible without any click | Warning hidden behind see more or cut off | 🟠, 🔴 for high-risk |
| R9 | Warning on screen inside the video | Warning only in the caption under the video | 🟠 |
| R10 | Warning on every slide and for the whole video | Warning only on the last slide or end of the video | 🟠 |
| R11 | Past return with reliability warning, period and source | Past return as the headline, no warning, no period | 🟠 |
| R12 | Forecast with reasonable basis and a not-reliable warning | Bold future return claim with no warning or basis | 🟠 |
| R13 | Benefits stated alongside the relevant risks | All upside, no mention of risk | 🟠 |
| R14 | Tax benefit plus depends on your circumstances and may change | Tax-free or save tax with no caveat | 🟠 |
| R15 | Tipster discloses the holding or payment and labels the ad | Repeated tipping, presented as expert, no disclosure | 🟠 |
| R16 | Full warning, the Take 2 mins link, and the approver FRN | Shortened warning where the full one fits, link or FRN missing | 🟠 |
| R17 | Approver firm and approval date shown | Approved retail advert with no approver named | 🟠 |

---

## 3. ✅ The GREEN pass checklist

An advert is GREEN only if it clears all of these. If any item fails, it is AMBER or RED per the rule.

1. **No guarantee or no-risk language** on a capital-at-risk product. (R1)
2. **No false or implied FCA approval or endorsement.** (R2)
3. **The correct prescribed risk warning is present** if it is crypto or high-risk, and it is the right variant for the product type. (R3)
4. **No incentive to invest.** (R4)
5. **The firm is not on the Warning List.** (R5)
6. **It is lawfully communicated**, either by an authorised firm or approved by one and the approver named, or covered by an exemption. (R6, R17)
7. **The warning is prominent, complete, unobscured and shown throughout**, not in a caption, not behind see more, not only on the last slide. (R8, R9, R10)
8. **Any performance claim carries its warning** and the past or future rules are met. (R11, R12)
9. **Benefits are balanced by the relevant risks.** (R13)
10. **Any tax claim carries the circumstances caveat.** (R14)
11. **Any recommendation discloses conflicts and is presented objectively.** (R15)

---

## 4. ⚖️ The rules engine

Each rule is self-contained. Read the minimal pair and the phrase lists. The 9 demo-core rules are marked ⭐.

### 🔴 RED rules (illegal or severe)

---

#### ⭐ R1. Guaranteed or risk-free returns 🔴

**The rule.** A product that places capital at risk must never be described as guaranteed, risk-free, protected or secure.
**Provision.** COBS 4.2.5G and COBS 4.2.1R.
**❌ Fails if the advert says.** guaranteed, guaranteed returns, risk-free, zero risk, no risk, 100% safe, cannot lose, can't lose, capital protected, capital guaranteed, secure returns, locked-in profit, fixed guaranteed income.
**✅ Does not fail just because it says.** capital at risk, your capital is at risk, returns are not guaranteed, you could lose all the money you invest, past performance is no guide, target return, projected return.
**🔴 Non-compliant.** "Earn 12% a year, guaranteed. Your capital is 100% protected."
**🟢 Compliant.** "Target return 12% a year. Capital at risk. You could lose all the money you invest."
**Quote as evidence.** the guarantee or no-risk phrase.
**Fix.** Remove the guarantee and protection language. State the capital-loss risk plainly.

---

#### ⭐ R2. False or unverified FCA status 🔴

**The rule.** The FCA does not approve products. Its name must never be used to suggest it endorses or approves a firm, product or promotion. Claiming authorisation that the firm does not hold is a breach.
**Provision.** GEN 4.3.1R, COBS 4.5A.16R, s21 FSMA.
**❌ Fails if the advert says.** FCA approved, FCA endorsed, approved by the FCA, authorised by the FCA when not on the Register, FCA regulated when not, backed by the regulator, the FCA recommends, government approved investment.
**✅ Does not fail just because it says.** Authorised and regulated by the Financial Conduct Authority, FRN 123456, where the firm genuinely holds that FRN, or, This financial promotion has been approved by Beta Compliance Ltd, FRN 654321, naming the real s21 approver.
**🔴 Non-compliant.** "FCA approved investment. Backed by the regulator. Totally safe."
**🟢 Compliant.** "Issued by Acme Ltd. This financial promotion has been approved by Beta Compliance Ltd, FRN 654321."
**Quote as evidence.** the FCA-status claim.
**Fix.** Delete any claim of FCA approval or endorsement. Show only a true authorisation or approval statement with the correct FRN.

---

#### ⭐ R3. No prescribed risk warning on a crypto or high-risk promotion 🔴

**The rule.** A promotion of crypto, P2P, non-readily-realisable securities or a long-term asset fund must carry the prescribed risk warning for that exact product type. None present means RED.
**Provision.** COBS 4.12A.10R and COBS 4.12A.11R. Exact wording is in section 7.
**❌ Fails if.** the advert promotes one of those products and contains none of the four prescribed warnings, in any form.
**✅ Compliant if.** the correct prescribed warning for the product type is present and prominent.
**🔴 Non-compliant.** A TikTok promoting a token. "Buy SolanaX now, the next 100x. Link in bio." No warning anywhere.
**🟢 Compliant.** Same post with the crypto warning fixed across the top. "Don't invest unless you're prepared to lose all the money you invest. This is a high-risk investment and you should not expect to be protected if something goes wrong."
**Quote as evidence.** state that no prescribed warning is present.
**Fix.** Add the prescribed warning for the product type, displayed prominently for the duration.

---

#### ⭐ R4. Incentive to invest 🔴

**The rule.** A promotion of a restricted mass market investment must not offer any monetary or non-monetary incentive to invest. Incentives are banned outright.
**Provision.** COBS 4.12A.7R, with examples in COBS 4.12A.8G.
**❌ Fails if the advert offers.** cashback, a sign-up bonus, a deposit bonus, a refer-a-friend reward, free crypto, free shares for joining, a free gift such as a laptop or phone, discounts or rebates linked to how much you trade, any free or bonus investment.
**✅ Does not fail.** information and research tools, lower fees not linked to trade volume that are available to all clients, or an incentive offered solely to transfer an existing holding between platforms.
**🔴 Non-compliant.** "Deposit £100 and get £20 in free Bitcoin. Refer a friend for another £50."
**🟢 Compliant.** "Free market data and charting tools for every user." This is not an incentive to invest.
**Quote as evidence.** the incentive offer.
**Fix.** Remove the bonus, cashback, free asset or referral reward entirely.

---

#### ⭐ R5. Firm or individual on the FCA Warning List 🔴

**The rule.** If the promoting firm, trading name, domain or named individual matches the FCA Warning List, treat the advert as a scam showstopper.
**Provision.** s21 FSMA context. See section 8 for the matching logic and section 9 for how a hit forces the overall verdict.
**❌ Fails if.** the name, domain or person matches, or near-matches, an entry on the local Warning List dataset.
**🔴 Non-compliant.** Any advert from a firm whose name appears on the Warning List.
**Quote as evidence.** the matched name and the Warning List entry.
**Fix.** This is not a fixable advert. The firm is operating without permission. Escalate.
**Data note.** Roughly two thirds of the illegal ads in the FCA April 2026 action came from firms already on this list. **Confidence high.** This is the answer that proves the tool is regulator-grade and not a chatbot.

---

#### R6. Illegal unauthorised promotion 🔴

**The rule.** An unauthorised person communicating a financial promotion in the course of business, with no authorised approver and no exemption, is committing a criminal offence under s21.
**Provision.** s21 FSMA, FG24/1 chapters 2 and 4.
**❌ Fails if.** the communicator is not authorised, no approving firm or FRN is named, and there is a clear commercial interest, for example a paid finfluencer or an affiliate link, with no exemption evident.
**✅ Compliant if.** the same content is approved by a named authorised firm, or the communicator is themselves authorised, or a clear exemption applies.
**🔴 Non-compliant.** A paid influencer post. "Use code MAX for 10% off your first trade with [unregulated broker]." No approver, paid partnership.
**🟢 Compliant.** Same post carrying "Approved by Beta Compliance Ltd, FRN 654321" from a real authorised approver.
**Quote as evidence.** the absence of an approver plus the commercial-interest signal.
**Fix.** Have an authorised firm approve the promotion, or rely on a valid FPO exemption.
**Severity note.** Up to 2 years imprisonment and an unlimited fine, per FG24/1 2.6.

---

#### R7. Banned mass-marketing 🔴

**The rule.** Non-mass-market investments, for example speculative illiquid securities such as mini-bonds, and non-mainstream pooled investments, must not be mass-marketed to ordinary retail investors.
**Provision.** COBS 4.12B.6R.
**❌ Fails if.** one of those products is promoted openly to the general public, with no gating to certified high-net-worth or sophisticated investors.
**✅ Compliant if.** the promotion is restricted to and directed only at certified or self-certified sophisticated or high-net-worth investors, with the categorisation steps applied.
**🔴 Non-compliant.** An open Instagram ad. "Invest in our 8% property mini-bond. Anyone can join from £500."
**🟢 Compliant.** The same mini-bond promoted only to investors who have completed the sophisticated or high-net-worth investor statement.
**Quote as evidence.** the open-to-all framing.
**Fix.** Restrict the audience and apply investor categorisation, or do not promote on open social media.

---

### 🟠 AMBER rules (lawful but non-compliant)

---

#### ⭐ R8. Risk warning truncated or obscured 🟠

**The rule.** A required warning must be visible without any click or optional action and must not be hidden by a platform design feature.
**Provision.** FG24/1 2.29, 2.30, 2.43, COBS 4.12A.36R, COBS 4.12A.38R.
**❌ Fails if.** the warning sits behind see more, an ellipsis, a fold, or is cut off, faded, or in a colour that blends into the background.
**✅ Compliant if.** the full warning is visible up front with no interaction needed.
**🟠 Non-compliant.** A Facebook post where the warning reads "Don't invest unless you're prepared to lose... see more".
**🟢 Compliant.** The full warning shown in the visible body of the post with no truncation.
**Quote as evidence.** the truncated fragment.
**Fix.** Show the full warning without any click. Increase contrast and size.
**Escalation.** This becomes 🔴 RED for a high-risk investment, where FG24/1 2.43 says the warning must not be truncated at all. **Confidence moderate** on the exact escalation threshold, since it is a reading of how to tier the guidance.

---

#### ⭐ R9. Risk warning in the caption, not the body 🟠

**The rule.** Where benefits are inside the video or image, the risk warning must also be inside that content, not only in the caption.
**Provision.** FG24/1 2.27, 2.45.
**❌ Fails if.** all the upside is in the video or image while the risk warning sits only in the caption underneath.
**✅ Compliant if.** the warning appears on screen within the video or image itself.
**🟠 Non-compliant.** A reel showing lifestyle clips and big return numbers, with the warning only in the caption below the video.
**🟢 Compliant.** The same reel with the warning displayed on screen across the footage.
**Quote as evidence.** note that the warning is caption-only.
**Fix.** Burn the warning into the on-screen content.

---

#### R10. Warning not shown throughout 🟠

**The rule.** The warning must appear on every slide of a carousel that carries the promotion, and for the duration of the relevant part of a video, not only at the end.
**Provision.** FG24/1 Table 1, COBS 4.12A.36R(2).
**❌ Fails if.** the warning appears only on the last carousel slide, or only in the final seconds or end card of a video.
**✅ Compliant if.** the warning is on every relevant slide and held on screen for the whole promotional section.
**🟠 Non-compliant.** A five-slide carousel with the warning only on slide five.
**🟢 Compliant.** The same carousel with the warning fixed on every slide.
**Quote as evidence.** note the warning placement.
**Fix.** Repeat the warning on every slide and hold it on screen throughout the video.

---

#### ⭐ R11. Past performance without warning 🟠

**The rule.** A past return must carry the warning that past performance is not a reliable indicator of future results, must not be the most prominent feature, and must state the period and source. Where available it should cover five complete years.
**Provision.** COBS 4.5A.10R for MiFID business, COBS 4.6.2R for non-MiFID.
**❌ Fails if.** a past return is quoted with no reliability warning, or it is the headline, or the period and source are missing.
**✅ Compliant if.** the warning, the period and the source are present and the figure is not the dominant element.
**🟠 Non-compliant.** "Our fund returned 18% last year." Shown as the giant headline, no warning, no period.
**🟢 Compliant.** "Past performance. The fund returned 18% over the year to 31 December 2025, source Acme. Past performance is not a reliable indicator of future results." Shown in normal-sized text, not the headline.
**Quote as evidence.** the past-return figure.
**Fix.** Add the reliability warning, the period and the source, and reduce the prominence of the figure.

---

#### ⭐ R12. Future performance without warning 🟠

**The rule.** A forward projection must rest on reasonable assumptions, show both positive and negative scenarios where required, must not be based on simulated past performance, and must carry a prominent warning that forecasts are not a reliable indicator of future performance.
**Provision.** COBS 4.5A.14R for MiFID business, COBS 4.6.7R for non-MiFID.
**❌ Fails if.** a future return is asserted with no warning and no reasonable basis, for example a bare projected growth number.
**✅ Compliant if.** the projection is supported and carries the not-reliable warning, or there is simply no unsupported forward claim.
**🟠 Non-compliant.** "Set to grow 30% next year. Get in before everyone else."
**🟢 Compliant.** Either drop the forward claim, or, for an eligible instrument, present scenarios with the warning. "Forecasts are not a reliable indicator of future performance."
**Quote as evidence.** the forward-return claim.
**Fix.** Remove unsupported projections, or add a reasonable basis, scenarios and the warning.

---

#### ⭐ R13. Lacks balance 🟠

**The rule.** A promotion must give a balanced view. Benefits must be set against the relevant risks. All upside and no risk is not fair, clear and not misleading.
**Provision.** COBS 4.2.1R, FG24/1 2.23, 2.32.
**❌ Fails if.** the advert promotes benefits or returns and makes no mention of any risk.
**✅ Compliant if.** the relevant risks sit alongside the benefits.
**🟠 Non-compliant.** "Grow your money fast with our high-yield fund. Smart investors are already in."
**🟢 Compliant.** "Aim to grow your money with our fund. The value can fall as well as rise and you may get back less than you invest."
**Quote as evidence.** the unbalanced benefit claim.
**Fix.** Add the relevant risks next to the benefits.

---

#### R14. Tax claim without caveat 🟠

**The rule.** Any reference to tax treatment must state that it depends on individual circumstances and may change in the future.
**Provision.** COBS 4.5.7R for non-MiFID, COBS 4.5A.8R for MiFID.
**❌ Fails if.** the advert claims a tax benefit, for example tax-free returns, with no caveat.
**✅ Compliant if.** the circumstances-and-may-change caveat is shown prominently.
**🟠 Non-compliant.** "Enjoy completely tax-free returns on your investment."
**🟢 Compliant.** "Returns may be tax-free. Tax treatment depends on your individual circumstances and may change in the future."
**Quote as evidence.** the tax claim.
**Fix.** Add the tax caveat.

---

#### ⭐ R15. Undisclosed conflict on a recommendation 🟠

**The rule.** A finfluencer who repeatedly tips an investment and presents as an expert is making an investment recommendation. It must be presented objectively and any conflict of interest must be disclosed. The ASA also requires the content to be labelled as an ad up front.
**Provision.** MAR Article 20, COBS 12.4, FG24/1 4.8, plus the ASA CAP Code.
**❌ Fails if.** the poster repeatedly recommends a coin or stock, presents as having financial expertise, and does not present the information objectively or disclose that they hold the asset or are being paid, or does not label the ad.
**✅ Compliant if.** the recommendation is balanced and objective, the holding or payment is disclosed, and the content is labelled as an ad.
**🟠 Non-compliant.** A self-styled crypto expert posts daily. "This is the coin that will change your life, I'm all in." No disclosure that they hold a large position, no ad label.
**🟢 Compliant.** The same person discloses "I hold this asset. Paid partnership. #ad" and presents the case in a balanced way with the risks.
**Quote as evidence.** the tipping language plus the missing disclosure.
**Fix.** Disclose the conflict, present objectively, label the ad.
**Why it matters.** This checks something genuinely beyond the obvious. **Confidence high** that it separates you from teams that only check for risk warnings.

---

#### R16. Wrong or incomplete digital warning 🟠

**The rule.** On digital media the warning must be the full version unless the platform character limit is exceeded, must include the Take 2 mins to learn more link, and the approver FRN must be shown where relevant.
**Provision.** COBS 4.12A.11R(2), COBS 4.12A.11R(3), COBS 4.5.2AR.
**❌ Fails if.** a shortened warning is used where the full one fits, or the digital advert is missing the Take 2 mins to learn more link, or the approver FRN is missing.
**✅ Compliant if.** the full warning, the link and the FRN are all present.
**🟠 Non-compliant.** A web banner with room for the full warning but showing only "Don't invest unless you're prepared to lose all the money you invest." No link.
**🟢 Compliant.** The full four-sentence warning plus "Take 2 mins to learn more" linking to the risk summary, with the approver FRN shown.
**Quote as evidence.** the shortened or incomplete warning.
**Fix.** Use the full warning, add the link, show the FRN.

---

#### R17. Missing approver disclosure 🟠

**The rule.** An approved promotion likely to reach retail clients must name the approving firm and the date of approval.
**Provision.** COBS 4.5.2R(1) and COBS 4.5.2R(1A).
**❌ Fails if.** an approved retail advert does not name the approver or show the approval date.
**✅ Compliant if.** both the approver name and the approval date appear.
**🟠 Non-compliant.** A retail investment advert with a risk warning but no approver named anywhere.
**🟢 Compliant.** The same advert showing "Approved by Beta Compliance Ltd on 1 June 2026."
**Quote as evidence.** note the missing approver detail.
**Fix.** Add the approver name and the approval date.

---

## 5. 🧠 Reading order for the model

For each advert the model should, in order.

1. Identify the **product type**, crypto, P2P, NRRS, LTAF, mainstream investment, or unknown. This decides which prescribed warning applies.
2. Identify the **communicator status**, authorised, approved by a named firm, or unauthorised. This decides R6.
3. Run the **Warning List check**. This decides R5.
4. Run **all rules R1 to R17**, recording for each one triggered true or false, severity, the exact evidence phrase, and the provision.
5. **Aggregate** using section 9.

---

## 6. 📜 Prescribed text library (exact strings to match)

These are mandated by regulation. Treat them as literal strings. The four warnings are different and must not be conflated. **Confidence high**, verbatim from COBS 4.12A.11R.

### 6.1 Full risk warnings by product type, COBS 4.12A.11R(1)

**Non-readily-realisable securities.**
> Don't invest unless you're prepared to lose all the money you invest. This is a high-risk investment and you are unlikely to be protected if something goes wrong.

**Peer-to-peer agreements or P2P portfolios.**
> Don't invest unless you're prepared to lose money. This is a high-risk investment. You may not be able to access your money easily and are unlikely to be protected if something goes wrong.

**Long-term asset fund units.**
> This is a high-risk investment, and assets may take a long time to buy and sell. Only invest if you can wait (possibly several years) to get your money back. You do not have protection against poor performance.

**Cryptoassets or UK RIE cryptoasset exchange traded notes.**
> Don't invest unless you're prepared to lose all the money you invest. This is a high-risk investment and you should not expect to be protected if something goes wrong.

**The trap to encode.** Crypto says **you should not expect to be protected**. Non-readily-realisable securities say **you are unlikely to be protected**. Same opening sentence, different closing clause. A model that matches the wrong variant will throw a false positive on a compliant crypto advert. **Confidence high.**

### 6.2 The digital link, COBS 4.12A.11R(3)

On a website, app or other digital medium the warning is followed by a link in the form of the text.
> Take 2 mins to learn more

This is appended to the warning. It is not part of the core warning text.

### 6.3 Shortened warnings, character-limit exception only, COBS 4.12A.11R(2)

**Non-readily-realisable securities, crypto or UK RIE crypto ETNs.**
> Don't invest unless you're prepared to lose all the money you invest.

**P2P agreements or P2P portfolios.**
> Don't invest unless you're prepared to lose money.

**Long-term asset fund units.**
> This is a high-risk investment, so only invest if you can wait to get your money back.

Permitted **only** where the full warning exceeds a third-party character limit. If the platform has room for the full warning, the shortened one is non-compliant. That is rule R16.

### 6.4 Personalised risk warning, first direct-offer promotion, COBS 4.12A.20R(1)(b)

> [Client name], this is a high-risk investment. How would you feel if you lost the money you're about to invest? Take 2 mins to learn more.

### 6.5 The FSCS carve-out, COBS 4.12A.11R(5)

The words **and you are unlikely to be protected if something goes wrong** may be omitted where the investment is issued or provided by a participant firm and could give rise to a protected FSCS claim. So the rule must flag the **absence** of a warning, not punish a firm for using a permitted shorter or carved-out variant. **Confidence high.** A clean Q&A flex.

---

## 7. 🔍 Phrase bank for the model

A fast scan list. Flag the red-flag phrases. Do not flag the safe phrases on their own.

### 🚩 Red-flag phrases, likely a breach

- **Guarantee and safety.** guaranteed, guaranteed returns, risk-free, zero risk, no risk, 100% safe, cannot lose, can't lose, capital protected, capital guaranteed, secure returns, locked-in profit
- **FCA and authority.** FCA approved, FCA endorsed, approved by the FCA, FCA regulated, backed by the regulator, government approved
- **Incentives.** free crypto, free shares, sign-up bonus, deposit bonus, cashback, refer a friend, free gift, bonus when you invest
- **Hype and urgency with no balance.** next 100x, to the moon, get rich, life-changing returns, get in before everyone, last chance, don't miss out
- **Unbalanced tax.** tax-free returns, completely tax-free, save tax, with no caveat
- **Truncation signals.** see more, ellipsis at the end of a warning, warning only in a caption, warning only on the last slide

### ✅ Safe phrases, compliant on their own, do not flag

- capital at risk, your capital is at risk, the value can fall as well as rise, you may get back less than you invest, you could lose all the money you invest
- returns are not guaranteed, past performance is not a reliable indicator of future results, forecasts are not a reliable indicator of future performance
- target return, projected return shown with a proper basis and warning
- Authorised and regulated by the Financial Conduct Authority, FRN shown and true
- Approved by [Firm], FRN shown
- tax treatment depends on your individual circumstances and may change

**Important.** A safe phrase does not cancel a red-flag phrase. An advert that says both "capital at risk" and "guaranteed 12%" still trips R1, because the guarantee is the misleading element.

---

## 8. 🔴 FCA Warning List logic

The only genuinely live external data source and the engine behind the red demo.

- **Source.** FCA Warning List of unauthorised firms. https://www.fca.org.uk/consumers/warning-list-unauthorised-firms
- **Scrape it to a local JSON** for the demo so venue wifi cannot kill it.
- **Match on** firm name, trading name, domain and any named individual. Normalise case and strip punctuation first. Flag near-matches too, since clone firms deliberately mimic authorised names.
- **A hit sets** `warning_list_hit` to true and forces overall RED regardless of any other rule.
- **Data fields matter.** If the scrape only captures firm names and not domains or individuals, clone-firm detection weakens. Confirm the fields before the demo.

---

## 9. 🧮 Decision logic and scoring

```
1. Identify product type and communicator status.
2. Run all rules R1 to R17.
3. For each rule record: triggered (true or false), severity, evidence phrase, provision.
4. Run the Warning List check.

Aggregation precedence:
   IF warning_list_hit OR any RED rule triggered  -> overall_verdict = RED
   ELSE IF any AMBER rule triggered               -> overall_verdict = AMBER
   ELSE                                           -> overall_verdict = GREEN

Escalation:
   R8 (truncation) severity becomes RED if the product is a high-risk investment.
```

**A human always makes the final call.** The tool triages and prioritises the queue. It does not enforce. Every verdict cites the provision and quotes the evidence phrase so a compliance officer can check the reasoning in seconds.

---

## 10. 🧾 Output schema the model returns

```json
{
  "overall_verdict": "RED",
  "summary": "Crypto promotion with a guaranteed-returns claim, a false FCA approval claim, and no prescribed risk warning.",
  "warning_list_hit": false,
  "product_type": "cryptoasset",
  "communicator_status": "unauthorised",
  "rules": [
    {
      "rule_id": "R1",
      "name": "Guaranteed or risk-free returns",
      "triggered": true,
      "severity": "RED",
      "provision": "COBS 4.2.5G; COBS 4.2.1R",
      "evidence": "300% guaranteed returns, zero risk",
      "explanation": "Describes a capital-at-risk crypto product as guaranteed and zero risk, which cannot be a fair, clear and not misleading description.",
      "suggested_fix": "Remove the guarantee and zero-risk claims. State that the investor could lose all the money they invest."
    },
    {
      "rule_id": "R3",
      "name": "No prescribed risk warning",
      "triggered": true,
      "severity": "RED",
      "provision": "COBS 4.12A.10R; COBS 4.12A.11R(1)(d)",
      "evidence": "no prescribed warning present anywhere in the advert",
      "explanation": "A cryptoasset promotion must carry the prescribed crypto risk warning. None is present.",
      "suggested_fix": "Add the prescribed crypto warning, displayed prominently for the duration of the promotion."
    }
  ]
}
```

---

## 11. 🎯 Full worked examples

End-to-end, the way the model should reason and output. These are training few-shots.

### 11.1 🔴 RED, the crypto scam showstopper

**Advert.** "CoinVault Pro. 300% guaranteed returns, zero risk. FCA approved. Refer a friend and get £50 free crypto. Sign up now."

**Reasoning.** Product type crypto. Communicator unauthorised. R1 fires on guaranteed and zero risk. R2 fires on FCA approved. R3 fires, no prescribed warning. R4 fires on free crypto and the referral reward. If CoinVault Pro is on the Warning List, R5 fires and forces RED on its own.

**Verdict.** RED. Five independent severe breaches plus a likely Warning List match. Unlawful and a scam signal. Must not run.

### 11.2 🟠 AMBER, the performance claim

**Advert.** A clean equity-fund video. "Our flagship fund returned 18% last year. Capital at risk." The 18% is the headline in large flashing text. No statement that past performance is not a reliable indicator. No period or source.

**Reasoning.** Product type mainstream investment. Communicator authorised. R1 does not fire, it says capital at risk and makes no guarantee. R11 fires, the past return is the dominant feature, carries no reliability warning, and gives no period or source.

**Verdict.** AMBER. Lawful, even mentions capital at risk, so not RED. But it breaches COBS 4.5A.10R on how past performance must be presented. Fixable by adding the warning, the period and the source, and by making the figure less prominent.

### 11.3 🟢 GREEN, the compliant promotion

**Advert.** A crypto exchange Instagram post. The prescribed crypto warning is statically fixed across the top of every slide for the duration. Benefits are stated alongside the risk. The Take 2 mins to learn more link opens the risk summary. The approving firm and its FRN are shown.

**Reasoning.** Product type crypto. Communicator authorised and approved. No rule fires. Warning present, correct crypto variant, prominent, complete, throughout. Balance present. Approver disclosure present.

**Verdict.** GREEN. Standalone compliant. This is what passing looks like. The model must not invent a breach where none exists.

---

## 12. ✂️ Scope and limitations

Encode this and say it out loud. The rubric rewards honesty about limits.

- **It is triage, not enforcement.** A human reviewer decides. The tool prioritises the queue.
- **It can produce false positives and can hallucinate.** Every verdict cites the provision and quotes the evidence phrase so a human can check.
- **Scope is investments and crypto.** Deep on COBS 4, s21 and FG24/1. The rule set swaps in per vertical.
- **Next steps.** A live Warning List API, vision on video reels and carousels, the other COBS verticals, and a feedback loop into the firm's audit trail.

### 12.1 Modular extension map

| Vertical | Sourcebook |
|---|---|
| Consumer credit and BNPL | CONC 3 |
| Mortgages and home finance | MCOB 3A |
| Insurance | ICOBS 2 |
| Banking | BCOBS 2 |
| Claims management | CMCOB 2 and CMCOB 3 |
| Funeral plans | FPCOB 4 |

---

## 13. 🎯 The Consumer Duty layer, framing not a line-item

FG24/1 sits on top of Principle 12 and PRIN 2A, with FG22/5 as the guidance. Balance and consumer understanding are Duty concepts. Use the Duty as the **why** in the pitch, the FCA expects good outcomes and not merely technically-true ads, but do not encode it as a separate checkable rule. It is the outcomes umbrella over everything else. **Confidence high.**

---

## 14. 🔗 Source provisions index

### Legislation
- s21 FSMA 2000, the financial promotion restriction. https://www.legislation.gov.uk/ukpga/2000/8/section/21
- s19 FSMA 2000, the general prohibition. https://www.legislation.gov.uk/ukpga/2000/8/section/19

### Handbook rules
- COBS 4, the whole chapter. https://handbook.fca.org.uk/handbook/cobs4
- COBS 4.2 Fair, clear and not misleading. https://handbook.fca.org.uk/handbook/cobs4/cobs4s2
- COBS 4.5A Past, simulated past and future performance. https://handbook.fca.org.uk/handbook/cobs4/cobs4s5a
- COBS 4.10 Approving and confirming compliance. https://handbook.fca.org.uk/handbook/cobs4/cobs4s10
- COBS 4.12A Promotion of restricted mass market investments including crypto. https://handbook.fca.org.uk/handbook/cobs4/cobs4s12a
- COBS 12.4 Investment research and recommendations. https://handbook.fca.org.uk/handbook/cobs12/cobs12s4

### Guidance and rules documents
- FG24/1 Financial promotions on social media. https://www.fca.org.uk/publications/finalised-guidance/fg24-1-finalised-guidance-financial-promotions-social-media
- FG23/3 Cryptoasset promotions finalised guidance. https://www.fca.org.uk/publications/fg23-3-finalised-non-handbook-guidance-cryptoasset-financial-promotions
- PS23/6 Financial promotion rules for cryptoassets. https://www.fca.org.uk/publications/policy-statements/ps23-6-financial-promotion-rules-cryptoassets
- FG22/5 Consumer Duty final non-Handbook guidance. https://www.fca.org.uk/publication/finalised-guidance/fg22-5.pdf

### Live data
- FCA Warning List of unauthorised firms. https://www.fca.org.uk/consumers/warning-list-unauthorised-firms

### Demo data
- ASA rulings, free few-shot examples of real adjudications on dodgy investment ads. https://www.asa.org.uk/codes-and-rulings/rulings.html
