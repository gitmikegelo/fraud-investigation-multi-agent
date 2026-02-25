import { useRef, useEffect, useState, useCallback } from 'react'

// ── Layout constants ─────────────────────────────────────────────────
const ENTITY_COLORS = {
  provider: { fill: '#1e3a5f', stroke: '#3b82f6', text: '#93c5fd', icon: 'P' },
  member:   { fill: '#1a332a', stroke: '#22c55e', text: '#86efac', icon: 'M' },
  facility: { fill: '#3b1f06', stroke: '#f59e0b', text: '#fcd34d', icon: 'F' },
  unknown:  { fill: '#1e293b', stroke: '#64748b', text: '#94a3b8', icon: '?' },
}

const EDGE_COLORS = {
  BILLED_FOR:  '#3b82f680',
  REFERRED_TO: '#f59e0b80',
  OPERATES_AT: '#22c55e80',
  CONNECTED:   '#64748b60',
}

const RING_COLORS = [
  '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899',
]

// ── Simple force-directed simulation ─────────────────────────────────
function forceSimulation(nodes, edges, width, height, iterations = 200) {
  const k = Math.sqrt((width * height) / Math.max(nodes.length, 1)) * 0.8
  const dt = 0.3

  // Initialize positions (circle layout as starting point)
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.length
    const r = Math.min(width, height) * 0.35
    n.x = width / 2 + r * Math.cos(angle) + (Math.random() - 0.5) * 20
    n.y = height / 2 + r * Math.sin(angle) + (Math.random() - 0.5) * 20
    n.vx = 0
    n.vy = 0
  })

  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]))

  for (let iter = 0; iter < iterations; iter++) {
    const cooling = 1 - iter / iterations

    // Repulsion between all nodes
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        let dx = nodes[i].x - nodes[j].x
        let dy = nodes[i].y - nodes[j].y
        let dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = (k * k) / dist
        const fx = (dx / dist) * force * dt * cooling
        const fy = (dy / dist) * force * dt * cooling
        nodes[i].vx += fx
        nodes[i].vy += fy
        nodes[j].vx -= fx
        nodes[j].vy -= fy
      }
    }

    // Attraction along edges
    edges.forEach(e => {
      const src = nodeMap[e.source]
      const tgt = nodeMap[e.target]
      if (!src || !tgt) return
      let dx = tgt.x - src.x
      let dy = tgt.y - src.y
      let dist = Math.sqrt(dx * dx + dy * dy) || 1
      const force = (dist * dist) / k
      const fx = (dx / dist) * force * dt * cooling * 0.1
      const fy = (dy / dist) * force * dt * cooling * 0.1
      src.vx += fx
      src.vy += fy
      tgt.vx -= fx
      tgt.vy -= fy
    })

    // Center gravity
    nodes.forEach(n => {
      const dx = width / 2 - n.x
      const dy = height / 2 - n.y
      n.vx += dx * 0.001 * cooling
      n.vy += dy * 0.001 * cooling
    })

    // Apply velocity with damping
    nodes.forEach(n => {
      n.x += n.vx
      n.y += n.vy
      n.vx *= 0.6
      n.vy *= 0.6
      // Bound
      n.x = Math.max(40, Math.min(width - 40, n.x))
      n.y = Math.max(40, Math.min(height - 40, n.y))
    })
  }

  return nodes
}

// ── Anomaly → size mapping ───────────────────────────────────────────
function nodeRadius(anomaly) {
  return 10 + anomaly * 18
}

// ── Component ────────────────────────────────────────────────────────
export default function NetworkGraph({ isComplete }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hoveredNode, setHoveredNode] = useState(null)
  const [selectedRing, setSelectedRing] = useState(null)
  const [focusEntity, setFocusEntity] = useState(null)
  const svgRef = useRef(null)
  const [dims, setDims] = useState({ w: 800, h: 500 })

  // Resize observer
  useEffect(() => {
    const container = svgRef.current?.parentElement
    if (!container) return
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        setDims({ w: entry.contentRect.width, h: entry.contentRect.height })
      }
    })
    ro.observe(container)
    return () => ro.disconnect()
  }, [])

  // Fetch data
  const fetchNetwork = useCallback(async (entity = null) => {
    setLoading(true)
    setError(null)
    try {
      const url = entity
        ? `/api/fraud-network?focus_entity=${encodeURIComponent(entity)}&depth=2`
        : '/api/fraud-network?min_anomaly=0.5&min_ring_size=3'
      const res = await fetch(url)
      const json = await res.json()
      if (json.error) { setError(json.error); return }

      // Run layout
      const laid = forceSimulation([...json.nodes], json.edges, dims.w, dims.h)
      setData({ ...json, nodes: laid })
      setSelectedRing(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [dims])

  // Auto-fetch when investigation completes
  useEffect(() => {
    if (isComplete) fetchNetwork()
  }, [isComplete])

  // Focus on entity
  const handleFocus = useCallback((entityId) => {
    setFocusEntity(entityId)
    fetchNetwork(entityId)
  }, [fetchNetwork])

  // Back to rings view
  const handleBackToRings = useCallback(() => {
    setFocusEntity(null)
    fetchNetwork(null)
  }, [fetchNetwork])

  if (!isComplete && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="text-4xl opacity-20">🕸️</div>
          <p className="text-sm" style={{ color: 'var(--c-text-dim)' }}>
            Fraud network will appear once the investigation completes
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--c-text-dim)' }}>
          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="50 20" />
          </svg>
          Loading network…
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm" style={{ color: 'var(--c-red)' }}>Error: {error}</p>
      </div>
    )
  }

  if (!data) return null

  const { nodes, edges, rings, mode } = data

  // Filter by selected ring
  const visibleNodes = selectedRing !== null
    ? nodes.filter(n => n.ring_index === selectedRing)
    : nodes
  const visibleIds = new Set(visibleNodes.map(n => n.id))
  const visibleEdges = edges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target))

  const nodeMap = Object.fromEntries(visibleNodes.map(n => [n.id, n]))
  const hovered = hoveredNode ? nodeMap[hoveredNode] : null

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 px-4 py-2 flex-shrink-0 flex-wrap"
        style={{ borderBottom: '1px solid var(--c-border)' }}
      >
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--c-text-dim)' }}>
          {mode === 'focus' ? `Network: ${focusEntity}` : 'Fraud Rings'}
        </span>

        {mode === 'focus' && (
          <button
            onClick={handleBackToRings}
            className="text-[10px] px-2 py-0.5 rounded cursor-pointer"
            style={{ background: 'var(--c-surface2)', color: 'var(--c-accent)', border: '1px solid var(--c-border)' }}
          >
            ← All Rings
          </button>
        )}

        {/* Ring filter chips */}
        {mode === 'rings' && rings && rings.map(r => (
          <button
            key={r.ring_index}
            onClick={() => setSelectedRing(selectedRing === r.ring_index ? null : r.ring_index)}
            className="text-[10px] px-2 py-0.5 rounded cursor-pointer transition-colors"
            style={{
              background: selectedRing === r.ring_index ? RING_COLORS[r.ring_index % RING_COLORS.length] + '30' : 'var(--c-surface2)',
              color: RING_COLORS[r.ring_index % RING_COLORS.length],
              border: `1px solid ${selectedRing === r.ring_index ? RING_COLORS[r.ring_index % RING_COLORS.length] : 'var(--c-border)'}`,
            }}
          >
            Ring {r.ring_index + 1} · {r.entity_count} entities · ${(r.total_billed / 1000).toFixed(0)}K
          </button>
        ))}

        {/* Legend */}
        <div className="ml-auto flex items-center gap-3">
          {[
            { type: 'provider', label: 'Provider' },
            { type: 'member', label: 'Member' },
            { type: 'facility', label: 'Facility' },
          ].map(l => (
            <div key={l.type} className="flex items-center gap-1">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: ENTITY_COLORS[l.type].stroke }} />
              <span className="text-[10px]" style={{ color: 'var(--c-text-dim)' }}>{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="flex-1 relative overflow-hidden" style={{ background: '#080b10' }}>
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          viewBox={`0 0 ${dims.w} ${dims.h}`}
          style={{ display: 'block' }}
        >
          <defs>
            <marker id="net-arrow" markerWidth="6" markerHeight="5" refX="6" refY="2.5" orient="auto">
              <polygon points="0 0, 6 2.5, 0 5" fill="#475569" fillOpacity="0.6" />
            </marker>
            {/* Glow filter */}
            <filter id="node-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#ef4444" floodOpacity="0.5" />
            </filter>
          </defs>

          {/* Edges */}
          {visibleEdges.map((e, i) => {
            const src = nodeMap[e.source]
            const tgt = nodeMap[e.target]
            if (!src || !tgt) return null
            const isHighlighted = hoveredNode && (e.source === hoveredNode || e.target === hoveredNode)
            const edgeColor = EDGE_COLORS[e.relationship] || EDGE_COLORS.CONNECTED
            return (
              <line
                key={i}
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke={isHighlighted ? '#f8fafc' : edgeColor}
                strokeWidth={isHighlighted ? 2 : Math.min(1 + e.weight * 0.3, 3)}
                strokeOpacity={isHighlighted ? 0.8 : hoveredNode ? 0.15 : 0.5}
                markerEnd="url(#net-arrow)"
              />
            )
          })}

          {/* Nodes */}
          {visibleNodes.map((n) => {
            const colors = ENTITY_COLORS[n.entity_type] || ENTITY_COLORS.unknown
            const r = nodeRadius(n.anomaly_score)
            const isHigh = n.anomaly_score >= 0.7
            const isHovered = hoveredNode === n.id
            const ringColor = n.ring_index !== undefined ? RING_COLORS[n.ring_index % RING_COLORS.length] : null
            const dimmed = hoveredNode && !isHovered &&
              !visibleEdges.some(e => (e.source === hoveredNode && e.target === n.id) || (e.target === hoveredNode && e.source === n.id))

            return (
              <g
                key={n.id}
                onMouseEnter={() => setHoveredNode(n.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => handleFocus(n.id)}
                style={{ cursor: 'pointer' }}
                opacity={dimmed ? 0.2 : 1}
              >
                {/* Anomaly ring for high-anomaly nodes */}
                {isHigh && (
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={r + 4}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                    opacity="0.6"
                  />
                )}

                {/* Ring membership indicator */}
                {ringColor && (
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={r + 7}
                    fill="none"
                    stroke={ringColor}
                    strokeWidth="1"
                    opacity="0.4"
                  />
                )}

                {/* Main circle */}
                <circle
                  cx={n.x}
                  cy={n.y}
                  r={r}
                  fill={colors.fill}
                  stroke={isHovered ? '#ffffff' : colors.stroke}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  filter={isHigh ? 'url(#node-glow)' : undefined}
                />

                {/* Entity type icon */}
                <text
                  x={n.x}
                  y={n.y + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={colors.text}
                  fontSize="9"
                  fontWeight="700"
                >
                  {colors.icon}
                </text>

                {/* Label (only if hovered or large enough) */}
                {(isHovered || r > 16) && (
                  <text
                    x={n.x}
                    y={n.y + r + 12}
                    textAnchor="middle"
                    fill={isHovered ? '#f8fafc' : '#64748b'}
                    fontSize="9"
                    fontWeight="500"
                  >
                    {n.label}
                  </text>
                )}

                {/* Anomaly score badge */}
                {isHigh && (
                  <g>
                    <rect
                      x={n.x + r - 4}
                      y={n.y - r - 4}
                      width="26"
                      height="13"
                      rx="3"
                      fill="#7f1d1d"
                      stroke="#ef4444"
                      strokeWidth="0.5"
                    />
                    <text
                      x={n.x + r + 9}
                      y={n.y - r + 5}
                      textAnchor="middle"
                      fill="#fca5a5"
                      fontSize="8"
                      fontWeight="600"
                    >
                      {n.anomaly_score.toFixed(2)}
                    </text>
                  </g>
                )}
              </g>
            )
          })}
        </svg>

        {/* Hover tooltip */}
        {hovered && (
          <div
            className="absolute pointer-events-none px-3 py-2 rounded-lg text-xs"
            style={{
              left: Math.min(hovered.x + 20, dims.w - 200),
              top: Math.max(hovered.y - 60, 10),
              background: 'var(--c-surface)',
              border: '1px solid var(--c-border)',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              zIndex: 50,
            }}
          >
            <div className="font-semibold mb-1" style={{ color: '#e2e8f0' }}>{hovered.id}</div>
            <div className="space-y-0.5" style={{ color: 'var(--c-text-dim)' }}>
              <div>Type: <span style={{ color: ENTITY_COLORS[hovered.entity_type]?.text }}>{hovered.entity_type}</span></div>
              <div>Anomaly: <span style={{ color: hovered.anomaly_score >= 0.7 ? '#fca5a5' : 'var(--c-text)' }}>{hovered.anomaly_score.toFixed(2)}</span></div>
              {hovered.total_billed > 0 && <div>Billed: <span style={{ color: 'var(--c-text)' }}>${hovered.total_billed.toLocaleString()}</span></div>}
              {hovered.specialty && <div>Specialty: <span style={{ color: 'var(--c-text)' }}>{hovered.specialty}</span></div>}
            </div>
            <div className="mt-1 text-[9px]" style={{ color: 'var(--c-accent)' }}>Click to focus</div>
          </div>
        )}

        {/* Summary overlay */}
        <div
          className="absolute bottom-3 left-3 px-3 py-2 rounded-lg text-[10px]"
          style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)', opacity: 0.9 }}
        >
          <span style={{ color: 'var(--c-text-dim)' }}>
            {visibleNodes.length} nodes · {visibleEdges.length} edges
            {mode === 'rings' && rings && ` · ${rings.length} rings detected`}
          </span>
        </div>
      </div>
    </div>
  )
}
