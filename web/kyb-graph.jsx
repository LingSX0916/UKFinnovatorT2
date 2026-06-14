/* ============================================================
   kyb-graph.jsx — interactive SVG ownership / UBO graph.
   No build step, so no React Flow: a small layered layout drawn
   as SVG. Nodes are coloured by screening verdict; edges carry
   the effective control %. Clicking a node selects its subject.
   Exposes: OwnershipGraph
   ============================================================ */

/* split a long name onto two lines (break at a space), so node text isn't
   truncated to "Dmitry Konstantinovich Kis". Returns 1 or 2 lines. */
function wrapName(name, maxChars) {
  name = (name || "").trim();
  if (name.length <= maxChars) return [name];
  let cut = name.lastIndexOf(" ", maxChars);
  if (cut <= 0) cut = maxChars;
  let l1 = name.slice(0, cut).trim();
  let l2 = name.slice(cut).trim();
  if (l2.length > maxChars) l2 = l2.slice(0, maxChars - 1) + "…";
  return [l1, l2];
}

function OwnershipGraph({ graph, onSelect, selectedId }) {
  if (!graph || !graph.nodes || !graph.nodes.length) {
    return <div className="empty-note"><Icon name="info" size={16} /> No ownership data.</div>;
  }
  const NODE_W = 214, NODE_H = 64, COL = 284, ROW = 102, PAD = 30;

  // group nodes by depth -> columns (depth 0 = target company on the left)
  const byDepth = {};
  graph.nodes.forEach(n => { (byDepth[n.depth] = byDepth[n.depth] || []).push(n); });
  const depths = Object.keys(byDepth).map(Number).sort((a, b) => a - b);
  const maxRows = Math.max(1, ...depths.map(d => byDepth[d].length));
  const pos = {};
  depths.forEach(d => {
    const n = byDepth[d].length;
    const offset = ((maxRows - n) / 2) * ROW;  // vertically centre each column
    byDepth[d].forEach((node, i) => {
      pos[node.id] = { x: PAD + d * COL, y: PAD + offset + i * ROW };
    });
  });
  const width = PAD * 2 + (depths.length - 1) * COL + NODE_W;
  const height = PAD * 2 + Math.max(1, maxRows - 1) * ROW + NODE_H;

  const tone = (n) => {
    const v = n.screening && n.screening.verdict;
    if (v === "RED") return "red";
    if (v === "AMBER") return "amber";
    if (v === "GREEN") return "green";
    return n.kind === "company" ? "co" : "neutral";
  };

  const edgePath = (from, to) => {
    const a = pos[from], b = pos[to];
    if (!a || !b) return null;
    const x1 = a.x, y1 = a.y + NODE_H / 2;            // owner left-mid
    const x2 = b.x + NODE_W, y2 = b.y + NODE_H / 2;   // owned right-mid
    const mx = (x1 + x2) / 2;
    return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
  };

  return (
    <div className="ubo-wrap">
      <svg className="ubo-svg" viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label="Ownership graph">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill="var(--ink-400)" />
          </marker>
        </defs>
        {/* edges first, so nodes sit on top */}
        {graph.edges.map((e, i) => {
          const d = edgePath(e.from, e.to);
          if (!d) return null;
          const a = pos[e.from], b = pos[e.to];
          const lx = (a.x + b.x + NODE_W) / 2;
          const ly = (a.y + b.y) / 2 + NODE_H / 2;
          const label = e.effective_pct != null ? (e.ownership_band || (e.effective_pct + "%")) : "";
          const w = label.length * 6.6 + 12;
          return (
            <g key={i}>
              <path d={d} className="ubo-edge" markerEnd="url(#arrow)" />
              {label ? (
                <g transform={`translate(${lx},${ly})`}>
                  <rect x={-w / 2} y={-9} width={w} height={18} rx={9} className="ubo-edge-pill" />
                  <text x={0} y={4} className="ubo-edge-label" textAnchor="middle">{label}</text>
                </g>
              ) : null}
            </g>
          );
        })}
        {graph.nodes.map(n => {
          const p = pos[n.id]; const t = tone(n);
          const sel = n.id === selectedId;
          const lines = wrapName(n.name, 24);
          const two = lines.length === 2;
          const sub = (n.kind === "company" ? "Company" : n.kind === "entity" ? "Entity" : "Individual")
            + (n.effective_pct != null && !n.is_target ? ` · ${n.effective_pct}% effective` : "")
            + (n.is_target ? " · subject" : "");
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`}
               className={"ubo-node " + t + (sel ? " sel" : "") + (n.is_target ? " target" : "")}
               onClick={() => onSelect && onSelect(n)} style={{ cursor: "pointer" }}>
              <title>{n.name}{n.screening && n.screening.verdict ? ` — ${n.screening.verdict}` : ""}</title>
              <rect width={NODE_W} height={NODE_H} rx="10" />
              {two ? (
                <React.Fragment>
                  <text x="13" y="22" className="ubo-name">{lines[0]}</text>
                  <text x="13" y="38" className="ubo-name">{lines[1]}</text>
                  <text x="13" y="54" className="ubo-sub">{sub}</text>
                </React.Fragment>
              ) : (
                <React.Fragment>
                  <text x="13" y="27" className="ubo-name">{lines[0]}</text>
                  <text x="13" y="46" className="ubo-sub">{sub}</text>
                </React.Fragment>
              )}
              {n.screening && n.screening.verdict && n.screening.verdict !== "GREEN" ? (
                <circle cx={NODE_W - 15} cy="16" r="6" className={"ubo-dot " + t} />
              ) : null}
            </g>
          );
        })}
      </svg>
      <div className="ubo-legend">
        <span><i className="lg red" /> Sanctions / Warning hit</span>
        <span><i className="lg amber" /> Possible match</span>
        <span><i className="lg green" /> Clear</span>
        <span><i className="lg co" /> Subject company</span>
        <span className="ubo-hint">Arrows point owner → controlled entity · click a node for detail</span>
      </div>
    </div>
  );
}

Object.assign(window, { OwnershipGraph });
