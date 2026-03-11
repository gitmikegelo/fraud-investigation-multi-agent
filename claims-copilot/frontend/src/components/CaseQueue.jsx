import { useState, useEffect } from 'react'

const PRIORITY_COLORS = {
  HIGH:   { dot: '#ef4444', bg: 'rgba(239,68,68,0.08)', text: '#fca5a5' },
  MEDIUM: { dot: '#f59e0b', bg: 'rgba(245,158,11,0.08)', text: '#fcd34d' },
  LOW:    { dot: '#6b7280', bg: 'rgba(107,114,128,0.08)', text: '#9ca3af' },
}

const TYPE_LABELS = {
  provider_fraud:   'Provider Fraud',
  disability_claim: 'Disability',
}

export default function CaseQueue({ onSelectCase }) {
  const [cases, setCases] = useState([])
  const [counts, setCounts] = useState({ total: 0, by_type: {}, by_priority: {} })
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [filterPriority, setFilterPriority] = useState(null)

  const fetchCases = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (activeTab !== 'all') params.set('case_type', activeTab)
      if (filterPriority) params.set('priority', filterPriority)
      const res = await fetch(`http://${window.location.hostname}:8000/api/cases?${params}`)
      const data = await res.json()
      setCases(data.cases || [])
      setCounts(data.counts || { total: 0, by_type: {}, by_priority: {} })
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCases() }, [activeTab, filterPriority])

  const tabs = [
    { id: 'all', label: `All (${counts.total})` },
    { id: 'disability_claim', label: `Disability (${counts.by_type?.disability_claim || 0})` },
    { id: 'provider_fraud', label: `Provider Fraud (${counts.by_type?.provider_fraud || 0})` },
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
            Investigation Queue
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
                  {p}
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

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 0 }}>
          {tabs.map(t => {
            const active = activeTab === t.id
            return (
              <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
                padding: '8px 18px', fontSize: 12, fontWeight: active ? 600 : 400,
                color: active ? '#c7d2fe' : 'var(--c-text-dim)',
                background: 'transparent', border: 'none', cursor: 'pointer',
                borderBottom: active ? '2px solid #6366f1' : '2px solid transparent',
                transition: 'all 0.15s',
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
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>Loading cases…</div>
        ) : cases.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>No cases found.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)' }}>
                {['Case ID', 'Type', 'Subject', 'Flag Reason', 'Priority', 'Status'].map(h => (
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
                return (
                  <tr key={c.case_id}
                    onClick={() => onSelectCase(c)}
                    style={{
                      cursor: 'pointer', borderBottom: '1px solid var(--c-border)',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '11px 16px', fontWeight: 600, color: '#818cf8', fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>
                      {c.case_id}
                    </td>
                    <td style={{ padding: '11px 16px', color: 'var(--c-text-dim)' }}>
                      <span style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 10,
                        background: c.case_type === 'disability_claim' ? 'rgba(168,85,247,0.12)' : 'rgba(59,130,246,0.12)',
                        color: c.case_type === 'disability_claim' ? '#c084fc' : '#60a5fa',
                        fontWeight: 600,
                      }}>
                        {TYPE_LABELS[c.case_type] || c.case_type}
                      </span>
                    </td>
                    <td style={{ padding: '11px 16px', color: 'var(--c-text)', fontWeight: 500 }}>
                      {c.subject_name}
                    </td>
                    <td style={{ padding: '11px 16px', color: 'var(--c-text-dim)', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {c.flag_reason}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                        <span style={{ width: 7, height: 7, borderRadius: '50%', background: colors.dot, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, fontWeight: 600, color: colors.text }}>{c.priority}</span>
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
