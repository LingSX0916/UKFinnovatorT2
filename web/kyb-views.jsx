/* ============================================================
   kyb-views.jsx — KYB console screens: search, dossier (tabbed),
   screening panel (factor breakdown + evidence-cited match cards),
   match-review drawer. Reuses components.jsx (Icon, RAG pills).
   Exposes: KybTopbar, SearchView, DossierView, MatchDrawer
   ============================================================ */
const { useState: useS, useEffect: useE } = React;

function KybTopbar({ onHome }) {
  return (
    <header className="topbar">
      <div className="brand" style={{ cursor: "pointer" }} onClick={onHome}>
        <div className="brand-mark" />
        <div className="brand-name">KYB&nbsp;Intel</div>
      </div>
      <div className="brand-sub">Company due diligence · UK Sanctions List · FCA Warning List · Companies House</div>
      <div className="topbar-spacer" />
      <div className="topbar-meta">
        <a className="btn-link" href="/">← Promotions Triage</a>
        <span>Internal use only</span>
        <div className="topbar-user"><span className="avatar">CO</span><span>Compliance</span></div>
      </div>
    </header>
  );
}

/* ---------- search ---------- */
function SearchView({ onOpen }) {
  const [q, setQ] = useS("");
  const [results, setResults] = useS(null);
  const [busy, setBusy] = useS(false);
  const [err, setErr] = useS(null);
  const [mode, setMode] = useS(null);

  useE(() => { window.KYB.health().then(setMode).catch(() => {}); }, []);
  const isLive = mode && mode.companies_house === "live";

  const run = async () => {
    if (!q.trim()) return;
    setBusy(true); setErr(null);
    try { setResults(await window.KYB.search(q.trim())); }
    catch (e) { setErr(e.message); setResults([]); }
    finally { setBusy(false); }
  };

  return (
    <div className="board-stage">
      <div className="board-wrap kyb-search">
        <div className="board-head">
          <div>
            <h1>Company due-diligence search</h1>
            <div className="fca-accent" />
            <p className="sub">Search Companies House, open a dossier, then run a one-click sanctions &amp; Warning-List check across every officer and beneficial owner.</p>
          </div>
        </div>

        {mode ? (
          <div className={"mode-banner " + (isLive ? "live" : "demo")}>
            <Icon name={isLive ? "check" : "info"} size={15} />
            {isLive
              ? <span><b>Live</b> — connected to the Companies House API; search returns real UK companies.</span>
              : <span><b>Demo data</b> — Companies House search is limited to the bundled demo companies below. Set <code>COMPANIES_HOUSE_API_KEY</code> in <code>.env</code> and restart the server for live search.</span>}
          </div>
        ) : null}

        <div className="search-bar">
          <input className="text-input" placeholder="Company name or number…" value={q}
            onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === "Enter" && run()} />
          <button className="btn btn-primary" onClick={run} disabled={busy}>
            <Icon name="search" size={16} /> {busy ? "Searching…" : "Search"}
          </button>
        </div>

        <div className="demo-row">
          <span className="demo-label">Demo companies:</span>
          {window.DEMO_COMPANIES.map(d => (
            <button key={d.number} className="demo-chip" onClick={() => onOpen(d.number)}>
              <b>{d.name}</b><span>{d.hint}</span>
            </button>
          ))}
        </div>

        {err ? <div className="error-box">{err}</div> : null}

        {results ? (
          results.length === 0 && !err
            ? <div className="empty-note"><Icon name="info" size={16} /> No companies matched “{q}”.
                {!isLive ? " Demo mode only searches the bundled companies — add a Companies House API key for live search." : ""}</div>
            : (
              <table className="kyb-table">
                <thead><tr><th>Company</th><th>Number</th><th>Status</th><th></th></tr></thead>
                <tbody>
                  {results.map(r => (
                    <tr key={r.company_number} className="clickable" onClick={() => onOpen(r.company_number)}>
                      <td><b>{r.company_name}</b></td>
                      <td className="mono">{r.company_number}</td>
                      <td><span className="mini-tag">{r.company_status || "—"}</span></td>
                      <td><span className="row-go"><Icon name="arrow" size={15} /></span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
        ) : null}
      </div>
    </div>
  );
}

/* ---------- dossier ---------- */
function RiskBadge({ rating, band }) {
  const rag = window.ragOf(rating);
  return (
    <div className={"risk-badge " + rag}>
      <RagLight rag={rag} />
      <div>
        <div className="rb-rating">{rating || "Not screened"}</div>
        <div className="rb-band">{band || "Run a sanction check to rate this company"}</div>
      </div>
    </div>
  );
}

function ScreeningProgress({ step }) {
  return (
    <div className="screen-progress">
      <span className="spinner" />
      <span>{window.SCREEN_STEPS[Math.min(step, window.SCREEN_STEPS.length - 1)]}…</span>
    </div>
  );
}

function FactorRow({ f }) {
  const rag = ({ RED: "red", AMBER: "amber", GREEN: "green" })[f.severity] || "amber";
  return (
    <div className={"factor " + rag}>
      <div className="factor-head">
        <span className={"sev " + (rag === "red" ? "high" : rag === "amber" ? "medium" : "low")}>{f.severity}</span>
        <span className="factor-label">{f.label}</span>
        <span className="factor-code mono">{f.code}</span>
      </div>
      <p className="factor-ev">{f.evidence}</p>
      <div className="factor-prov"><Icon name="doc" size={12} /> {f.provision} · confidence {f.confidence}</div>
    </div>
  );
}

function MatchCard({ m, onReview }) {
  const rag = window.ragOf(m.verdict);
  const ev = m.evidence || {};
  const mf = m.matched_fields || {};
  return (
    <div className={"match-card " + rag}>
      <div className="mc-head">
        <span className={"status-pill s-" + rag}><span className="pdot" />{m.verdict}</span>
        <span className="mc-list">{m.list === "UK_SANCTIONS" ? "UK Sanctions List" : "FCA Warning List"}</span>
        <span className="mc-score mono">score {Number(m.score).toFixed(2)}</span>
        <button className="btn-link mc-review" onClick={() => onReview(m)}>Review →</button>
      </div>
      <div className="mc-body">
        <div className="mc-subject"><b>{m.subject_name}</b> <span className="mc-type">{m.subject_type}</span></div>
        <div className="mc-arrow">matches</div>
        <div className="mc-desig">
          <b>{m.matched_name}</b>
          <span className="mono mc-uid">{m.matched_designation_id}</span>
        </div>
      </div>
      <div className="mc-fields">
        {mf.name_score != null ? <span className="mc-chip">name {Number(mf.name_score).toFixed(2)}</span> : null}
        {mf.dob ? <span className={"mc-chip " + (mf.dob === "match" ? "ok" : "bad")}>DOB {mf.dob}</span> : null}
        {mf.nationality ? <span className="mc-chip ok">nationality {mf.nationality}</span> : null}
        {mf.identifier ? <span className="mc-chip ok">ID {mf.identifier}</span> : null}
        {mf.common_name ? <span className="mc-chip warn">common name</span> : null}
      </div>
      {ev.regime_name ? (
        <div className="mc-evidence">
          <div className="mc-ev-row"><span className="mc-ev-k">Regime</span><span>{ev.regime_name}</span></div>
          {ev.sanctions_imposed && ev.sanctions_imposed.length ?
            <div className="mc-ev-row"><span className="mc-ev-k">Measures</span><span>{ev.sanctions_imposed.join(", ")}</span></div> : null}
          {ev.uk_statement_of_reasons ?
            <div className="mc-ev-row"><span className="mc-ev-k">UK Statement of Reasons</span><span className="mc-sor">{ev.uk_statement_of_reasons}</span></div> : null}
        </div>
      ) : ev.note ? <div className="mc-evidence"><div className="mc-ev-row"><span>{ev.note}</span></div></div> : null}
    </div>
  );
}

function SubjectChip({ s, onClick }) {
  const rag = window.ragOf(s.verdict);
  return (
    <button className={"subject-chip " + rag} onClick={onClick} title={s.subject_name}>
      <span className={"pdot " + rag} />
      <span className="sc-name">{s.subject_name}</span>
      <span className="sc-type">{s.subject_type}</span>
      {s.match_count ? <span className="sc-count">{s.match_count}</span> : <Icon name="check" size={13} stroke={2.4} />}
    </button>
  );
}

function DossierView({ number, dossier, screening, screenState, onScreen, onReview, decisions, onBack }) {
  const [tab, setTab] = useS("overview");
  const [node, setNode] = useS(null);
  const prof = dossier.profile || {};
  const ro = prof.registered_office || {};
  const risk = screening && screening.risk_assessment;
  const rating = risk && risk.overall_rating;

  const tabs = [
    ["overview", "Overview", "building"],
    ["filing", "Filing history", "doc"],
    ["officers", "Officers", "user"],
    ["ownership", "Ownership (UBO)", "shield"],
    ["risk", "Risk & screening", "alert"]
  ];

  return (
    <div className="result-stage">
      <button className="back-btn" onClick={onBack}><Icon name="back" size={16} /> Search</button>
      <div className="dossier-head">
        <div className="dh-id">
          <h1>{prof.name || number}</h1>
          <div className="dh-meta">
            <span className="mono">{number}</span>
            <span className="mini-tag">{prof.status || "—"}</span>
            <span className="mini-tag">{prof.company_type || "—"}</span>
            {prof.jurisdiction ? <span className="mini-tag">{prof.jurisdiction}</span> : null}
          </div>
        </div>
        <div className="dh-actions">
          <RiskBadge rating={rating} band={risk && risk.fca_fatf_band} />
          <button className="btn btn-primary big" onClick={onScreen} disabled={screenState.running}>
            <Icon name="shield" size={18} /> {screenState.running ? "Screening…" : "Run sanction check"}
          </button>
          <a className="btn btn-ghost" href={window.KYB.exportUrl(number, "pdf")} target="_blank" rel="noreferrer">
            <Icon name="download" size={16} /> Export PDF
          </a>
        </div>
      </div>

      {screenState.running ? <ScreeningProgress step={screenState.step} /> : null}
      {screenState.error ? <div className="error-box">Screening failed: {screenState.error}</div> : null}

      <div className="tab-bar">
        {tabs.map(([id, label, icon]) => (
          <button key={id} className={"tab " + (tab === id ? "on" : "")} onClick={() => setTab(id)}>
            <Icon name={icon} size={15} /> {label}
            {id === "risk" && screening ? <span className={"tab-dot " + window.ragOf(rating)} /> : null}
          </button>
        ))}
      </div>

      <div className="tab-body">
        {tab === "overview" && <OverviewTab prof={prof} ro={ro} />}
        {tab === "filing" && <FilingTab filings={dossier.filing_history || []} flags={screening && screening.filing_flags} />}
        {tab === "officers" && <OfficersTab officers={dossier.officers || []} statuses={screening && screening.subjects_status} />}
        {tab === "ownership" && (
          <div className="ubo-tab">
            <OwnershipGraph graph={(screening && screening.ownership_graph) || dossier.ownership_graph}
              onSelect={setNode} selectedId={node && node.id} />
            {node ? <NodeDetail node={node} /> : <div className="hint-note">Click a node to inspect its screening result.</div>}
          </div>
        )}
        {tab === "risk" && (
          screening
            ? <ScreeningPanel screening={screening} onReview={onReview} decisions={decisions} onPick={(ref) => { setTab("ownership"); }} />
            : <div className="empty-note"><Icon name="shield" size={18} /> Run the sanction check to produce an FCA / FATF risk rating with evidence.</div>
        )}
      </div>
    </div>
  );
}

function OverviewTab({ prof, ro }) {
  const acc = prof.accounts || {}, cs = prof.confirmation_statement || {};
  const Field = ({ k, v }) => <div className="field"><div className="k">{k}</div><div className="v">{v || "—"}</div></div>;
  return (
    <div className="card card-pad ov-grid">
      <Field k="Incorporated" v={prof.date_of_creation} />
      <Field k="Type" v={prof.company_type} />
      <Field k="Jurisdiction" v={prof.jurisdiction} />
      <Field k="SIC codes" v={(prof.sic_codes || []).join(", ")} />
      <Field k="Registered office" v={[ro.address_line_1, ro.locality, ro.postal_code, ro.country].filter(Boolean).join(", ")} />
      <div className="field">
        <div className="k">Accounts</div>
        <div className="v">{acc.next_due ? ("next due " + acc.next_due) : "—"} {prof.accounts_overdue ? <span className="chip-bad">OVERDUE</span> : null}</div>
      </div>
      <div className="field">
        <div className="k">Confirmation statement</div>
        <div className="v">{cs.next_due ? ("next due " + cs.next_due) : "—"} {prof.confirmation_overdue ? <span className="chip-bad">OVERDUE</span> : null}</div>
      </div>
    </div>
  );
}

function FilingTab({ filings, flags }) {
  return (
    <div>
      {flags && flags.length ? (
        <div className="flag-row">
          {flags.map((f, i) => <span key={i} className="chip-bad" title={f.evidence}>{f.label}</span>)}
        </div>
      ) : null}
      <table className="kyb-table">
        <thead><tr><th>Date</th><th>Category</th><th>Description</th></tr></thead>
        <tbody>
          {filings.length === 0 ? <tr><td colSpan="3" className="muted">No filings.</td></tr> :
            filings.map((f, i) => (
              <tr key={i}><td className="mono">{f.date}</td><td><span className="mini-tag">{f.category}</span></td><td>{f.description}</td></tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function OfficersTab({ officers, statuses }) {
  const stByName = {};
  (statuses || []).forEach(s => { stByName[(s.subject_name || "").toLowerCase()] = s; });
  return (
    <table className="kyb-table">
      <thead><tr><th>Name</th><th>Role</th><th>Appointed</th><th>Nationality</th><th>DOB</th><th>Screening</th></tr></thead>
      <tbody>
        {officers.length === 0 ? <tr><td colSpan="6" className="muted">No officers.</td></tr> :
          officers.map((o, i) => {
            const st = stByName[(o.name || "").toLowerCase()];
            const rag = st ? window.ragOf(st.verdict) : null;
            return (
              <tr key={i}>
                <td><b>{o.name}</b></td><td>{o.officer_role}</td><td className="mono">{o.appointed_on}</td>
                <td>{o.nationality || "—"}</td><td className="mono">{o.dob_month ? (o.dob_month + "/") : ""}{o.dob_year || "—"}</td>
                <td>{rag ? <span className={"status-pill s-" + rag}><span className="pdot" />{st.verdict}</span> : <span className="muted">—</span>}</td>
              </tr>
            );
          })}
      </tbody>
    </table>
  );
}

function NodeDetail({ node }) {
  const scr = node.screening || {};
  return (
    <div className="node-detail">
      <div className="nd-head"><b>{node.name}</b> <span className="mini-tag">{node.kind}</span></div>
      <div className="nd-rows">
        {node.effective_pct != null ? <div><span className="k">Effective control</span><span>{node.effective_pct}%</span></div> : null}
        {node.ownership_band ? <div><span className="k">Declared band</span><span>{node.ownership_band}</span></div> : null}
        {scr.verdict ? <div><span className="k">Screening</span><span className={"status-pill s-" + window.ragOf(scr.verdict)}><span className="pdot" />{scr.verdict}</span></div> : null}
        {scr.designation_id ? <div><span className="k">Designation</span><span className="mono">{scr.designation_id}</span></div> : null}
      </div>
    </div>
  );
}

function ScreeningPanel({ screening, onReview, decisions }) {
  const risk = screening.risk_assessment || {};
  const rag = window.ragOf(risk.overall_rating);
  const triggered = (risk.factors || []).filter(f => f.triggered);
  return (
    <div className="screen-panel">
      <div className={"verdict-banner " + rag}>
        <div className="vb-light"><RagLight rag={rag} /></div>
        <div className="vb-main">
          <div className="vb-status">{window.RAG_LABEL[risk.overall_rating]} · {risk.subjects_screened} subjects screened</div>
          <h2 className="vb-headline">{risk.summary}</h2>
          <div className="vb-action"><b>Required action:</b> {risk.required_action}</div>
        </div>
        <div className="vb-score"><div className="n">{risk.score}</div><div className="l">Risk score</div></div>
      </div>

      <div className="panel-grid">
        <div className="stack">
          <div className="section-h"><Icon name="alert" size={16} /><h3>Risk factors</h3><span className="count">{triggered.length}</span></div>
          {triggered.length === 0
            ? <div className="empty-note"><Icon name="check" size={16} stroke={2.4} /> No risk factors triggered.</div>
            : triggered.map((f, i) => <FactorRow key={i} f={f} />)}
          <div className="citations"><b>Citations:</b> {(risk.citations || []).join(" · ")}</div>
        </div>

        <div className="stack">
          <div className="section-h"><Icon name="user" size={16} /><h3>Subjects</h3><span className="count">{(screening.subjects_status || []).length}</span></div>
          <div className="subject-list">
            {(screening.subjects_status || []).map((s, i) => <SubjectChip key={i} s={s} />)}
          </div>

          <div className="section-h" style={{ marginTop: 14 }}><Icon name="flag" size={16} /><h3>Matches</h3><span className="count">{(screening.matches || []).length}</span></div>
          {(screening.matches || []).length === 0
            ? <div className="empty-note"><Icon name="check" size={16} stroke={2.4} /> No sanctions or Warning List alerts.</div>
            : (screening.matches || []).map((m) => {
              const dec = decisions[m.id];
              return (
                <div key={m.id} className={"match-wrap" + (dec ? " decided " + dec : "")}>
                  <MatchCard m={m} onReview={onReview} />
                  {dec ? <div className="decided-tag">{dec === "confirmed" ? "✓ Confirmed" : "✕ Dismissed"}</div> : null}
                </div>
              );
            })}
        </div>
      </div>

      <div className="disclaimer">
        <Icon name="info" size={15} />
        <span>This tool triages and prioritises officer review. Statuses are automated and must be confirmed against the live UK Sanctions List, FCA Warning List and Companies House before any regulatory action. Guidance, not legal advice — a human compliance officer decides.</span>
      </div>
    </div>
  );
}

/* ---------- review drawer ---------- */
function MatchDrawer({ match, onClose, onDecide }) {
  const [note, setNote] = useS("");
  if (!match) return null;
  const ev = match.evidence || {}, mf = match.matched_fields || {};
  const rag = window.ragOf(match.verdict);
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={e => e.stopPropagation()}>
        <div className="drawer-head">
          <span className={"status-pill s-" + rag}><span className="pdot" />{match.verdict}</span>
          <h3>Review match</h3>
          <button className="btn-link" onClick={onClose}><Icon name="x" size={16} /></button>
        </div>
        <div className="drawer-body">
          <div className="cmp">
            <div className="cmp-col">
              <div className="cmp-h">Subject</div>
              <div className="cmp-name">{match.subject_name}</div>
              <div className="cmp-type">{match.subject_type}</div>
            </div>
            <div className="cmp-vs">vs</div>
            <div className="cmp-col">
              <div className="cmp-h">{match.list === "UK_SANCTIONS" ? "Designation" : "Warning List entry"}</div>
              <div className="cmp-name">{match.matched_name}</div>
              <div className="cmp-type mono">{match.matched_designation_id}</div>
            </div>
          </div>
          <div className="drawer-fields">
            {Object.entries(mf).map(([k, v]) => v != null && v !== false ? (
              <div key={k} className="df-row"><span className="df-k">{k.replace(/_/g, " ")}</span><span className="df-v">{String(v)}</span></div>
            ) : null)}
          </div>
          {ev.regime_name ? <div className="drawer-ev">
            <div className="de-k">Regime</div><div>{ev.regime_name}</div>
            {ev.sanctions_imposed ? <><div className="de-k">Measures</div><div>{ev.sanctions_imposed.join(", ")}</div></> : null}
            {ev.uk_statement_of_reasons ? <><div className="de-k">UK Statement of Reasons</div><div className="mc-sor">{ev.uk_statement_of_reasons}</div></> : null}
            {ev.aliases && ev.aliases.length ? <><div className="de-k">Aliases</div><div>{ev.aliases.join("; ")}</div></> : null}
          </div> : null}
          <textarea className="advert-input" placeholder="Reviewer note (recorded in the audit log)…"
            value={note} onChange={e => setNote(e.target.value)} style={{ minHeight: 70 }} />
        </div>
        <div className="drawer-foot">
          <button className="btn btn-primary" onClick={() => onDecide(match, "confirmed", note)}><Icon name="check" size={16} /> Confirm match</button>
          <button className="btn btn-ghost" onClick={() => onDecide(match, "dismissed", note)}><Icon name="x" size={16} /> Dismiss</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { KybTopbar, SearchView, DossierView, MatchDrawer });
