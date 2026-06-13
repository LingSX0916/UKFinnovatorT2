/* ============================================================
   app.jsx — Triage orchestrator: Kanban board ⇄ case ⇄ intake.
   A background agent pulls Inbox cards, analyses each via the
   backend /scan endpoint (OpenAI, grounded in FCA.md) and moves
   it to a risk column.
   ============================================================ */
const { useState, useEffect, useRef } = React;

// build the initial board: seeded (already triaged) + raw inbox cards
function initialComplaints() {
  const seeded = window.COMPLAINTS.map(c => ({ ...c, stage: c.analysis.rag }));
  const inbox = window.INBOX.map(c => ({ ...c, analysis: null, stage: "inbox" }));
  return [...inbox, ...seeded];
}

function App() {
  // case-detail layout: "A" = Dossier, "B" = Signal (toggle in the result bar)
  const [resultStyle, setResultStyle] = useState("A");
  const t = { resultStyle, showScore: true };

  const [view, setView] = useState("queue");          // queue(board) | case | intake
  const [complaints, setComplaints] = useState(initialComplaints);
  const [activeRef, setActiveRef] = useState(null);
  const [freshRef, setFreshRef] = useState(null);
  const [analysingNow, setAnalysingNow] = useState(null);

  const complaintsRef = useRef(complaints);
  useEffect(() => { complaintsRef.current = complaints; }, [complaints]);
  const busy = useRef(false);
  const started = useRef(false);

  const patch = (ref, p) => setComplaints(prev => prev.map(c => c.ref === ref ? { ...c, ...p } : c));

  // analyse one card, then advance to the next inbox card
  const triageCard = (card) => {
    const minDwell = window.SCAN_STEPS.length * 520 + 400;
    const t0 = Date.now();
    const ctx = `Channel: ${card.channels.join(", ")}. Product type: ${card.productTypes.join(", ")}. Complainant reports the firm is ${card.authorisedClaim === "No" ? "NOT authorised" : card.authorisedClaim === "Yes" ? "authorised" : "of unknown authorisation"}. Reason given: ${card.reason}`;
    window.analyseAdvert(card.advert, card.promoter, ctx, card.image).then(analysis => {
      const wait = Math.max(0, minDwell - (Date.now() - t0));
      setTimeout(() => {
        patch(card.ref, { analysis, stage: analysis.rag });
        setAnalysingNow(null);
        busy.current = false;
        setFreshRef(r => (r === card.ref ? null : r));
        // persist complaints logged through the intake form (not the demo seeds)
        if (card.persist) window.saveComplaint({ ...card, analysis, stage: analysis.rag });
        setTimeout(processNext, 700);
      }, wait);
    });
  };

  const processNext = () => {
    if (busy.current) return;
    const next = complaintsRef.current.find(c => c.stage === "inbox");
    if (!next) return;
    busy.current = true;
    setAnalysingNow(next.promoter);
    patch(next.ref, { stage: "analysing" });
    triageCard(next);
  };

  // load previously persisted (Supabase-backed) complaints, deduped by ref
  useEffect(() => {
    let cancelled = false;
    window.fetchSavedComplaints && window.fetchSavedComplaints().then(saved => {
      if (cancelled || !saved.length) return;
      setComplaints(prev => {
        const have = new Set(prev.map(c => c.ref));
        const add = saved
          .filter(c => c && c.ref && !have.has(c.ref))
          .map(c => ({ ...c, persist: true, stage: c.analysis ? c.analysis.rag : "inbox" }));
        return [...add, ...prev];
      });
    });
    return () => { cancelled = true; };
  }, []);

  // kick off the background agent on load; drop a live complaint in mid-stream
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    window.loadRulebook && window.loadRulebook();
    const t1 = setTimeout(processNext, 900);
    const t2 = setTimeout(() => {
      const incoming = { ...window.INCOMING, analysis: null, stage: "inbox" };
      setComplaints(prev => [incoming, ...prev]);
      setFreshRef(incoming.ref);
      setTimeout(processNext, 200);
    }, 6500);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const openCase = (ref) => { setActiveRef(ref); setView("case"); };
  const goHome = () => setView("queue");
  const goNew = () => setView("intake");

  const submitComplaint = (complaint) => {
    const c = { ...complaint, analysis: null, stage: "inbox", persist: true };
    setComplaints(prev => [c, ...prev]);
    setFreshRef(c.ref);
    setView("queue");
    setTimeout(processNext, 250);
  };

  const active = complaints.find(c => c.ref === activeRef);
  const toggleStyle = () => setResultStyle(s => (s === "A" ? "B" : "A"));

  return (
    <div className="app">
      <Topbar onHome={goHome} onNew={goNew} view={view} />

      {view === "queue" &&
        <QueueView complaints={complaints} freshRef={freshRef} analysingNow={analysingNow}
          onOpen={openCase} onNew={goNew} />}
      {view === "case" && active && active.analysis &&
        <CaseView c={active} t={t} onBack={goHome} onToggleStyle={toggleStyle} />}
      {view === "intake" &&
        <IntakeView onSubmit={submitComplaint} onCancel={goHome} />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
