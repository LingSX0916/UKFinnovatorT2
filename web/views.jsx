/* ============================================================
   views.jsx — QueueView, CaseView (2 layouts), IntakeView,
   AgentTriaging, StatBar, QueueRow, Disclaimer.
   Exposes: QueueView, CaseView, IntakeView
   ============================================================ */
const { useState: useStateV, useEffect: useEffectV, useRef: useRefV, useMemo: useMemoV } = React;

/* ---- small step-ticker shown on the card being analysed ---- */
function AnalysingTicker() {
  const steps = window.SCAN_STEPS;
  const [i, setI] = useStateV(0);
  useEffectV(() => {
    const id = setInterval(() => setI(p => Math.min(p + 1, steps.length - 1)), 520);
    return () => clearInterval(id);
  }, []);
  return <span className="step-now">{steps[i]}</span>;
}

/* ---- a single complaint card on the board ---- */
function KCard({ c, fresh, onOpen }) {
  const a = c.analysis;
  const clickable = !!a;
  const chan = c.channels[0];
  const chanShort = chan.includes("(") ? chan.replace(/^.*\(([^)]+)\).*$/, "$1") : chan;
  return (
    <div className={"kcard " + (a ? a.rag : c.stage === "analysing" ? "analysing" : "") + (fresh ? " fresh" : "") + (clickable ? " clickable" : "")}
         onClick={() => clickable && onOpen(c.ref)}>
      <div className="kc-top">
        <span className="kref">{c.ref}</span>
        {fresh ? <span className="fresh-flag2"><Icon name="bolt" size={9} stroke={2.6} />New</span> : <span>{window.relTime(c.mins)}</span>}
      </div>
      <div className="kc-promoter">{c.promoter}</div>
      <div className="kc-meta">
        <span className="kp"><Icon name="pin" size={11} />{chanShort}</span>
        <span className="kp"><Icon name="doc" size={11} />{c.productTypes[0]}</span>
        {c.image ? <span className="kp"><Icon name="image" size={11} />Image</span> : null}
      </div>

      {c.stage === "inbox" ? (
        <div className="kc-queued"><Icon name="clock" size={13} /> Queued for triage</div>
      ) : c.stage === "analysing" ? (
        <div className="kc-analysing"><span className="spinner" /><span>Agent reading…<AnalysingTicker /></span></div>
      ) : (
        <div className="kc-foot">
          <span className={"kc-cat " + a.rag}>{a.category}</span>
          <span className="flags"><Icon name="alert" size={12} />{a.breaches.length}</span>
        </div>
      )}
    </div>
  );
}

/* ---- a board column ---- */
function KColumn({ id, title, tone, cards, fresh, onOpen, emptyText }) {
  return (
    <div className={"kcol " + tone}>
      <div className="kcol-head">
        <span className="cdot" /><h3>{title}</h3>
        <span className="kcount">{cards.length}</span>
      </div>
      {cards.length === 0
        ? <div className="kcol-empty">{emptyText}</div>
        : cards.map(c => <KCard key={c.ref} c={c} fresh={c.ref === fresh} onOpen={onOpen} />)}
    </div>
  );
}

/* ---- the Kanban board ---- */
function QueueView({ complaints, freshRef, analysingNow, onOpen, onNew }) {
  const byStage = (s) => complaints.filter(c => c.stage === s);
  const rb = window.RULEBOOK || { rules: 8, file: "fca-rules.md" };
  const analysedToday = complaints.filter(c => c.analysis).length;
  const pending = byStage("inbox").length;
  const cols = [
    { id: "inbox", title: "Inbox", tone: "inbox", empty: "No new complaints" },
    { id: "analysing", title: "Analysing", tone: "analysing", empty: "Agent idle" },
    { id: "red", title: "Red · Escalate", tone: "red", empty: "None" },
    { id: "amber", title: "Amber · Amend", tone: "amber", empty: "None" },
    { id: "green", title: "Green · Compliant", tone: "green", empty: "None" }
  ];
  return (
    <div className="board-stage">
      <div className="board-wrap">
        <div className="board-head">
          <div>
            <h1>Triage board</h1>
            <div className="fca-accent" />
            <p className="sub">Complaints from the “Report a financial promotion” form flow left to right as the agent reads, analyses and triages each one against the FCA rulebook.</p>
          </div>
          <div className="spacer" />
          <button className="btn btn-primary" onClick={onNew} style={{ padding: "11px 18px" }}>
            <Icon name="plus" size={16} stroke={2.4} /> Log complaint
          </button>
        </div>

        <div className="agent-strip">
          <span className="as-title"><span className="dot2" />Triage agent</span>
          <span className="as-now">
            {analysingNow
              ? <React.Fragment><span className="spinner" />Analysing {analysingNow}…</React.Fragment>
              : pending > 0
                ? <React.Fragment><span className="spinner" />{pending} complaint{pending > 1 ? "s" : ""} awaiting triage</React.Fragment>
                : <React.Fragment><Icon name="check" size={14} stroke={2.4} />Monitoring intake — queue clear</React.Fragment>}
          </span>
          <span className="spacer" />
          <span className="as-stat"><b>{analysedToday}</b> triaged today</span>
          <span className="rulechip"><Icon name="doc" size={13} />{rb.file} · {rb.rules} rules</span>
        </div>

        <div className="kanban">
          {cols.map(col => (
            <KColumn key={col.id} id={col.id} title={col.title} tone={col.tone}
              cards={byStage(col.id)} fresh={freshRef} onOpen={onOpen} emptyText={col.empty} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---- shared disclaimer ---- */
function Disclaimer({ error }) {
  return (
    <div>
      {error ? (
        <div className="error-box">
          The triage agent could not reach the model, so this assessment was produced by the built-in rule heuristics. Re-open the case to retry.
        </div>
      ) : null}
      <div className="disclaimer">
        <Icon name="info" size={15} />
        <span>Automated triage to prioritise officer review. Warning List, Companies House and FS Register statuses are agent-assessed and must be confirmed against the live registers before any regulatory action.</span>
      </div>
    </div>
  );
}

function RecommendedAction({ data, dark }) {
  return (
    <div className="recommend" style={dark ? { background: "rgba(0,0,0,.28)", boxShadow: "inset 0 0 0 1px rgba(255,255,255,.1)" } : null}>
      <div className="rl">Recommended action</div>
      <div className="rv">{data.action}</div>
      <div className="rd">{data.verdict}</div>
    </div>
  );
}

/* ============================================================
   CASE DETAIL — Layout A (Dossier)
   ============================================================ */
function CaseDossier({ c, t }) {
  const data = c.analysis;
  const [active, setActive] = useStateV(null);
  const m = window.RAG_META[data.rag];
  const quotes = data.breaches.map(b => b.quote);
  return (
    <div className="layA fade-up">
      <div className={"verdict-banner " + data.rag}>
        <div className="vb-light"><RagLight rag={data.rag} /></div>
        <div className="vb-main">
          <div className="vb-status">{m.full} · {data.category}</div>
          <h2 className="vb-headline">{data.verdict}</h2>
        </div>
        {t.showScore ? <div className="vb-score"><div className="n">{data.score}</div><div className="l">Risk score</div></div> : null}
      </div>

      <div className="layA-grid">
        <div className="stack">
          <div className="card">
            <div className="card-head">
              <Icon name="doc" size={17} /><h3>Reported advert</h3>
              <span className="count">{data.breaches.length} flag{data.breaches.length === 1 ? "" : "s"}</span>
            </div>
            <div className="card-pad"><AdvertView advert={data.advert} quotes={quotes} activeQuote={active} image={c.image} /></div>
          </div>
          <div className="card">
            <div className="card-head"><Icon name="inbox" size={17} /><h3>Complaint record</h3>
              <span className="count mono" style={{ background: "transparent" }}>{c.ref}</span></div>
            <div className="card-pad" style={{ paddingTop: 4, paddingBottom: 10 }}><ComplaintRecord complaint={c} /></div>
          </div>
        </div>

        <div className="stack">
          <RecommendedAction data={data} />
          <div className="section-h" style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
            <Icon name="alert" size={17} /><h2 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>Rule breaches</h2>
          </div>
          {data.breaches.length === 0
            ? <div className="empty-note"><Icon name="check" size={18} stroke={2.4} /> No rule breaches detected.</div>
            : data.breaches.map((b, i) => <BreachCard key={i} breach={b} onHover={setActive} />)}

          <div className="card" style={{ marginTop: 6 }}>
            <div className="card-head"><Icon name="shield" size={17} /><h3>Firm &amp; scam checks</h3></div>
            <div className="card-pad" style={{ paddingTop: 6, paddingBottom: 6 }}>
              <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ink-600)", padding: "8px 0 2px" }}>{data.company.name}</div>
              <CompanyCheck company={data.company} />
            </div>
          </div>

          <div className="action-row" style={{ marginTop: 4 }}>
            <button className="btn btn-primary"><Icon name="flag" size={16} /> Escalate</button>
            <button className="btn btn-ghost"><Icon name="download" size={16} /> Export case file</button>
          </div>
        </div>
      </div>
      <Disclaimer error={data.error} />
    </div>
  );
}

/* ============================================================
   CASE DETAIL — Layout B (Signal panel)
   ============================================================ */
function CaseSignal({ c, t }) {
  const data = c.analysis;
  const [active, setActive] = useStateV(null);
  const m = window.RAG_META[data.rag];
  const quotes = data.breaches.map(b => b.quote);
  const high = data.breaches.filter(b => b.severity === "high").length;
  return (
    <div className="layB fade-up">
      <aside className="layB-rail">
        <Beacon rag={data.rag} />
        <div className="beacon-verdict">
          <div className="st">{m.verb}</div>
          <div className="sub">{data.category}</div>
        </div>
        <div>
          {t.showScore ? <div className="rail-stat"><span className="k">Risk score</span><span className="v">{data.score} / 100</span></div> : null}
          <div className="rail-stat"><span className="k">Total breaches</span><span className="v">{data.breaches.length}</span></div>
          <div className="rail-stat"><span className="k">High severity</span><span className="v">{high}</span></div>
          <div className="rail-stat"><span className="k">Warning List</span><span className="v">{data.company.warningList.status === "match" ? "Match" : data.company.warningList.status === "clear" ? "Clear" : "—"}</span></div>
          <div className="rail-stat"><span className="k">Authorised</span><span className="v">{data.company.authorised.status === "authorised" ? "Yes" : data.company.authorised.status === "not_authorised" ? "No" : "—"}</span></div>
        </div>
        <RecommendedAction data={data} dark />
        <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
          <button className="btn btn-primary" style={{ background: "var(--coral)", boxShadow: "0 2px 0 var(--coral-700)", justifyContent: "center" }}>
            <Icon name="flag" size={16} /> Escalate this case
          </button>
          <button className="btn btn-ghost" style={{ borderColor: "rgba(255,255,255,.25)", color: "#fff", justifyContent: "center" }}>
            <Icon name="download" size={16} /> Export case file
          </button>
        </div>
      </aside>

      <main className="layB-main">
        <div className="section">
          <div className="section-h"><h2>Reported advert</h2><span className="num">{data.breaches.length} flags</span></div>
          <div className="card card-pad"><AdvertView advert={data.advert} quotes={quotes} activeQuote={active} image={c.image} /></div>
        </div>
        <div className="section">
          <div className="section-h"><h2>Rule breaches</h2><span className="num">{data.breaches.length}</span></div>
          {data.breaches.length === 0
            ? <div className="empty-note"><Icon name="check" size={18} stroke={2.4} /> No rule breaches detected — promotion appears compliant.</div>
            : <div className="stack">{data.breaches.map((b, i) => <BreachCard key={i} breach={b} onHover={setActive} />)}</div>}
        </div>
        <div className="section">
          <div className="section-h"><h2>Firm &amp; scam checks</h2><span className="num">{data.company.name}</span></div>
          <div className="card card-pad" style={{ paddingTop: 6, paddingBottom: 6 }}><CompanyCheck company={data.company} /></div>
        </div>
        <div className="section">
          <div className="section-h"><h2>Complaint record</h2><span className="num mono">{c.ref}</span></div>
          <div className="card card-pad" style={{ paddingTop: 4, paddingBottom: 10 }}><ComplaintRecord complaint={c} /></div>
        </div>
        <Disclaimer error={data.error} />
      </main>
    </div>
  );
}

/* ---- case wrapper + result bar ---- */
function CaseView({ c, t, onBack, onToggleStyle }) {
  const data = c.analysis;
  return (
    <div className="result-stage">
      <div className="result-bar">
        <button className="back-btn" onClick={onBack}><Icon name="back" size={16} /> Queue</button>
        <span style={{ width: 1, height: 22, background: "var(--border-2)" }} />
        <StatusPill rag={data.rag} />
        <span className="crumb"><b className="mono">{c.ref}</b> · {c.promoter}</span>
        <button className="btn-link mono" style={{ marginLeft: "auto", fontSize: 12 }}
          onClick={onToggleStyle} title="Switch case layout">
          {t.resultStyle === "A" ? "Dossier view" : "Signal view"} ⇄
        </button>
      </div>
      {t.resultStyle === "A" ? <CaseDossier c={c} t={t} /> : <CaseSignal c={c} t={t} />}
    </div>
  );
}

/* ============================================================
   INTAKE — log a new incoming complaint (agent will triage it)
   ============================================================ */
const CHANNEL_OPTS = ["Social media (Instagram)", "Social media (Facebook)", "Social media (TikTok)", "Website", "Search engine advert", "Mobile app", "Newspaper", "Email / post", "TV or radio"];
const PRODUCT_OPTS = ["Investments", "Crypto", "Pensions", "Consumer credit", "Buy Now Pay Later", "Mortgages", "Insurance", "Financial advice", "Claims management"];

// read an image file, downscaling its longest edge to maxDim, as a JPEG data URL
function readImageDownscaled(file, maxDim, cb) {
  const reader = new FileReader();
  reader.onload = e => {
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      if (Math.max(width, height) > maxDim) {
        const s = maxDim / Math.max(width, height);
        width = Math.round(width * s); height = Math.round(height * s);
      }
      const canvas = document.createElement("canvas");
      canvas.width = width; canvas.height = height;
      canvas.getContext("2d").drawImage(img, 0, 0, width, height);
      try { cb(canvas.toDataURL("image/jpeg", 0.85)); }
      catch (err) { cb(e.target.result); } // fallback to original (e.g. cross-origin)
    };
    img.onerror = () => cb(e.target.result);
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function IntakeView({ onSubmit, onCancel }) {
  const [promoter, setPromoter] = useStateV("");
  const [advert, setAdvert] = useStateV("");
  const [reason, setReason] = useStateV("");
  const [channel, setChannel] = useStateV(CHANNEL_OPTS[0]);
  const [product, setProduct] = useStateV(PRODUCT_OPTS[0]);
  const [auth, setAuth] = useStateV("Unsure");
  const [where, setWhere] = useStateV("");
  const [image, setImage] = useStateV(null);
  const [imageName, setImageName] = useStateV("");
  const ready = advert.trim().length > 12 || !!image;
  const onPickImage = (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setImageName(f.name);
    readImageDownscaled(f, 1600, setImage);
  };
  const submit = () => {
    if (!ready) return;
    onSubmit({
      ref: "FP-2026-0" + (4922 + Math.floor(Math.random() * 70)),
      mins: 0, reporterType: "Member of the public",
      channels: [channel], promoter: promoter.trim() || "Unidentified promoter",
      authorisedClaim: auth, productTypes: [product],
      whenSeen: "13 Jun 2026, just now", whereSeen: where.trim() || channel,
      reason: reason.trim() || "No further detail provided.",
      advert: advert.trim(), image: image || null
    });
  };
  return (
    <div className="intake-stage">
      <div className="intake-col">
        <button className="back-btn" onClick={onCancel}><Icon name="back" size={16} /> Back to queue</button>
        <h1>Log an incoming complaint</h1>
        <p className="lead">Enter the details a complainant submitted through the “Report a financial promotion” form. The triage agent will read it and categorise it automatically.</p>

        <div className="intake-grid">
          <div className="full">
            <div className="field-label"><span>Advert copy reported</span><span className="hint">text and / or image</span></div>
            <textarea className="advert-input" style={{ minHeight: 150 }} value={advert}
              onChange={e => setAdvert(e.target.value)}
              placeholder="Paste the text of the financial promotion the complainant reported…" />
          </div>
          <div className="full">
            <div className="field-label"><span>Advert screenshot / image</span><span className="hint">optional — read by the AI</span></div>
            {image ? (
              <div className="image-preview">
                <img src={image} alt="advert preview" />
                <div className="image-meta">
                  <span className="image-name">{imageName || "uploaded image"}</span>
                  <button className="btn-link" onClick={() => { setImage(null); setImageName(""); }}>Remove</button>
                </div>
              </div>
            ) : (
              <label className="image-drop">
                <Icon name="image" size={22} />
                <span>Click to upload a screenshot of the advert (PNG / JPG)</span>
                <input type="file" accept="image/*" style={{ display: "none" }} onChange={onPickImage} />
              </label>
            )}
          </div>
          <div>
            <div className="field-label"><span>Who is advertising?</span><span className="hint">optional</span></div>
            <input className="text-input" value={promoter} onChange={e => setPromoter(e.target.value)} placeholder="e.g. Quantum Yield Capital Ltd" />
          </div>
          <div>
            <div className="field-label"><span>Where was it seen?</span><span className="hint">channel</span></div>
            <select className="text-input" value={channel} onChange={e => setChannel(e.target.value)}>
              {CHANNEL_OPTS.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
          <div>
            <div className="field-label"><span>Product type</span></div>
            <select className="text-input" value={product} onChange={e => setProduct(e.target.value)}>
              {PRODUCT_OPTS.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
          <div>
            <div className="field-label"><span>Claims to be FCA authorised?</span></div>
            <select className="text-input" value={auth} onChange={e => setAuth(e.target.value)}>
              <option>Unsure</option><option>Yes</option><option>No</option>
            </select>
          </div>
          <div className="full">
            <div className="field-label"><span>Where exactly seen</span><span className="hint">optional</span></div>
            <input className="text-input" value={where} onChange={e => setWhere(e.target.value)} placeholder="e.g. Sponsored Instagram reel, @handle" />
          </div>
          <div className="full">
            <div className="field-label"><span>Reason for the complaint</span><span className="hint">optional</span></div>
            <input className="text-input" value={reason} onChange={e => setReason(e.target.value)} placeholder="What the complainant told us…" />
          </div>
        </div>

        <div className="action-row">
          <button className="btn btn-primary" disabled={!ready} onClick={submit}>
            <Icon name="scan" size={18} /> Submit to agent
          </button>
          <span className="action-note">{ready ? "The agent will triage this against the FCA rulebook & the Warning List." : "Paste the advert text or upload an image to continue."}</span>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { QueueView, CaseView, IntakeView });
