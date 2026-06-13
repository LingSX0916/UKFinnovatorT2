/* ============================================================
   kyb-graph.jsx — interactive SVG ownership / UBO graph.
   No build step, so no React Flow: a small layered layout drawn
   as SVG. Nodes are coloured by screening verdict; edges carry
   the effective control %. Clicking a node selects its subject.
   Exposes: OwnershipGraph
   ============================================================ */

function OwnershipGraph({ graph, onSelect, selectedId }) {
  if (!graph || !graph.nodes || !graph.nodes.length) {
    return <div className="empty-note"><Icon name="info" size={16} /> No ownership data.</div>;
  }
  const NODE_W = 184, NODE_H = 58, COL = 250, ROW = 86, PAD = 24;

  // group nodes by depth -> columns (depth 0 = target company on the left)
  const byDepth = {};
  graph.nodes.forEach(n => { (byDepth[n.depth] = byDepth[n.depth] || []).push(n); });
  const depths = Object.keys(byDepth).map(Number).sort((a, b) => a - b);
  const pos = {};
  let maxRows = 0;
  depths.forEach(d => {
    byDepth[d].forEach((n, i) => {
      pos[n.id] = { x: PAD + d * COL, y: PAD + i * ROW };
    });
    maxRows = Math.max(maxRows, byDepth[d].length);
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
    // owner (a) sits to the right; it controls the node to its left (b)
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
        {graph.edges.map((e, i) => {
          const d = edgePath(e.from, e.to);
          if (!d) return null;
          const a = pos[e.from], b = pos[e.to];
          const lx = (a.x + b.x + NODE_W) / 2, ly = (a.y + b.y) / 2 + NODE_H / 2 - 8;
          const label = e.effective_pct != null ? (e.ownership_band || (e.effective_pct + "%")) : "";
          return (
            <g key={i}>
              <path d={d} className="ubo-edge" markerEnd="url(#arrow)" />
              {label ? <text x={lx} y={ly} className="ubo-edge-label" textAnchor="middle">{label}</text> : null}
            </g>
          );
        })}
        {graph.nodes.map(n => {
          const p = pos[n.id]; const t = tone(n);
          const sel = n.id === selectedId;
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`}
               className={"ubo-node " + t + (sel ? " sel" : "") + (n.is_target ? " target" : "")}
               onClick={() => onSelect && onSelect(n)} style={{ cursor: "pointer" }}>
              <rect width={NODE_W} height={NODE_H} rx="8" />
              <text x="12" y="23" className="ubo-name">{(n.name || "").slice(0, 26)}</text>
              <text x="12" y="42" className="ubo-sub">
                {n.kind === "company" ? "Company" : n.kind === "entity" ? "Entity" : "Individual"}
                {n.effective_pct != null && !n.is_target ? ` · ${n.effective_pct}% effective` : ""}
                {n.is_target ? " · subject" : ""}
              </text>
              {n.screening && n.screening.verdict ? (
                <circle cx={NODE_W - 14} cy="16" r="6" className={"ubo-dot " + t} />
              ) : null}
            </g>
          );
        })}
      </svg>
      <div className="ubo-legend">
        <span><i className="lg red" /> Sanctions / Warning hit</span>
        <span><i className="lg amber" /> Possible match</span>
        <span><i className="lg green" /> Clear</span>
        <span><i className="lg co" /> Company in chain</span>
        <span className="ubo-hint">Arrows point from owner → controlled entity · click a node for detail</span>
      </div>
    </div>
  );
}

Object.assign(window, { OwnershipGraph });
