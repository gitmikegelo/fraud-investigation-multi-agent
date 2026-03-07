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
  orchestrator: { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
  investigation: { bg: 'var(--c-green-bg)', text: 'var(--c-green)', border: 'var(--c-green-border)' },
  dossier: { bg: 'var(--c-amber-bg)', text: 'var(--c-amber)', border: 'var(--c-amber-border)' },
}

// Distinctive row styles for rejection / acceptance events
const REJECTION_STYLE = { bg: 'var(--c-red-bg)', border: '1px solid var(--c-red-border)' }
const ACCEPTANCE_STYLE = { bg: 'var(--c-green-bg)', border: '1px solid var(--c-green-border)' }

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
  const [showTooltip, setShowTooltip] = useState(false)
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

  // Check if this event has additional details to show in tooltip
  const hasDetails = (event.evidence_gaps && typeof event.evidence_gaps === 'string') || 
                     (event.findings_preview && typeof event.findings_preview === 'string') || 
                     (event.details && typeof event.details === 'string')

  return (
    <div
      className="flex items-start gap-2.5 py-1.5 px-2 rounded-md transition-colors"
      style={{ ...rowStyle, position: 'relative' }}
      onMouseEnter={e => {
        if (!rowStyle.background) e.currentTarget.style.background = 'var(--c-surface2)'
        if (hasDetails) setShowTooltip(true)
      }}
      onMouseLeave={e => {
        if (!rowStyle.background) e.currentTarget.style.background = ''
        setShowTooltip(false)
      }}
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
          {hasDetails && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{
                background: 'var(--c-accent-light)',
                color: 'var(--c-accent)',
                border: '1px solid #c7d2fe',
                cursor: 'help',
              }}
              title="Hover for details"
            >
              ℹ️
            </span>
          )}
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
            style={{ background: 'var(--c-accent-light)', color: 'var(--c-accent)', border: '1px solid #c7d2fe' }}
          >
            {event.phase}
          </span>
        )}
      </div>
      <span className="text-[10px] font-mono flex-shrink-0 mt-1" style={{ color: 'var(--c-text-dim)' }}>
        {formatTs(event.timestamp)}
      </span>

      {/* Tooltip for additional details */}
      {showTooltip && hasDetails && (
        <div
          className="absolute z-50 px-3 py-2 text-xs rounded-md shadow-lg border"
          style={{
            background: 'var(--c-surface)',
            borderColor: 'var(--c-border)',
            color: 'var(--c-text)',
            top: '100%',
            left: '0',
            marginTop: '4px',
            maxWidth: '400px',
            minWidth: '250px',
            whiteSpace: 'pre-wrap',
            lineHeight: '1.4',
          }}
        >
          {event.evidence_gaps && typeof event.evidence_gaps === 'string' && (
            <div>
              <div className="font-semibold mb-1" style={{ color: 'var(--c-red)' }}>
                Evidence Gaps:
              </div>
              <div>{event.evidence_gaps}</div>
            </div>
          )}
          {event.findings_preview && !event.evidence_gaps && typeof event.findings_preview === 'string' && (
            <div>
              <div className="font-semibold mb-1" style={{ color: 'var(--c-green)' }}>
                Findings:
              </div>
              <div>{event.findings_preview}</div>
            </div>
          )}
          {event.details && !event.evidence_gaps && !event.findings_preview && typeof event.details === 'string' && (
            <div>{event.details}</div>
          )}
        </div>
      )}
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
  const isRejectionLog = isDossierLog && log.message && log.message.includes('REJECTED')
  const isAcceptanceLog = isDossierLog && log.message && log.message.includes('ACCEPTED')
  const isRejection = isRejectionLog
  const isAcceptance = isAcceptanceLog
  const rowStyle = isRejectionLog
    ? { background: REJECTION_STYLE.bg, border: REJECTION_STYLE.border }
    : isAcceptanceLog
    ? { background: ACCEPTANCE_STYLE.bg, border: ACCEPTANCE_STYLE.border }
    : {}

  // Badge colors for dossier agent
  const badgeStyle = isDossierLog
    ? { background: 'var(--c-amber-bg)', color: 'var(--c-amber)', border: '1px solid var(--c-amber-border)' }
    : {
        background: isToolLog ? 'var(--c-accent-light)' : 'var(--c-surface2)',
        color: isToolLog ? 'var(--c-accent)' : 'var(--c-text-dim)',
        border: `1px solid ${isToolLog ? '#c7d2fe' : 'var(--c-border)'}`,
      }

  return (
    <div
      className="flex items-start gap-2.5 py-1 px-2 rounded-md font-mono text-xs"
      onMouseEnter={e => { if (!rowStyle.background) e.currentTarget.style.background = 'var(--c-surface2)' }}
      onMouseLeave={e => { if (!rowStyle.background) e.currentTarget.style.background = '' }}
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
