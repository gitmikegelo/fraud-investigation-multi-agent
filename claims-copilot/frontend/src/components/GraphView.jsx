import { useMemo } from 'react'

/**
 * Graph nodes layout (fixed positions for clarity):
 *
 *          [START]
 *             |
 *        [Analysis] ← Isolation Forest + Connection Analysis
 *             |
 *        [Orchestrator]  ←──── [Dossier]
 *             |                    ↑
 *       [Investigation] ──────────┘
 *             |
 *           [END]
 *
 * We lay this out on an SVG canvas.
 */

const NODES = [
  { id: 'start',         x: 300, y: 20,  label: 'START',          type: 'terminal' },
  { id: 'analysis',      x: 300, y: 85,  label: 'Initial Analysis', type: 'analysis', desc: 'Isolation Forest • Graph Analysis' },
  { id: 'orchestrator',  x: 300, y: 165, label: 'Orchestrator',   type: 'agent',   desc: 'Lead Investigator' },
  { id: 'investigation', x: 150, y: 270, label: 'Investigation',  type: 'agent',   desc: 'Detective Agent' },
  { id: 'dossier',       x: 450, y: 270, label: 'Dossier',        type: 'agent',   desc: 'Case Writer' },
  { id: 'end',           x: 300, y: 340, label: 'END',            type: 'terminal' },
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

const NODE_COLORS = {
  start:         { bg: '#1e293b', border: '#475569', text: '#94a3b8' },
  analysis:      { bg: '#3b0764', border: '#a855f7', text: '#d8b4fe' },
  orchestrator:  { bg: '#172554', border: '#3b82f6', text: '#93c5fd' },
  investigation: { bg: '#14532d', border: '#22c55e', text: '#86efac' },
  dossier:       { bg: '#451a03', border: '#f59e0b', text: '#fcd34d' },
  end:           { bg: '#1e293b', border: '#475569', text: '#94a3b8' },
}

const ACTIVE_GLOW = {
  start:         '#a855f7',
  analysis:      '#a855f7',
  orchestrator:  '#3b82f6',
  investigation: '#22c55e',
  dossier:       '#f59e0b',
}

// Node dimensions
function getNodeDimensions(id) {
  const node = NODES.find(n => n.id === id)
  if (!node) return { w: 0, h: 0 }
  const isTerminal = node.type === 'terminal'
  const isAnalysis = node.type === 'analysis'
  return {
    w: isTerminal ? 80 : isAnalysis ? 150 : 130,
    h: isTerminal ? 30 : 50
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
    // Horizontal-ish: exit from side
    startX = a.x + (dx > 0 ? dimA.w / 2 : -dimA.w / 2)
    startY = a.y
  } else {
    // Vertical-ish: exit from top/bottom
    startX = a.x
    startY = a.y + (dy > 0 ? dimA.h / 2 : -dimA.h / 2)
  }

  // Determine end point (to node edge)
  if (Math.abs(dx) > Math.abs(dy)) {
    // Horizontal-ish: enter from side
    endX = b.x + (dx > 0 ? -dimB.w / 2 - 4 : dimB.w / 2 + 4)
    endY = b.y
  } else {
    // Vertical-ish: enter from top/bottom
    endX = b.x
    endY = b.y + (dy > 0 ? -dimB.h / 2 - 4 : dimB.h / 2 + 4)
  }

  // For edges that go back up (investigation→orchestrator, dossier→orchestrator),
  // use a curve and adjust attachment points
  if (b.y < a.y) {
    // Exit from top of source node
    startY = a.y - dimA.h / 2
    // Enter from bottom of target node
    endY = b.y + dimB.h / 2 + 4
    
    const midX = (startX + endX) / 2 + (dx > 0 ? -50 : 50)
    const midY = (startY + endY) / 2
    return `M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`
  }

  // Check if diagonal - use slight curve for orchestrator -> investigation/dossier
  if (from === 'orchestrator' && (to === 'investigation' || to === 'dossier')) {
    // Exit from bottom-left or bottom-right
    startX = a.x + (dx > 0 ? 30 : -30)
    startY = a.y + dimA.h / 2
    // Enter from top of target
    endX = b.x
    endY = b.y - dimB.h / 2 - 4
    
    const cX = startX
    const cY = endY - 20
    return `M ${startX} ${startY} Q ${cX} ${cY} ${endX} ${endY}`
  }

  return `M ${startX} ${startY} L ${endX} ${endY}`
}

export default function GraphView({ activeNode, phase, nodeHistory, isRunning, initialClaims = [] }) {
  // Determine which nodes have been visited (for completed styling)
  const visitedSet = useMemo(() => new Set(nodeHistory), [nodeHistory])

  // Determine active edge based on the last transition (previous node -> current node)
  const activeEdge = useMemo(() => {
    if (!activeNode || nodeHistory.length < 2) return null
    // Find the last occurrence of activeNode in history and get the node before it
    for (let i = nodeHistory.length - 1; i >= 0; i--) {
      if (nodeHistory[i] === activeNode && i > 0) {
        const prev = nodeHistory[i - 1]
        return `${prev}->${activeNode}`
      }
    }
    return null
  }, [activeNode, nodeHistory])

  // Get the color for the active edge based on source node
  const getEdgeColor = (from, isActive) => {
    if (!isActive) return '#2d3748'
    // Use the source node's color for the arrow
    if (from === 'start') return '#a855f7'
    if (from === 'analysis') return '#a855f7'
    if (from === 'orchestrator') return '#3b82f6'
    if (from === 'investigation') return '#22c55e'
    if (from === 'dossier') return '#f59e0b'
    return '#3b82f6'
  }

  // Show claims panel only after analysis is done (once orchestrator appears in history)
  const analysisComplete = nodeHistory.includes('orchestrator')

  console.log('GraphView debug:', { nodeHistory, initialClaims, analysisComplete, activeNode })

  return (
    <div className="w-full h-full flex" style={{ background: 'var(--c-bg)' }}>
      {/* Initial Claims Panel - only shown after analysis completes */}
      {analysisComplete && initialClaims.length > 0 && (
        <div 
          className="flex-shrink-0 overflow-y-auto p-3"
          style={{ 
            width: '180px', 
            borderRight: '1px solid var(--c-border)',
            background: 'var(--c-surface)'
          }}
        >
          <div className="text-xs font-semibold mb-2" style={{ color: 'var(--c-text-dim)' }}>
            INITIAL CLAIMS ({initialClaims.length})
          </div>
          <div className="space-y-1.5">
            {initialClaims.map((claim, i) => (
              <div 
                key={claim.entity_id || i}
                className="p-2 rounded text-xs"
                style={{ 
                  background: 'var(--c-bg)', 
                  border: '1px solid var(--c-border)' 
                }}
              >
                <div className="font-medium truncate" style={{ color: 'var(--c-text)' }}>
                  {claim.entity_id}
                </div>
                <div className="flex justify-between mt-1" style={{ color: 'var(--c-text-dim)' }}>
                  <span>Score: {claim.anomaly_score}</span>
                  <span 
                    className="px-1 rounded text-[10px]"
                    style={{ 
                      background: claim.anomaly_score >= 0.7 ? '#ef444420' : '#f59e0b20',
                      color: claim.anomaly_score >= 0.7 ? '#ef4444' : '#f59e0b'
                    }}
                  >
                    {claim.anomaly_score >= 0.7 ? 'HIGH' : 'MED'}
                  </span>
                </div>
                {claim.total_billed > 0 && (
                  <div className="mt-1" style={{ color: 'var(--c-text-dim)' }}>
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
        <svg viewBox="0 0 600 380" className="w-full h-full max-w-[600px]">
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#475569" />
            </marker>
            <marker id="arrowhead-purple" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#a855f7" />
            </marker>
            <marker id="arrowhead-blue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6" />
            </marker>
            <marker id="arrowhead-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#22c55e" />
          </marker>
          <marker id="arrowhead-amber" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#f59e0b" />
          </marker>
          {/* Glow filters */}
          {Object.entries(ACTIVE_GLOW).map(([id, color]) => (
            <filter key={id} id={`glow-${id}`} x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor={color} floodOpacity="0.6" />
            </filter>
          ))}
          {/* Edge glow filters */}
          <filter id="edge-glow-purple" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#a855f7" floodOpacity="0.8" />
          </filter>
          <filter id="edge-glow-blue" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#3b82f6" floodOpacity="0.8" />
          </filter>
          <filter id="edge-glow-green" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#22c55e" floodOpacity="0.8" />
          </filter>
          <filter id="edge-glow-amber" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#f59e0b" floodOpacity="0.8" />
          </filter>
        </defs>

        {/* Edges */}
        {EDGES.map((edge, i) => {
          const key = `${edge.from}->${edge.to}`
          const isActive = activeEdge === key
          const path = edgePath(edge.from, edge.to)
          const edgeColor = getEdgeColor(edge.from, isActive)
          
          // Determine arrow marker and glow based on source
          let arrowMarker = 'url(#arrowhead)'
          let glowFilter = undefined
          if (isActive) {
            if (edge.from === 'start' || edge.from === 'analysis') {
              arrowMarker = 'url(#arrowhead-purple)'
              glowFilter = 'url(#edge-glow-purple)'
            } else if (edge.from === 'investigation') {
              arrowMarker = 'url(#arrowhead-green)'
              glowFilter = 'url(#edge-glow-green)'
            } else if (edge.from === 'dossier') {
              arrowMarker = 'url(#arrowhead-amber)'
              glowFilter = 'url(#edge-glow-amber)'
            } else {
              arrowMarker = 'url(#arrowhead-blue)'
              glowFilter = 'url(#edge-glow-blue)'
            }
          }

          return (
            <g key={i}>
              <path
                d={path}
                fill="none"
                stroke={edgeColor}
                strokeWidth={isActive ? 3 : 1.5}
                className={isActive ? 'edge-active' : ''}
                markerEnd={arrowMarker}
                filter={isActive ? glowFilter : undefined}
                opacity={isActive ? 1 : 0.4}
              />
              {/* Edge label */}
              {edge.label && (() => {
                const a = getNodePos(edge.from)
                const b = getNodePos(edge.to)
                let lx = (a.x + b.x) / 2
                let ly = (a.y + b.y) / 2
                
                // Adjust label position for curved paths
                if (b.y < a.y) {
                  // Return paths - offset label outward
                  lx += (b.x > a.x ? -35 : 35)
                } else if (edge.from === 'orchestrator' && (edge.to === 'investigation' || edge.to === 'dossier')) {
                  // Diagonal paths
                  ly -= 10
                }
                
                return (
                  <text
                    x={lx}
                    y={ly}
                    textAnchor="middle"
                    fill={isActive ? edgeColor : '#4a5568'}
                    fontSize="9"
                    fontWeight={isActive ? '600' : '400'}
                  >
                    {edge.label}
                  </text>
                )
              })()}
            </g>
          )
        })}

        {/* Nodes */}
        {NODES.map((node) => {
          const colors = NODE_COLORS[node.id]
          const isActive = activeNode === node.id
          const isVisited = visitedSet.has(node.id)
          const isTerminal = node.type === 'terminal'
          const dims = getNodeDimensions(node.id)
          const w = dims.w
          const h = dims.h
          const rx = isTerminal ? 15 : 10

          return (
            <g key={node.id}>
              {/* Active glow pulse */}
              {isActive && ACTIVE_GLOW[node.id] && (
                <rect
                  x={node.x - w / 2 - 4}
                  y={node.y - h / 2 - 4}
                  width={w + 8}
                  height={h + 8}
                  rx={rx + 4}
                  fill="none"
                  stroke={ACTIVE_GLOW[node.id]}
                  strokeWidth="2"
                  opacity="0.3"
                  className="node-pulse"
                />
              )}

              {/* Node body */}
              <rect
                x={node.x - w / 2}
                y={node.y - h / 2}
                width={w}
                height={h}
                rx={rx}
                fill={colors.bg}
                stroke={isActive ? ACTIVE_GLOW[node.id] || colors.border : isVisited ? colors.border : '#2d3748'}
                strokeWidth={isActive ? 2.5 : 1.5}
                filter={isActive && ACTIVE_GLOW[node.id] ? `url(#glow-${node.id})` : undefined}
                opacity={isActive ? 1 : isVisited ? 0.9 : 0.6}
              />

              {/* Node label */}
              <text
                x={node.x}
                y={node.y + (isTerminal ? 1 : -3)}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={isActive ? '#ffffff' : colors.text}
                fontSize={isTerminal ? '10' : '12'}
                fontWeight="600"
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
                  fill={isActive ? colors.text : '#4a5568'}
                  fontSize="8"
                >
                  {node.desc}
                </text>
              )}

              {/* Visited checkmark */}
              {isVisited && !isActive && !isTerminal && (
                <circle
                  cx={node.x + w / 2 - 6}
                  cy={node.y - h / 2 + 6}
                  r="6"
                  fill="#22c55e"
                >
                </circle>
              )}
            </g>
          )
        })}
        </svg>
      </div>
    </div>
  )
}
