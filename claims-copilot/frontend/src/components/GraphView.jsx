import { useMemo } from 'react'

/**
 * Graph nodes layout (fixed positions for clarity):
 *
 *          [START]
 *             |
 *        [Analysis]  ←  Isolation Forest · Graph Analysis
 *             |
 *        [Orchestrator]  ←──── [Dossier]
 *             |                    ↑
 *       [Investigation] ──────────┘
 *             |
 *           [END]
 *
 * We lay this out on an SVG canvas, scoped to a dark "operations console" theme.
 */

const NODES = [
  { id: 'start',         x: 300, y: 24,  label: 'START',            type: 'terminal' },
  { id: 'analysis',      x: 300, y: 92,  label: 'Initial Analysis', type: 'analysis', desc: 'Isolation Forest · Graph Analysis' },
  { id: 'orchestrator',  x: 300, y: 172, label: 'Orchestrator',     type: 'agent',   desc: 'Lead Investigator' },
  { id: 'investigation', x: 150, y: 278, label: 'Investigation',    type: 'agent',   desc: 'Detective Agent' },
  { id: 'dossier',       x: 450, y: 278, label: 'Dossier',          type: 'agent',   desc: 'Case Writer' },
  { id: 'end',           x: 300, y: 348, label: 'END',              type: 'terminal' },
]

const EDGES = [
  { from: 'start',         to: 'analysis',       label: '' },
  { from: 'analysis',      to: 'orchestrator',   label: 'anomalies detected' },
  { from: 'orchestrator',  to: 'investigation',  label: 'investigate' },
  { from: 'orchestrator',  to: 'dossier',        label: 'compile' },
  { from: 'orchestrator',  to: 'end',            label: 'done' },
  { from: 'investigation', to: 'orchestrator',   label: 'report' },
  { from: 'dossier',       to: 'orchestrator',   label: 'assess' },
]

// ── One accent system ────────────────────────────────────────────────
//   purple  → orchestrator / control (+ start/analysis = control entry)
//   green   → active / processing (investigation)
//   amber   → output / writer (dossier)
//   neutral → terminals (start / end)
const ACCENT = {
  purple:  '#a855f7',
  green:   '#22c55e',
  amber:   '#f59e0b',
  neutral: '#64748b',
}

// Role assignment per node, on the dark canvas
const NODE_ROLE = {
  start:         'neutral',
  analysis:      'purple',
  orchestrator:  'purple',
  investigation: 'green',
  dossier:       'amber',
  end:           'neutral',
}

// Dark-canvas node surface tints (subtle, accent-derived)
const NODE_SURFACE = {
  neutral: '#1a2030',
  purple:  '#231a36',
  green:   '#13261c',
  amber:   '#2a2113',
}

function nodeSurface(id) { return NODE_SURFACE[NODE_ROLE[id]] || NODE_SURFACE.neutral }

// Node dimensions
function getNodeDimensions(id) {
  const node = NODES.find(n => n.id === id)
  if (!node) return { w: 0, h: 0 }
  const isTerminal = node.type === 'terminal'
  const isAnalysis = node.type === 'analysis'
  return {
    w: isTerminal ? 84 : isAnalysis ? 184 : 140,
    h: isTerminal ? 30 : 52
  }
}

function getNodePos(id) {
  return NODES.find(n => n.id === id)
}

function edgePath(from, to) {
  const a = getNodePos(from)
  const b = getNodePos(to)
  if (!a || !b) return ''

  const dimA = getNodeDimensions(from)
  const dimB = getNodeDimensions(to)

  // Calculate edge attachment points based on direction
  const dx = b.x - a.x
  const dy = b.y - a.y

  let startX, startY, endX, endY

  // Determine start point (from node edge)
  if (Math.abs(dx) > Math.abs(dy)) {
    startX = a.x + (dx > 0 ? dimA.w / 2 : -dimA.w / 2)
    startY = a.y
  } else {
    startX = a.x
    startY = a.y + (dy > 0 ? dimA.h / 2 : -dimA.h / 2)
  }

  // Determine end point (to node edge)
  if (Math.abs(dx) > Math.abs(dy)) {
    endX = b.x + (dx > 0 ? -dimB.w / 2 - 4 : dimB.w / 2 + 4)
    endY = b.y
  } else {
    endX = b.x
    endY = b.y + (dy > 0 ? -dimB.h / 2 - 4 : dimB.h / 2 + 4)
  }

  // Edges that go back up (investigation→orchestrator, dossier→orchestrator):
  // curve and adjust attachment points.
  if (b.y < a.y) {
    startY = a.y - dimA.h / 2
    endY = b.y + dimB.h / 2 + 4

    const midX = (startX + endX) / 2 + (dx > 0 ? -50 : 50)
    const midY = (startY + endY) / 2
    return `M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`
  }

  // Diagonal slight curve for orchestrator -> investigation/dossier
  if (from === 'orchestrator' && (to === 'investigation' || to === 'dossier')) {
    startX = a.x + (dx > 0 ? 30 : -30)
    startY = a.y + dimA.h / 2
    endX = b.x
    endY = b.y - dimB.h / 2 - 4

    const cX = startX
    const cY = endY - 20
    return `M ${startX} ${startY} Q ${cX} ${cY} ${endX} ${endY}`
  }

  return `M ${startX} ${startY} L ${endX} ${endY}`
}

const CANVAS_BG = '#10141d'
const IDLE_EDGE = '#323a4d'
const DIM_OPACITY = 0.4

export default function GraphView({ activeNode, nodeHistory, isRunning, loopCount = 0, elapsed = 0, initialClaims = [] }) {
  // Determine which nodes have been visited (for completed styling)
  const visitedSet = useMemo(() => new Set(nodeHistory), [nodeHistory])

  // Active edge = last transition (previous node -> current node)
  const activeEdge = useMemo(() => {
    if (!activeNode || nodeHistory.length < 2) return null
    for (let i = nodeHistory.length - 1; i >= 0; i--) {
      if (nodeHistory[i] === activeNode && i > 0) {
        const prev = nodeHistory[i - 1]
        return `${prev}->${activeNode}`
      }
    }
    return null
  }, [activeNode, nodeHistory])

  // Show claims panel only after analysis is done (once orchestrator appears in history)
  const analysisComplete = nodeHistory.includes('orchestrator')

  // Only render nodes that actually exist in the layout (no ghost/placeholder nodes)
  const renderableNodes = NODES.filter(n => n.label && n.label.trim().length > 0)

  return (
    <div
      className="w-full h-full flex"
      style={{
        // Dark canvas treatment is scoped to this panel only
        background: `radial-gradient(120% 90% at 50% 0%, #161b27 0%, ${CANVAS_BG} 70%)`,
      }}
    >
      {/* Initial Claims Panel — only shown after analysis completes */}
      {analysisComplete && initialClaims.length > 0 && (
        <div
          className="flex-shrink-0 overflow-y-auto p-3"
          style={{
            width: '180px',
            borderRight: '1px solid rgba(255,255,255,0.06)',
            background: 'rgba(255,255,255,0.02)',
          }}
        >
          <div className="text-[11px] font-semibold mb-2 tracking-wide" style={{ color: '#8b93a7' }}>
            INITIAL CLAIMS ({initialClaims.length})
          </div>
          <div className="space-y-1.5">
            {initialClaims.map((claim, i) => (
              <div
                key={claim.entity_id || i}
                className="p-2 rounded-lg text-xs"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.07)',
                }}
              >
                <div className="font-medium truncate" style={{ color: '#e6e9f0' }}>
                  {claim.entity_id}
                </div>
                <div className="flex justify-between mt-1" style={{ color: '#8b93a7' }}>
                  <span>Score: {claim.anomaly_score}</span>
                  <span
                    className="px-1.5 rounded text-[10px] font-semibold"
                    style={{
                      background: claim.anomaly_score >= 0.7 ? 'rgba(239,68,68,0.18)' : 'rgba(245,158,11,0.18)',
                      color: claim.anomaly_score >= 0.7 ? '#fca5a5' : '#fcd34d',
                    }}
                  >
                    {claim.anomaly_score >= 0.7 ? 'HIGH' : 'MED'}
                  </span>
                </div>
                {claim.total_billed > 0 && (
                  <div className="mt-1" style={{ color: '#8b93a7' }}>
                    ${claim.total_billed.toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Graph Area */}
      <div className="flex-1 flex items-center justify-center">
        <svg viewBox="0 0 600 380" className="w-full h-full max-w-[640px]">
          <defs>
            {/* Neutral idle arrowhead */}
            <marker id="ag-arrow-idle" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">
              <polygon points="0 0, 9 3.5, 0 7" fill={IDLE_EDGE} />
            </marker>
            {/* Accent arrowheads */}
            {Object.entries(ACCENT).map(([role, color]) => (
              <marker key={role} id={`ag-arrow-${role}`} markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">
                <polygon points="0 0, 9 3.5, 0 7" fill={color} />
              </marker>
            ))}

            {/* Node glow filters (soft outer glow per accent) */}
            {Object.entries(ACCENT).map(([role, color]) => (
              <filter key={role} id={`ag-glow-${role}`} x="-60%" y="-60%" width="220%" height="220%">
                <feDropShadow dx="0" dy="0" stdDeviation="7" floodColor={color} floodOpacity="0.7" />
              </filter>
            ))}

            {/* Active edge glow */}
            {Object.entries(ACCENT).map(([role, color]) => (
              <filter key={role} id={`ag-edge-glow-${role}`} x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor={color} floodOpacity="0.85" />
              </filter>
            ))}
          </defs>

          {/* ── Edges ────────────────────────────────────────────── */}
          {EDGES.map((edge, i) => {
            const key = `${edge.from}->${edge.to}`
            const isActive = activeEdge === key
            const path = edgePath(edge.from, edge.to)
            const role = NODE_ROLE[edge.from] || 'neutral'
            const accent = ACCENT[role]

            return (
              <g key={i}>
                {/* Base edge — single neutral gray when idle, accent when active */}
                <path
                  d={path}
                  fill="none"
                  stroke={isActive ? accent : IDLE_EDGE}
                  strokeWidth={isActive ? 2.5 : 1.4}
                  markerEnd={isActive ? `url(#ag-arrow-${role})` : 'url(#ag-arrow-idle)'}
                  opacity={isActive ? 1 : 0.5}
                />
                {/* Flowing dashed gradient overlay on the active edge */}
                {isActive && (
                  <path
                    d={path}
                    fill="none"
                    stroke={accent}
                    strokeWidth={2.5}
                    strokeLinecap="round"
                    className="console-edge-active"
                    filter={`url(#ag-edge-glow-${role})`}
                    opacity={0.95}
                  />
                )}
                {/* Travelling particle on the active edge */}
                {isActive && (
                  <circle r="3" fill="#ffffff" opacity="0.9">
                    <animateMotion dur="0.7s" repeatCount="indefinite" path={path} />
                  </circle>
                )}

                {/* Edge label — bright when active, dimmed when idle */}
                {edge.label && (() => {
                  const a = getNodePos(edge.from)
                  const b = getNodePos(edge.to)
                  let lx = (a.x + b.x) / 2
                  let ly = (a.y + b.y) / 2

                  if (b.y < a.y) {
                    lx += (b.x > a.x ? -35 : 35)
                  } else if (edge.from === 'orchestrator' && (edge.to === 'investigation' || edge.to === 'dossier')) {
                    ly -= 10
                  }

                  return (
                    <text
                      x={lx}
                      y={ly}
                      textAnchor="middle"
                      fill={isActive ? accent : '#5b6478'}
                      fontSize="9"
                      fontWeight={isActive ? '600' : '400'}
                      opacity={isActive ? 1 : 0.6}
                      style={{ fontFamily: 'Inter, system-ui, sans-serif' }}
                    >
                      {edge.label}
                    </text>
                  )
                })()}
              </g>
            )
          })}

          {/* ── Nodes ────────────────────────────────────────────── */}
          {renderableNodes.map((node) => {
            const isActive = activeNode === node.id
            const isVisited = visitedSet.has(node.id)
            const isTerminal = node.type === 'terminal'
            const role = NODE_ROLE[node.id] || 'neutral'
            const accent = ACCENT[role]
            const surface = nodeSurface(node.id)
            const dims = getNodeDimensions(node.id)
            const w = dims.w
            const h = dims.h
            const rx = isTerminal ? 15 : 12

            // Attention model: active = full, visited = ~0.85, inactive dimmed
            const groupOpacity = isActive ? 1 : isVisited ? 0.85 : DIM_OPACITY

            return (
              <g key={node.id} style={{ opacity: groupOpacity, transition: 'opacity 0.3s ease' }}>
                {/* Breathing halo behind the active node */}
                {isActive && (
                  <rect
                    x={node.x - w / 2 - 5}
                    y={node.y - h / 2 - 5}
                    width={w + 10}
                    height={h + 10}
                    rx={rx + 5}
                    fill="none"
                    stroke={accent}
                    strokeWidth="2"
                    className="console-node-halo"
                  />
                )}

                {/* Node body (scales up briefly on handoff via console-node-active) */}
                <g className={isActive ? 'console-node-active' : undefined}>
                  <rect
                    x={node.x - w / 2}
                    y={node.y - h / 2}
                    width={w}
                    height={h}
                    rx={rx}
                    fill={surface}
                    stroke={isActive || isVisited ? accent : '#2b3346'}
                    strokeWidth={isActive ? 2.25 : 1.4}
                    filter={isActive ? `url(#ag-glow-${role})` : undefined}
                  />

                  {/* Node label */}
                  <text
                    x={node.x}
                    y={node.y + (isTerminal ? 1 : -4)}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={isActive ? '#ffffff' : isVisited ? '#dfe3ec' : '#aeb6c7'}
                    fontSize={isTerminal ? '10' : '12.5'}
                    fontWeight="600"
                    style={{ fontFamily: 'Inter, system-ui, sans-serif' }}
                  >
                    {node.label}
                  </text>

                  {/* Sub-label */}
                  {!isTerminal && node.desc && (
                    <text
                      x={node.x}
                      y={node.y + 13}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill={isActive ? accent : '#7f879b'}
                      fontSize="8.5"
                      style={{ fontFamily: 'Inter, system-ui, sans-serif' }}
                    >
                      {node.desc}
                    </text>
                  )}
                </g>

                {/* Loop / timer progress ring around the active agent node */}
                {isActive && !isTerminal && isRunning && (
                  <LoopRing cx={node.x + w / 2 - 4} cy={node.y - h / 2 + 4} accent={accent} loopCount={loopCount} elapsed={elapsed} />
                )}

                {/* Visited checkmark */}
                {isVisited && !isActive && !isTerminal && (
                  <g>
                    <circle cx={node.x + w / 2 - 8} cy={node.y - h / 2 + 8} r="7" fill={ACCENT.green} />
                    <path
                      d={`M ${node.x + w / 2 - 11} ${node.y - h / 2 + 8} l 2 2 l 4 -4`}
                      fill="none" stroke="#0b1019" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
                    />
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}

/**
 * Thin circular progress ring rendered around the active node.
 * Fills over the loop duration so "Loop 3 · 18s" has a visceral feel.
 */
function LoopRing({ cx, cy, accent, loopCount, elapsed }) {
  const r = 11
  const circ = 2 * Math.PI * r
  // Fill cycles every ~24s of the current loop (visual cadence, not exact)
  const LOOP_SECONDS = 24
  const progress = (elapsed % LOOP_SECONDS) / LOOP_SECONDS
  const dash = circ * progress

  return (
    <g>
      {/* Track */}
      <circle cx={cx} cy={cy} r={r} fill="#0b1019" stroke="rgba(255,255,255,0.12)" strokeWidth="2.5" />
      {/* Progress arc (rotated so it starts at 12 o'clock) */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={accent}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circ}`}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dasharray 0.9s linear' }}
      />
      {/* Loop count */}
      <text
        x={cx}
        y={cy + 0.5}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#ffffff"
        fontSize="9"
        fontWeight="700"
        style={{ fontFamily: 'Inter, system-ui, sans-serif' }}
      >
        {loopCount > 0 ? loopCount : ''}
      </text>
    </g>
  )
}
