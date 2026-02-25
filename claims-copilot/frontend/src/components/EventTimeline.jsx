import { useRef, useEffect, useState } from 'react'

const EVENT_ICONS = {
  connected: '🔌',
  status: '📡',
  graph_start: '🚀',
  node_enter: '➡️',
  node_exit: '✅',
  phase_change: '🔄',
  dossier_rejected: '⛔',
  dossier_accepted: '✅',
  investigation_complete: '🏁',
  error: '❌',
  log: '📝',
}

const NODE_BADGE_COLORS = {
  orchestrator: { bg: '#172554', text: '#93c5fd', border: '#3b82f6' },
  investigation: { bg: '#14532d', text: '#86efac', border: '#22c55e' },
  dossier: { bg: '#451a03', text: '#fcd34d', border: '#f59e0b' },
}

// Distinctive row styles for rejection / acceptance events
const REJECTION_STYLE = { bg: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)' }
const ACCEPTANCE_STYLE = { bg: 'rgba(34, 197, 94, 0.08)', border: '1px solid rgba(34, 197, 94, 0.25)' }

function formatTs(ts) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

export default function EventTimeline({ events, logs, isRunning }) {
  const [tab, setTab] = useState('events') // events | logs
  const scrollRef = useRef(null)

  const items = tab === 'events' ? events : logs

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [items])

  return (
    <div className="flex flex-col h-full">
      {/* Tab header */}
      <div
        className="flex items-center gap-0 px-4 py-0 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--c-border)' }}
      >
        {[
          { key: 'events', label: 'Events', count: events.length },
          { key: 'logs', label: 'Logs', count: logs.length },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className="px-4 py-2.5 text-sm font-medium transition-colors relative cursor-pointer"
            style={{
              color: tab === t.key ? 'var(--c-accent)' : 'var(--c-text-dim)',
              background: 'transparent',
              border: 'none',
            }}
          >
            {t.label}
            <span
              className="ml-1.5 text-xs px-1.5 py-0.5 rounded-full"
              style={{ background: 'var(--c-surface2)', color: 'var(--c-text-dim)' }}
            >
              {t.count}
            </span>
            {tab === t.key && (
              <div
                className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full"
                style={{ background: 'var(--c-accent)' }}
              />
            )}
          </button>
        ))}

        {/* Running indicator */}
        {isRunning && (
          <div className="ml-auto flex items-center gap-1.5 text-xs" style={{ color: 'var(--c-green)' }}>
            <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--c-green)' }} />
            Live
          </div>
        )}
      </div>

      {/* Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-2">
        {items.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--c-text-dim)' }}>
            {isRunning ? 'Waiting for events…' : 'Start an investigation to see events'}
          </div>
        ) : (
          <div className="space-y-1">
            {items.map((item, i) => (
              <div key={i} className="log-entry">
                {tab === 'events' ? (
                  <EventRow event={item} />
                ) : (
                  <LogRow log={item} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const TRUNCATE_LEN = 180

function EventRow({ event }) {
  const icon = EVENT_ICONS[event.type] || '•'
  const badge = event.node ? NODE_BADGE_COLORS[event.node] : null
  const [expanded, setExpanded] = useState(false)
  const isLong = event.message && event.message.length > TRUNCATE_LEN
  const displayMsg = isLong && !expanded ? event.message.slice(0, TRUNCATE_LEN) + '…' : event.message

  // Distinctive row highlight for rejection / acceptance
  const isRejection = event.type === 'dossier_rejected'
  const isAcceptance = event.type === 'dossier_accepted'
  const rowStyle = isRejection
    ? { background: REJECTION_STYLE.bg, border: REJECTION_STYLE.border }
    : isAcceptance
    ? { background: ACCEPTANCE_STYLE.bg, border: ACCEPTANCE_STYLE.border }
    : {}

  return (
    <div
      className="flex items-start gap-2.5 py-1.5 px-2 rounded-md hover:bg-white/[0.02] transition-colors"
      style={rowStyle}
    >
      <span className="text-sm flex-shrink-0 mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          {badge && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: badge.bg, color: badge.text, border: `1px solid ${badge.border}` }}
            >
              {event.node}
            </span>
          )}
          <span className="text-sm" style={{ color: 'var(--c-text)', whiteSpace: expanded ? 'pre-wrap' : undefined }}>
            {displayMsg}
          </span>
          {isLong && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setExpanded(prev => !prev)
              }}
              className="text-[10px] px-2 py-1 rounded cursor-pointer shrink-0 hover:opacity-80 transition-opacity"
              style={{ 
                background: 'var(--c-surface2)', 
                color: 'var(--c-accent)', 
                border: '1px solid var(--c-border)',
                pointerEvents: 'auto',
                userSelect: 'none'
              }}
            >
              {expanded ? 'collapse' : 'expand'}
            </button>
          )}
        </div>
        {/* Phase badge for phase_change */}
        {event.phase && (
          <span
            className="inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wide"
            style={{ background: '#1e293b', color: '#93c5fd' }}
          >
            {event.phase}
          </span>
        )}
      </div>
      <span className="text-[10px] font-mono flex-shrink-0 mt-1" style={{ color: 'var(--c-text-dim)' }}>
        {formatTs(event.timestamp)}
      </span>
    </div>
  )
}

function LogRow({ log }) {
  const isToolLog = log.agent === 'tool'
  const isDossierLog = log.agent === 'dossier'
  const [expanded, setExpanded] = useState(false)
  const isLong = log.message && log.message.length > TRUNCATE_LEN
  const displayMsg = isLong && !expanded ? log.message.slice(0, TRUNCATE_LEN) + '…' : log.message

  // Highlight rejection / acceptance log rows from dossier agent
  const isRejection = isDossierLog && log.message && log.message.includes('REJECTED')
  const isAcceptance = isDossierLog && log.message && log.message.includes('ACCEPTED')
  const rowStyle = isRejection
    ? { background: REJECTION_STYLE.bg, border: REJECTION_STYLE.border }
    : isAcceptance
    ? { background: ACCEPTANCE_STYLE.bg, border: ACCEPTANCE_STYLE.border }
    : {}

  // Badge colors for dossier agent
  const badgeStyle = isDossierLog
    ? { background: '#451a03', color: '#fcd34d', border: '1px solid #f59e0b' }
    : {
        background: isToolLog ? '#1e1b4b' : '#1a2030',
        color: isToolLog ? '#a5b4fc' : '#6b7a94',
        border: `1px solid ${isToolLog ? '#4338ca' : '#2d3748'}`,
      }

  return (
    <div
      className="flex items-start gap-2.5 py-1 px-2 rounded-md hover:bg-white/[0.02] font-mono text-xs"
      style={rowStyle}
    >
      <span
        className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded mt-0.5"
        style={badgeStyle}
      >
        {log.agent}
      </span>
      <div className="flex-1 min-w-0 flex items-start gap-1.5 flex-wrap">
        <span
          className="break-words"
          style={{ color: 'var(--c-text)', lineHeight: '1.5', whiteSpace: expanded ? 'pre-wrap' : undefined }}
        >
          {displayMsg}
        </span>
        {isLong && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              setExpanded(prev => !prev)
            }}
            className="text-[10px] px-2 py-1 rounded cursor-pointer shrink-0 hover:opacity-80 transition-opacity"
            style={{ 
              background: 'var(--c-surface2)', 
              color: 'var(--c-accent)', 
              border: '1px solid var(--c-border)',
              pointerEvents: 'auto',
              userSelect: 'none'
            }}
          >
            {expanded ? 'collapse' : 'expand'}
          </button>
        )}
      </div>
      <span className="text-[10px] flex-shrink-0 mt-0.5" style={{ color: 'var(--c-text-dim)' }}>
        {formatTs(log.timestamp)}
      </span>
    </div>
  )
}
