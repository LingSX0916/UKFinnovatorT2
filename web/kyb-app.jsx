/* ============================================================
   kyb-app.jsx — KYB console orchestrator: search ⇄ dossier,
   Run sanction check, match review. Talks to the Flask /api.
   ============================================================ */
const { useState: useState_, useEffect: useEffect_ } = React;

function KybApp() {
  const [view, setView] = useState_("search");      // search | dossier
  const [number, setNumber] = useState_(null);
  const [dossier, setDossier] = useState_(null);
  const [screening, setScreening] = useState_(null);
  const [screenState, setScreenState] = useState_({ running: false, step: 0, error: null });
  const [reviewMatch, setReviewMatch] = useState_(null);
  const [decisions, setDecisions] = useState_({});

  const openCompany = async (num) => {
    setView("dossier"); setNumber(num);
    setDossier(null); setScreening(null);
    setScreenState({ running: false, step: 0, error: null }); setDecisions({});
    try { setDossier(await window.KYB.dossier(num)); }
    catch (e) { setDossier({ profile: {}, error: e.message }); }
  };

  const runScreen = async () => {
    setScreenState({ running: true, step: 0, error: null });
    const tick = setInterval(() => setScreenState(s =>
      s.running ? { ...s, step: Math.min(s.step + 1, window.SCREEN_STEPS.length - 1) } : s), 750);
    try {
      const res = await window.KYB.screen(number);
      setScreening(res);
      setScreenState({ running: false, step: 0, error: null });
    } catch (e) {
      setScreenState({ running: false, step: 0, error: e.message });
    } finally { clearInterval(tick); }
  };

  const onDecide = async (match, decision, note) => {
    setDecisions(d => ({ ...d, [match.id]: decision }));
    setReviewMatch(null);
    try { await window.KYB.decide(match.id, decision, note); } catch (e) { /* demo: persistence optional */ }
  };

  const goHome = () => setView("search");

  return (
    <div className="app">
      <KybTopbar onHome={goHome} />
      {view === "search" && <SearchView onOpen={openCompany} />}
      {view === "dossier" && dossier &&
        <DossierView number={number} dossier={dossier} screening={screening}
          screenState={screenState} onScreen={runScreen} onReview={setReviewMatch}
          decisions={decisions} onBack={goHome} />}
      <MatchDrawer match={reviewMatch} onClose={() => setReviewMatch(null)} onDecide={onDecide} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<KybApp />);
