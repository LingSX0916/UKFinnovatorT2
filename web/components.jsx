/* ============================================================
   components.jsx — presentational pieces for Triage.
   Exposes: Icon, RagLight, Beacon, StatusPill, CategoryTag,
   BreachCard, AdvertView, CompanyCheck, ComplaintRecord,
   Topbar, RAG_META
   ============================================================ */

const RAG_META = {
  red:   { label: "Red", full: "Red · High risk",        verb: "Breaches found" },
  amber: { label: "Amber", full: "Amber · Needs amendment", verb: "Needs amendment" },
  green: { label: "Green", full: "Green · Compliant",     verb: "No breaches found" }
};

/* ---- inline icon set (stroke, currentColor) ---- */
function Icon({ name, size = 18, stroke = 1.8 }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: stroke, strokeLinecap: "round", strokeLinejoin: "round" };
  const paths = {
    check: <polyline points="20 6 9 17 4 12" />,
    x: <g><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></g>,
    alert: <g><path d="M10.3 3.3 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.3a2 2 0 0 0-3.4 0Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></g>,
    shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />,
    search: <g><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></g>,
    building: <g><rect x="4" y="3" width="16" height="18" rx="1.5" /><line x1="9" y1="7" x2="9.01" y2="7" /><line x1="15" y1="7" x2="15.01" y2="7" /><line x1="9" y1="11" x2="9.01" y2="11" /><line x1="15" y1="11" x2="15.01" y2="11" /><line x1="10" y1="21" x2="14" y2="21" /></g>,
    flag: <g><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V4s-1 1-4 1-5-2-8-2-4 1-4 1Z" /><line x1="4" y1="22" x2="4" y2="15" /></g>,
    doc: <g><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><polyline points="14 2 14 8 20 8" /></g>,
    arrow: <g><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></g>,
    back: <g><line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" /></g>,
    info: <g><circle cx="12" cy="12" r="9" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" /></g>,
    download: <g><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></g>,
    scan: <g><path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" /><path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" /><line x1="3" y1="12" x2="21" y2="12" /></g>,
    inbox: <g><polyline points="22 12 16 12 14 15 10 15 8 12 2 12" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z" /></g>,
    plus: <g><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></g>,
    bolt: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />,
    user: <g><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></g>,
    pin: <g><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0Z" /><circle cx="12" cy="10" r="3" /></g>,
    clock: <g><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15 14" /></g>,
    image: <g><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></g>
  };
  return <svg {...p}>{paths[name] || null}</svg>;
}

function RagLight({ rag }) {
  return (
    <span className={"rag-light " + rag} aria-label={RAG_META[rag].full}>
      <span className="lamp r" /><span className="lamp a" /><span className="lamp g" />
    </span>
  );
}

function Beacon({ rag }) {
  return (
    <div className={"beacon " + rag}>
      <div className="beacon-stack">
        <span className="beacon-lamp r" /><span className="beacon-lamp a" /><span className="beacon-lamp g" />
      </div>
    </div>
  );
}

function StatusPill({ rag }) {
  return <span className={"status-pill s-" + rag}><span className="pdot" />{RAG_META[rag].label}</span>;
}

function CategoryTag({ rag, children }) {
  return <span className={"cat-tag " + rag}>{children}</span>;
}

/* ---- breach card (handles omission breaches with no quote) ---- */
function BreachCard({ breach, onHover }) {
  return (
    <div className={"breach " + breach.severity}>
      <div className="breach-head">
        <span className="rule-code">{breach.rule}</span>
        <span className="breach-title">{breach.title}</span>
        <span className={"sev " + breach.severity}>{breach.severity}</span>
      </div>
      <p className="breach-body">{breach.explanation}</p>
      {breach.quote ? (
        <div className="breach-quote"
             onMouseEnter={() => onHover && onHover(breach.quote)}
             onMouseLeave={() => onHover && onHover(null)}>
          <span className="qlabel">Offending text</span>
          <em>“{breach.quote}”</em>
        </div>
      ) : (
        <div className="breach-quote empty">Breach of omission — no specific phrase; the required information is absent from the advert.</div>
      )}
    </div>
  );
}

/* ---- advert with highlighted offending spans ---- */
function buildSegments(text, quotes) {
  const ranges = [];
  quotes.forEach((q, qi) => {
    if (!q || q.length < 2) return;
    const idx = text.indexOf(q);
    if (idx !== -1) ranges.push({ start: idx, end: idx + q.length, qi });
  });
  ranges.sort((a, b) => a.start - b.start || b.end - a.end);
  const kept = []; let cursor = 0;
  for (const r of ranges) { if (r.start < cursor) continue; kept.push(r); cursor = r.end; }
  const segs = []; let pos = 0;
  for (const r of kept) {
    if (r.start > pos) segs.push({ t: text.slice(pos, r.start), hl: false });
    segs.push({ t: text.slice(r.start, r.end), hl: true, qi: r.qi });
    pos = r.end;
  }
  if (pos < text.length) segs.push({ t: text.slice(pos), hl: false });
  return segs;
}

function AdvertView({ advert, quotes, activeQuote, image }) {
  const segs = React.useMemo(() => buildSegments(advert || "", quotes), [advert, quotes]);
  return (
    <div className="advert-view">
      {image ? <img className="advert-image" src={image} alt="Reported advert" /> : null}
      {advert ? segs.map((s, i) => s.hl
        ? <mark key={i} className={"hl" + (activeQuote && quotes[s.qi] === activeQuote ? " on" : "")}>{s.t}</mark>
        : <React.Fragment key={i}>{s.t}</React.Fragment>) : null}
    </div>
  );
}

/* ---- company / scam check ---- */
function CompanyCheck({ company }) {
  const wl = company.warningList, ch = company.companiesHouse, au = company.authorised;
  const wlTone = wl.status === "match" ? "bad" : wl.status === "clear" ? "ok" : "neutral";
  const chTone = ch.status === "active" ? "ok" : ch.status === "dissolved" ? "warn" : ch.status === "not_found" ? "bad" : "neutral";
  const auTone = au.status === "authorised" ? "ok" : au.status === "not_authorised" ? "bad" : "neutral";
  const tagMap = { match: "ON WARNING LIST", clear: "NO MATCH", unknown: "UNCONFIRMED",
    active: "ACTIVE", dissolved: "DISSOLVED", not_found: "NOT FOUND",
    authorised: "AUTHORISED", not_authorised: "NOT AUTHORISED" };
  const ic = (tone) => tone === "ok" ? "check" : tone === "bad" ? "x" : tone === "warn" ? "alert" : "info";
  const Row = ({ tone, title, note, status }) => (
    <div className="check-row">
      <div className={"check-ic " + tone}><Icon name={ic(tone)} size={18} /></div>
      <div className="check-main">
        <h4>{title}</h4><p>{note}</p>
        <span className="check-tag">{tagMap[status]}</span>
      </div>
    </div>
  );
  return (
    <div>
      <Row tone={wlTone} title="FCA Warning List" note={wl.note} status={wl.status} />
      <Row tone={chTone} title="Companies House" note={ch.note} status={ch.status} />
      <Row tone={auTone} title="FCA Authorisation (FS Register)" note={au.note} status={au.status} />
    </div>
  );
}

/* ---- the complaint exactly as submitted via the report form ---- */
function ComplaintRecord({ complaint, showAdvert }) {
  const c = complaint;
  const authClass = c.authorisedClaim === "Yes" ? "yes" : c.authorisedClaim === "No" ? "no" : "unsure";
  const authIcon = c.authorisedClaim === "Yes" ? "check" : c.authorisedClaim === "No" ? "x" : "info";
  return (
    <div className="case-record">
      <div className="field">
        <div className="k">Reported by</div>
        <div className="v">{c.reporterType} · received {window.relTime(c.mins)}</div>
      </div>
      <div className="field">
        <div className="k">Who is advertising the product?</div>
        <div className="v">{c.promoter}</div>
      </div>
      <div className="field">
        <div className="k">Is the advert from an authorised firm?</div>
        <div className="v"><span className={"auth-flag " + authClass}><Icon name={authIcon} size={15} stroke={2.4} />{c.authorisedClaim}</span></div>
      </div>
      <div className="field">
        <div className="k">Where did they see the advert?</div>
        <div className="v"><div className="tag-list">{c.channels.map((ch, i) => <span key={i} className="mini-tag">{ch}</span>)}</div></div>
      </div>
      <div className="field">
        <div className="k">Type of financial product</div>
        <div className="v"><div className="tag-list">{c.productTypes.map((p, i) => <span key={i} className="mini-tag">{p}</span>)}</div></div>
      </div>
      <div className="field">
        <div className="k">When &amp; where seen</div>
        <div className="v">{c.whenSeen} — {c.whereSeen}</div>
      </div>
      <div className="field">
        <div className="k">Reason for the complaint</div>
        <div className="v reason">“{c.reason}”</div>
      </div>
      {showAdvert ? (
        <div className="field">
          <div className="k">Advert copy supplied</div>
          <div className="v" style={{ whiteSpace: "pre-wrap", marginTop: 4 }}>{c.advert}</div>
        </div>
      ) : null}
    </div>
  );
}

/* ---- top bar ---- */
function Topbar({ onHome, onNew, onDashboard, view }) {
  return (
    <header className="topbar">
      <div className="brand" style={{ cursor: "pointer" }} onClick={onHome}>
        <div className="brand-mark" />
        <div className="brand-name">Triage</div>
      </div>
      <div className="brand-sub">Financial Conduct Authority · Financial Promotions triage</div>
      <div className="topbar-spacer" />
      <div className="topbar-meta">
        {view !== "queue" ? (
          <button className="btn-link" onClick={onHome}>Board</button>
        ) : null}
        {view !== "dashboard" ? (
          <button className="btn-link" onClick={onDashboard}>Dashboard</button>
        ) : null}
        <a className="btn-link" href="/kyb" style={{ display: "inline-flex", alignItems: "center", gap: 6 }} title="Company due-diligence & sanctions screening">
          <Icon name="shield" size={15} /> KYB
        </a>
        <button className="btn-link" style={{ display: "inline-flex", alignItems: "center", gap: 6 }} onClick={onNew}>
          <Icon name="plus" size={15} stroke={2.4} /> Log complaint
        </button>
        <span>Internal use only</span>
        <div className="topbar-user"><span className="avatar">RM</span><span>R. Mensah</span></div>
      </div>
    </header>
  );
}

Object.assign(window, {
  Icon, RagLight, Beacon, StatusPill, CategoryTag, BreachCard, AdvertView,
  CompanyCheck, ComplaintRecord, Topbar, RAG_META
});
