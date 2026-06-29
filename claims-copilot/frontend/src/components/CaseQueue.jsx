import { useState, useEffect } from 'react'

const PRIORITY_COLORS = {
  HIGH:   { dot: '#ef4444', bg: 'rgba(239,68,68,0.08)', text: '#fca5a5' },
  MEDIUM: { dot: '#f59e0b', bg: 'rgba(245,158,11,0.08)', text: '#fcd34d' },
  LOW:    { dot: '#6b7280', bg: 'rgba(107,114,128,0.08)', text: '#9ca3af' },
}

const TYPE_LABELS = {
  wellness:            'Wellness',
  accident:            'Accident',
  hospital_indemnity:  'Hospital Ind.',
  critical_illness:    'Critical Illness',
  trip_cancellation:   'Trip Cancel',
  trip_interruption:   'Trip Interrupt',
  medical_emergency:   'Medical',
  baggage_loss:        'Baggage',
  travel_delay:        'Travel Delay',
}

const TYPE_COLORS = {
  wellness:           { bg: 'rgba(34,197,94,0.12)',  text: '#4ade80' },
  accident:           { bg: 'rgba(59,130,246,0.12)', text: '#60a5fa' },
  hospital_indemnity: { bg: 'rgba(168,85,247,0.12)', text: '#c084fc' },
  critical_illness:   { bg: 'rgba(239,68,68,0.12)',  text: '#fca5a5' },
  trip_cancellation:  { bg: 'rgba(59,130,246,0.12)', text: '#60a5fa' },
  trip_interruption:  { bg: 'rgba(59,130,246,0.12)', text: '#93c5fd' },
  medical_emergency:  { bg: 'rgba(239,68,68,0.12)',  text: '#fca5a5' },
  baggage_loss:       { bg: 'rgba(245,158,11,0.12)', text: '#fcd34d' },
  travel_delay:       { bg: 'rgba(107,114,128,0.12)',text: '#9ca3af' },
}

export default function CaseQueue({ onSelectCase }) {
  const [cases, setCases] = useState([])
  const [counts, setCounts] = useState({ total: 0, by_date: {}, by_type: {}, by_priority: {} })
  const [loading, setLoading] = useState(true)
  const [dateTab, setDateTab] = useState('all')
  const [typeTab, setTypeTab] = useState(null)
  const [filterPriority, setFilterPriority] = useState(null)

  const fetchCases = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('date_range', dateTab)
      if (typeTab) params.set('claim_type', typeTab)
      if (filterPriority) params.set('priority', filterPriority)
      const res = await fetch(`http://${window.location.hostname}:8000/api/claims?${params}`)
      const data = await res.json()
      setCases(data.claims || [])
      setCounts(data.counts || { total: 0, by_date: {}, by_type: {}, by_priority: {} })
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCases() }, [dateTab, typeTab, filterPriority])

  const byDate = counts.by_date || {}
  const dateTabs = [
    { id: 'today',     label: `Today (${byDate.today || 0})` },
    { id: 'this_week', label: `This Week (${byDate.this_week || 0})` },
    { id: 'all',       label: `All (${byDate.all || 0})` },
  ]

  const typeTabs = [
    { id: null,                  label: 'All Types' },
    { id: 'wellness',           label: 'Wellness' },
    { id: 'accident',           label: 'Accident' },
    { id: 'hospital_indemnity', label: 'Hospital Ind.' },
    { id: 'critical_illness',   label: 'Critical Illness' },
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header bar */}
      <div style={{
        padding: '16px 24px 0', background: 'var(--c-surface)',
        borderBottom: '1px solid var(--c-border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--c-text)', letterSpacing: '-0.01em' }}>
            Claims Queue
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {/* Priority filter chips */}
            {['HIGH', 'MEDIUM', 'LOW'].map(p => {
              const active = filterPriority === p
              const colors = PRIORITY_COLORS[p]
              return (
                <button key={p} onClick={() => setFilterPriority(active ? null : p)} style={{
                  fontSize: 10, fontWeight: 600, padding: '3px 10px', borderRadius: 12,
                  border: `1px solid ${active ? colors.dot : 'var(--c-border)'}`,
                  background: active ? colors.bg : 'transparent',
                  color: active ? colors.text : 'var(--c-text-dim)',
                  cursor: 'pointer', textTransform: 'uppercase', letterSpacing: '0.04em',
                }}>
                  {p} ({counts.by_priority?.[p] || 0})
                </button>
              )
            })}
            <button onClick={fetchCases} style={{
              fontSize: 11, padding: '3px 12px', borderRadius: 6,
              border: '1px solid var(--c-border)', background: 'transparent',
              color: 'var(--c-text-dim)', cursor: 'pointer',
            }}>↻ Refresh</button>
          </div>
        </div>

        {/* Date tabs */}
        <div style={{ display: 'flex', gap: 0, marginBottom: 8 }}>
          {dateTabs.map(t => {
            const active = dateTab === t.id
            return (
              <button key={t.id} onClick={() => setDateTab(t.id)} style={{
                padding: '8px 18px', fontSize: 12, fontWeight: active ? 600 : 400,
                color: active ? 'var(--c-accent)' : 'var(--c-text-dim)',
                background: 'transparent', border: 'none', cursor: 'pointer',
                borderBottom: active ? '2px solid var(--c-accent)' : '2px solid transparent',
                transition: 'all 0.15s',
              }}>
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Type sub-tabs */}
        <div style={{ display: 'flex', gap: 6, paddingBottom: 10 }}>
          {typeTabs.map(t => {
            const active = typeTab === t.id
            return (
              <button key={t.id || 'all'} onClick={() => setTypeTab(t.id)} style={{
                fontSize: 10, fontWeight: 600, padding: '3px 10px', borderRadius: 12,
                border: `1px solid ${active ? 'var(--c-accent)' : 'var(--c-border)'}`,
                background: active ? 'var(--c-accent-soft)' : 'transparent',
                color: active ? 'var(--c-accent)' : 'var(--c-text-dim)',
                cursor: 'pointer',
              }}>
                {t.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflow: 'auto', padding: '0' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>Loading claims…</div>
        ) : cases.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>No claims found.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)' }}>
                {['Claim #', 'Type', 'Member', 'Flags / Tasks', 'Risk', 'Status'].map(h => (
                  <th key={h} style={{
                    padding: '10px 16px', textAlign: 'left', fontSize: 10,
                    fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
                    color: 'var(--c-text-dim)', position: 'sticky', top: 0,
                    background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cases.map(c => {
                const colors = PRIORITY_COLORS[c.priority] || PRIORITY_COLORS.LOW
                const typeColor = TYPE_COLORS[c.claim_type] || TYPE_COLORS.wellness
                const ruleCount = c.rules_triggered?.length || 0
                const taskCount = c.workflow_tasks?.length || 0
                return (
                  <tr key={c.case_id}
                    onClick={() => onSelectCase(c)}
                    style={{
                      cursor: 'pointer', borderBottom: '1px solid var(--c-border)',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--c-accent-faint)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '11px 16px', fontWeight: 600, color: 'var(--c-blue)', fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>
                      {c.case_id}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 10,
                        background: typeColor.bg, color: typeColor.text, fontWeight: 600,
                      }}>
                        {TYPE_LABELS[c.claim_type] || c.claim_type}
                      </span>
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <div style={{ color: 'var(--c-text)', fontWeight: 500 }}>{c.subject_name}</div>
                      <div style={{ fontSize: 11, color: 'var(--c-text-dim)' }}>{c.employer_name}</div>
                    </td>
                    <td style={{ padding: '11px 16px', color: 'var(--c-text-dim)', fontSize: 12 }}>
                      {ruleCount > 0 && <span style={{ marginRight: 8 }}>🚩 {ruleCount}</span>}
                      {taskCount > 0 && <span style={{ marginRight: 8 }}>📋 {taskCount}</span>}
                      {ruleCount === 0 && taskCount === 0 && <span style={{ color: 'var(--c-text-muted)', marginRight: 8 }}>—</span>}
                      {c.key_metrics?.complexity === 'Complex' && (
                        <span style={{
                          fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 8,
                          background: 'rgba(234,179,8,0.15)', color: '#fbbf24',
                          textTransform: 'uppercase', letterSpacing: '0.05em',
                        }}>
                          Complex
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                        <span style={{ width: 7, height: 7, borderRadius: '50%', background: colors.dot, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, fontWeight: 600, color: colors.text }}>
                          {c.risk_score}
                        </span>
                      </span>
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 10,
                        background: 'rgba(100,116,139,0.12)', color: '#94a3b8', fontWeight: 500,
                        textTransform: 'capitalize',
                      }}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
