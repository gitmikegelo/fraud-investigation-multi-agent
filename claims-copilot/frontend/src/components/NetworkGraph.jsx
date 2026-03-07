import { useRef, useEffect, useState, useCallback } from 'react'

// ── Layout constants ─────────────────────────────────────────────────
const ENTITY_COLORS = {
  provider: { fill: '#eff6ff', stroke: '#3b82f6', text: '#1d4ed8', icon: 'P' },
  member:   { fill: '#f0fdf4', stroke: '#16a34a', text: '#15803d', icon: 'M' },
  facility: { fill: '#fffbeb', stroke: '#d97706', text: '#a16207', icon: 'F' },
  unknown:  { fill: '#f8fafc', stroke: '#94a3b8', text: '#475569', icon: '?' },
}

const EDGE_COLORS = {
  BILLED_FOR:  '#93c5fd60',
  REFERRED_TO: '#f59e0bcc',
  OPERATES_AT: '#86efac60',
  CONNECTED:   '#94a3b840',
}

const RING_COLORS = [
  '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899',
]

// ── Ring-clustered layout ────────────────────────────────────────────
// Each ring is laid out as a separate cluster: providers at center,
// members and facilities orbit around them.
function clusterLayout(nodes, edges, width, height) {
  // Separate nodes by ring_index
  const ringGroups = {}
  const unassigned = []
  nodes.forEach(n => {
    if (n.ring_index !== undefined && n.ring_index !== null) {
      if (!ringGroups[n.ring_index]) ringGroups[n.ring_index] = []
      ringGroups[n.ring_index].push(n)
    } else {
      unassigned.push(n)
    }
  })

  const ringKeys = Object.keys(ringGroups).sort((a, b) => a - b)
  const ringCount = ringKeys.length || 1
  const pad = 60

  // Build edge lookup for within-cluster connection detection
  const edgeMap = new Map()
  edges.forEach(e => {
    if (!edgeMap.has(e.source)) edgeMap.set(e.source, [])
    if (!edgeMap.has(e.target)) edgeMap.set(e.target, [])
    edgeMap.get(e.source).push(e.target)
    edgeMap.get(e.target).push(e.source)
  })

  // Compute cluster centers — place rings in a row or grid
  const usableW = width - pad * 2
  const usableH = height - pad * 2

  let cols, rows
  if (ringCount <= 3) {
    cols = ringCount
    rows = 1
  } else {
    cols = Math.ceil(Math.sqrt(ringCount))
    rows = Math.ceil(ringCount / cols)
  }

  const cellW = usableW / cols
  const cellH = usableH / rows

  ringKeys.forEach((key, idx) => {
    const col = idx % cols
    const row = Math.floor(idx / cols)
    const cx = pad + col * cellW + cellW / 2
    const cy = pad + row * cellH + cellH / 2
    const cluster = ringGroups[key]

    // Split into providers and others
    const providers = cluster.filter(n => n.entity_type === 'provider')
    const others = cluster.filter(n => n.entity_type !== 'provider')

    // Radius for orbiting nodes
    const clusterRadius = Math.min(cellW, cellH) * 0.38

    // Place providers in inner ring (or at center if single)
    if (providers.length === 1) {
      providers[0].x = cx
      providers[0].y = cy
    } else {
      const pRadius = Math.min(clusterRadius * 0.35, 60)
      providers.forEach((p, i) => {
        const angle = (2 * Math.PI * i) / providers.length - Math.PI / 2
        p.x = cx + pRadius * Math.cos(angle)
        p.y = cy + pRadius * Math.sin(angle)
      })
    }

    // Place other nodes in outer orbit, grouped by which provider they connect to
    if (others.length > 0) {
      // Assign each non-provider to its closest provider
      const providerBuckets = new Map()
      providers.forEach(p => providerBuckets.set(p.id, []))

      others.forEach(n => {
        const neighbors = edgeMap.get(n.id) || []
        const connectedProvider = neighbors.find(nid => providers.some(p => p.id === nid))
        if (connectedProvider && providerBuckets.has(connectedProvider)) {
          providerBuckets.get(connectedProvider).push(n)
        } else {
          // Assign to provider with fewest assignments
          let minKey = providers[0]?.id
          let minCount = Infinity
          for (const [pid, arr] of providerBuckets) {
            if (arr.length < minCount) { minCount = arr.length; minKey = pid }
          }
          if (minKey) providerBuckets.get(minKey).push(n)
        }
      })

      // Lay out each bucket as a fan around its provider
      const providerAngles = new Map()
      providers.forEach((p, i) => {
        providerAngles.set(p.id, (2 * Math.PI * i) / Math.max(providers.length, 1) - Math.PI / 2)
      })

      for (const [pid, bucket] of providerBuckets) {
        if (bucket.length === 0) continue
        const provider = providers.find(p => p.id === pid)
        if (!provider) continue

        // Fan outward from provider's position
        const baseAngle = Math.atan2(provider.y - cy, provider.x - cx)
        const fanSpread = Math.min(Math.PI * 0.8, bucket.length * 0.25)
        const startAngle = baseAngle - fanSpread / 2

        bucket.forEach((n, i) => {
          const t = bucket.length === 1 ? 0.5 : i / (bucket.length - 1)
          const angle = startAngle + fanSpread * t
          const dist = clusterRadius * (0.55 + Math.random() * 0.35)
          n.x = cx + dist * Math.cos(angle)
          n.y = cy + dist * Math.sin(angle)
        })
      }
    }
  })

  // Place unassigned nodes along the bottom
  unassigned.forEach((n, i) => {
    n.x = pad + (i + 0.5) * ((usableW) / Math.max(unassigned.length, 1))
    n.y = height - pad
  })

  // Light force pass to resolve overlaps (few iterations, repulsion only)
  for (let iter = 0; iter < 40; iter++) {
    const cooling = 1 - iter / 40
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x
        const dy = nodes[i].y - nodes[j].y
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.1
        const minDist = 28
        if (dist < minDist) {
          const push = (minDist - dist) * 0.3 * cooling
          const px = (dx / dist) * push
          const py = (dy / dist) * push
          nodes[i].x += px
          nodes[i].y += py
          nodes[j].x -= px
          nodes[j].y -= py
        }
      }
    }
    // Clamp to bounds
    nodes.forEach(n => {
      n.x = Math.max(20, Math.min(width - 20, n.x))
      n.y = Math.max(20, Math.min(height - 20, n.y))
    })
  }

  return nodes
}

// ── Anomaly → size mapping ───────────────────────────────────────────
function nodeRadius(anomaly, entityType) {
  if (entityType === 'provider') return 14 + anomaly * 16
  if (entityType === 'facility') return 8 + anomaly * 8
  return 6 + anomaly * 8 // members are smaller
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
  const dimsRef = useRef({ w: 800, h: 500 })

  // Keep ref in sync with state for use in callbacks
  useEffect(() => { dimsRef.current = dims }, [dims])

  // Resize observer — re-run when `data` changes so it can
  // attach once the SVG is actually in the DOM.
  useEffect(() => {
    const container = svgRef.current?.parentElement
    if (!container) return
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        const w = entry.contentRect.width
        const h = entry.contentRect.height
        if (w > 0 && h > 0) setDims({ w, h })
      }
    })
    ro.observe(container)
    return () => ro.disconnect()
  }, [data])

  // Fetch data — uses dimsRef so the callback identity is stable
  const fetchNetwork = useCallback(async (entity = null) => {
    setLoading(true)
    setError(null)
    try {
      const url = entity
        ? `/api/fraud-network?focus_entity=${encodeURIComponent(entity)}&depth=2`
        : '/api/fraud-network?min_anomaly=0.5&min_ring_size=3'
      console.log('[NetworkGraph] fetching', url)
      const res = await fetch(url)
      const json = await res.json()
      console.log('[NetworkGraph] response:', json.mode, 'nodes:', json.nodes?.length, 'edges:', json.edges?.length, 'rings:', json.rings?.length)
      if (json.error) { setError(json.error); return }
      if (!json.nodes?.length) { setError('No fraud network data returned'); return }

      // Use current dims from ref (avoids stale closure)
      const { w, h } = dimsRef.current
      const laid = clusterLayout([...json.nodes], json.edges, w || 800, h || 500)
      setData({ ...json, nodes: laid })
      setSelectedRing(null)
    } catch (e) {
      console.error('[NetworkGraph] fetch error:', e)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])  // stable — no deps since we use dimsRef

  // Auto-fetch when investigation completes
  useEffect(() => {
    if (isComplete) fetchNetwork()
  }, [isComplete, fetchNetwork])

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
        <div className="text-center space-y-3">
          <p className="text-sm" style={{ color: 'var(--c-red)' }}>Error: {error}</p>
          <button
            onClick={() => fetchNetwork()}
            className="text-xs px-3 py-1 rounded cursor-pointer"
            style={{ background: 'var(--c-surface2)', color: 'var(--c-accent)', border: '1px solid var(--c-border)' }}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!data) {
    // isComplete is true but data hasn't loaded yet — trigger fetch
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-sm" style={{ color: 'var(--c-text-dim)' }}>No network data loaded.</p>
          <button
            onClick={() => fetchNetwork()}
            className="text-xs px-3 py-1 rounded cursor-pointer"
            style={{ background: 'var(--c-surface2)', color: 'var(--c-accent)', border: '1px solid var(--c-border)' }}
          >
            Load Fraud Network
          </button>
        </div>
      </div>
    )
  }

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

        {/* Refresh button */}
        <button
          onClick={() => focusEntity ? fetchNetwork(focusEntity) : fetchNetwork()}
          className="text-[10px] px-2 py-0.5 rounded cursor-pointer"
          style={{ background: 'var(--c-surface2)', color: 'var(--c-text-dim)', border: '1px solid var(--c-border)' }}
          title="Reload network data"
        >
          ↻
        </button>

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
          <div className="w-px h-3" style={{ background: 'var(--c-border)' }} />
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5" style={{ background: '#f59e0b' }} />
            <span className="text-[10px]" style={{ color: 'var(--c-text-dim)' }}>Referral</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-0" style={{ borderTop: '1px dashed #3b82f680' }} />
            <span className="text-[10px]" style={{ color: 'var(--c-text-dim)' }}>Billed</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="flex-1 relative overflow-hidden" style={{ background: 'var(--c-bg)' }}>
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          viewBox={`0 0 ${dims.w} ${dims.h}`}
          style={{ display: 'block' }}
        >
          <defs>
            <marker id="net-arrow" markerWidth="6" markerHeight="5" refX="6" refY="2.5" orient="auto">
              <polygon points="0 0, 6 2.5, 0 5" fill="#475569" fillOpacity="0.5" />
            </marker>
            <marker id="net-arrow-referral" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#f59e0b" fillOpacity="0.8" />
            </marker>
            {/* Glow filter */}
            <filter id="node-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#ef4444" floodOpacity="0.5" />
            </filter>
          </defs>

          {/* Edges — render BILLED_FOR first (back), then REFERRED_TO on top */}
          {[...visibleEdges]
            .sort((a, b) => (a.relationship === 'REFERRED_TO' ? 1 : 0) - (b.relationship === 'REFERRED_TO' ? 1 : 0))
            .map((e, i) => {
            const src = nodeMap[e.source]
            const tgt = nodeMap[e.target]
            if (!src || !tgt) return null
            const isHighlighted = hoveredNode && (e.source === hoveredNode || e.target === hoveredNode)
            const isReferral = e.relationship === 'REFERRED_TO'
            const edgeColor = EDGE_COLORS[e.relationship] || EDGE_COLORS.CONNECTED
            return (
              <line
                key={i}
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke={isHighlighted ? '#f8fafc' : edgeColor}
                strokeWidth={isHighlighted ? 2.5 : isReferral ? 2.5 : Math.min(0.8 + e.weight * 0.2, 2)}
                strokeOpacity={isHighlighted ? 0.9 : hoveredNode ? 0.1 : isReferral ? 0.9 : 0.35}
                strokeDasharray={isReferral ? undefined : '3 2'}
                markerEnd={isReferral ? 'url(#net-arrow-referral)' : 'url(#net-arrow)'}
              />
            )
          })}

          {/* Nodes */}
          {visibleNodes.map((n) => {
            const colors = ENTITY_COLORS[n.entity_type] || ENTITY_COLORS.unknown
            const r = nodeRadius(n.anomaly_score, n.entity_type)
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
                  stroke={isHovered ? '#4f46e5' : colors.stroke}
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

                {/* Label — always show for providers, hover for others */}
                {(isHovered || n.entity_type === 'provider' || n.entity_type === 'facility' || r > 18) && (
                  <text
                    x={n.x}
                    y={n.y + r + 12}
                    textAnchor="middle"
                    fill={isHovered ? '#0f172a' : n.entity_type === 'provider' ? '#1d4ed8' : '#64748b'}
                    fontSize={n.entity_type === 'provider' ? '10' : '9'}
                    fontWeight={n.entity_type === 'provider' ? '600' : '500'}
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
                      fill="#fef2f2"
                      stroke="#ef4444"
                      strokeWidth="0.8"
                    />
                    <text
                      x={n.x + r + 9}
                      y={n.y - r + 5}
                      textAnchor="middle"
                      fill="#dc2626"
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
              boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
              zIndex: 50,
            }}
          >
            <div className="font-semibold mb-1" style={{ color: 'var(--c-text)' }}>{hovered.id}</div>
            <div className="space-y-0.5" style={{ color: 'var(--c-text-dim)' }}>
              <div>Type: <span style={{ color: ENTITY_COLORS[hovered.entity_type]?.text }}>{hovered.entity_type}</span></div>
              <div>Anomaly: <span style={{ color: hovered.anomaly_score >= 0.7 ? 'var(--c-red)' : 'var(--c-text)' }}>{hovered.anomaly_score.toFixed(2)}</span></div>
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
