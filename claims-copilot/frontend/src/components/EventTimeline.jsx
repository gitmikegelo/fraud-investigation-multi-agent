import { useRef, useEffect, useState } from 'react'

const EVENT_ICONS = {
  connected: '\u{1F50E}',
  status: '\u{1F4CD}',
  graph_start: '\u{1F680}',
  node_enter: '\u{1F9D1}',
  node_exit: '\u2705',
  phase_change: '\u{1F504}',
  dossier_rejected: '\u26D4',
  dossier_accepted: '\u2705',
  investigation_complete: '\u{1F3C1}',
  error: '\u274E',
  log: '\u{1F4DD}',
}

// Unified category pill palette — consistent muted tints (matches graph accents)
const NODE_BADGE_COLORS = {
  orchestrator:  { bg: 'rgba(168,85,247,0.10)', text: '#7c3aed' },
  investigation: { bg: 'rgba(34,197,94,0.10)',  text: '#15803d' },
  dossier:       { bg: 'rgba(245,158,11,0.10)', text: '#b45309' },
}

// Shared pill styling so every category chip is identical in shape
const PILL_BASE = {
  fontSize: 10,
  fontWeight: 600,
  padding: '2px 8px',
  borderRadius: 999,
  letterSpacing: '0.02em',
  lineHeight: 1.5,
  display: 'inline-block',
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

  // Auto-scroll to newest — smoothly, and respecting reduced-motion
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    el.scrollTo({ top: el.scrollHeight, behavior: reduce ? 'auto' : 'smooth' })
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
            className="px-4 py-3 text-sm font-semibold transition-colors relative cursor-pointer"
            style={{
              color: tab === t.key ? 'var(--c-accent)' : 'var(--c-text-dim)',
              background: 'transparent',
              border: 'none',
            }}
          >
            {t.label}
            <span
              className="ml-1.5 text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
              style={{
                background: tab === t.key ? 'var(--c-accent-soft)' : 'var(--c-surface2)',
                color: tab === t.key ? 'var(--c-accent)' : 'var(--c-text-dim)',
              }}
            >
              {t.count}
            </span>
            {tab === t.key && (
              <div
                className="absolute bottom-0 left-3 right-3 h-[2px] rounded-full"
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
            {isRunning ? 'Waiting for events\u2026' : 'Start an investigation to see events'}
          </div>
        ) : (
          <div className="space-y-1.5">
            {items.map((item, i) => (
              <div key={i} className="console-row-in">
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
  const icon = EVENT_ICONS[event.type] || '\u2022'
  const badge = event.node ? NODE_BADGE_COLORS[event.node] : null
  const [expanded, setExpanded] = useState(false)
  const [showTooltip, setShowTooltip] = useState(false)
  const isLong = event.message && event.message.length > TRUNCATE_LEN
  const displayMsg = isLong && !expanded ? event.message.slice(0, TRUNCATE_LEN) + '\u2026' : event.message

  // Distinctive row highlight for rejection / acceptance
  const isRejection = event.type === 'dossier_rejected'
  const isAcceptance = event.type === 'dossier_accepted'
  const rowStyle = isRejection
    ? { background: REJECTION_STYLE.bg, border: REJECTION_STYLE.border }
    : isAcceptance
    ? { background: ACCEPTANCE_STYLE.bg, border: ACCEPTANCE_STYLE.border }
    : {}

  // For rejections, show evidence gaps inline (expanded by default)
  const hasEvidenceGaps = isRejection && event.evidence_gaps && typeof event.evidence_gaps === 'string'
  const [gapsExpanded, setGapsExpanded] = useState(true)

  // Check if this event has additional details to show in tooltip (non-rejection only)
  const hasDetails = !hasEvidenceGaps && (
                     (event.findings_preview && typeof event.findings_preview === 'string') || 
                     (event.details && typeof event.details === 'string'))

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
            <span style={{ ...PILL_BASE, background: badge.bg, color: badge.text }}>
              {event.node}
            </span>
          )}
          <span className="text-sm" style={{ color: 'var(--c-text)', whiteSpace: expanded ? 'pre-wrap' : undefined }}>
            {displayMsg}
          </span>
          {hasDetails && (
            <span
              style={{ ...PILL_BASE, background: 'var(--c-accent-soft)', color: 'var(--c-accent)', cursor: 'help' }}
              title="Hover for details"
            >
              details
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
            className="mt-1"
            style={{ ...PILL_BASE, background: 'var(--c-accent-soft)', color: 'var(--c-accent)', textTransform: 'uppercase' }}
          >
            {event.phase}
          </span>
        )}
        {/* Inline evidence gaps for rejection events */}
        {hasEvidenceGaps && (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setGapsExpanded(prev => !prev)}
              className="text-[10px] px-2 py-1 rounded cursor-pointer hover:opacity-80 transition-opacity mb-1"
              style={{
                background: 'var(--c-red-bg, rgba(239,68,68,0.1))',
                color: 'var(--c-red, #dc2626)',
                border: '1px solid var(--c-red-border, rgba(239,68,68,0.3))',
                fontWeight: 600,
              }}
            >
              {gapsExpanded ? '\u25BC Case Writer Note' : '\u25B6 Case Writer Note'}
            </button>
            {gapsExpanded && (
              <FindingsCard heading="Case Writer Note" text={event.evidence_gaps} tone="red" />
            )}
          </div>
        )}
      </div>
      <span className="text-[10px] font-mono flex-shrink-0 mt-1" style={{ color: 'var(--c-text-dim)' }}>
        {formatTs(event.timestamp)}
      </span>

      {/* Details popover — clean summary card (no monospace dump) */}
      {showTooltip && hasDetails && (
        <div
          className="absolute z-50"
          style={{
            top: '100%',
            left: 0,
            marginTop: 6,
            maxWidth: 400,
            minWidth: 260,
            boxShadow: 'var(--c-shadow-md)',
            borderRadius: 12,
          }}
        >
          {event.findings_preview && typeof event.findings_preview === 'string' ? (
            <FindingsCard heading="Findings" text={event.findings_preview} tone="green" />
          ) : (
            event.details && typeof event.details === 'string' && (
              <FindingsCard heading="Details" text={event.details} tone="neutral" />
            )
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Tidy summary card — replaces the old monospace terminal block.
 * Renders a small heading then the text as a clean, comfortably-spaced list.
 */
const FINDINGS_TONE = {
  green:   { dot: 'var(--c-green)',  heading: 'var(--c-green)' },
  red:     { dot: 'var(--c-red)',    heading: 'var(--c-red)' },
  neutral: { dot: 'var(--c-text-muted)', heading: 'var(--c-text-dim)' },
}

function splitFindings(text) {
  // Break a blob into discrete points: explicit list markers first, else lines, else sentences.
  const raw = String(text).trim()
  const byMarker = raw
    .split(/\n+|(?:^|\s)[•\-*]\s+|(?:^|\s)\d+[.)]\s+/g)
    .map(s => s.trim())
    .filter(Boolean)
  if (byMarker.length > 1) return byMarker
  return [raw]
}

function FindingsCard({ heading, text, tone = 'neutral' }) {
  const t = FINDINGS_TONE[tone] || FINDINGS_TONE.neutral
  const items = splitFindings(text)

  return (
    <div
      style={{
        background: 'var(--c-surface)',
        border: '1px solid var(--c-border)',
        borderRadius: 12,
        padding: '12px 14px',
        boxShadow: 'var(--c-shadow-sm)',
        maxHeight: 320,
        overflowY: 'auto',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <div
        style={{
          fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
          color: t.heading, marginBottom: 8,
        }}
      >
        {heading}
      </div>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 7 }}>
        {items.map((item, i) => (
          <li key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
            <span
              style={{
                width: 5, height: 5, borderRadius: '50%', background: t.dot,
                flexShrink: 0, marginTop: 7,
              }}
            />
            <span style={{ fontSize: 12.5, lineHeight: 1.6, color: 'var(--c-text)' }}>
              {item}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function LogRow({ log }) {
  const isToolLog = log.agent === 'tool'
  const isDossierLog = log.agent === 'dossier'
  const [expanded, setExpanded] = useState(false)
  const isLong = log.message && log.message.length > TRUNCATE_LEN
  const displayMsg = isLong && !expanded ? log.message.slice(0, TRUNCATE_LEN) + '\u2026' : log.message

  // Highlight rejection / acceptance log rows from dossier agent
  const isRejectionLog = isDossierLog && log.message && log.message.includes('REJECTED')
  const isAcceptanceLog = isDossierLog && log.message && log.message.includes('ACCEPTED')
  const rowStyle = isRejectionLog
    ? { background: REJECTION_STYLE.bg, border: REJECTION_STYLE.border }
    : isAcceptanceLog
    ? { background: ACCEPTANCE_STYLE.bg, border: ACCEPTANCE_STYLE.border }
    : {}

  // Unified agent pill (same shape as event category pills)
  const badgeStyle = isDossierLog
    ? { ...PILL_BASE, background: 'rgba(245,158,11,0.10)', color: '#b45309' }
    : isToolLog
    ? { ...PILL_BASE, background: 'var(--c-accent-soft)', color: 'var(--c-accent)' }
    : { ...PILL_BASE, background: 'var(--c-surface2)', color: 'var(--c-text-dim)' }

  return (
    <div
      className="flex items-start gap-2.5 py-1.5 px-2 rounded-md text-xs"
      onMouseEnter={e => { if (!rowStyle.background) e.currentTarget.style.background = 'var(--c-surface2)' }}
      onMouseLeave={e => { if (!rowStyle.background) e.currentTarget.style.background = '' }}
      style={rowStyle}
    >
      <span className="flex-shrink-0 mt-0.5" style={badgeStyle}>
        {log.agent}
      </span>
      <div className="flex-1 min-w-0 flex items-start gap-1.5 flex-wrap">
        <span
          className="break-words"
          style={{ color: 'var(--c-text)', lineHeight: 1.6, whiteSpace: expanded ? 'pre-wrap' : undefined }}
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