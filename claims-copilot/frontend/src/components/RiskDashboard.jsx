import { useState, useEffect } from 'react'

const TIER_COLORS = {
  HIGH:   { dot: '#ef4444', bg: 'rgba(239,68,68,0.08)', text: '#fca5a5' },
  MEDIUM: { dot: '#f59e0b', bg: 'rgba(245,158,11,0.08)', text: '#fcd34d' },
  LOW:    { dot: '#6b7280', bg: 'rgba(107,114,128,0.08)', text: '#9ca3af' },
}

export default function RiskDashboard({ onSelectClaim }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`http://${window.location.hostname}:8000/api/claims/stats`)
        const data = await res.json()
        setStats(data)
      } catch {
        // silent
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>Loading dashboard…</div>
  }
  if (!stats) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>Failed to load dashboard data.</div>
  }

  const dist = stats.risk_distribution || {}
  const total = stats.total_claims || 1
  const topRules = stats.top_rules_triggered || []
  const patterns = stats.pattern_details || []
  const workflow = stats.workflow_health || {}
  const intercepts = stats.intercepts || {}

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 24 }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--c-text)', marginBottom: 20, letterSpacing: '-0.01em' }}>
          Risk Dashboard
        </h2>

        {/* Top cards row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
          {/* Intercepts */}
          <Card title="Auto-Adj Intercepts">
            <div style={{ fontSize: 28, fontWeight: 800, color: '#ef4444' }}>{intercepts.count || 0}</div>
            <div style={{ fontSize: 12, color: 'var(--c-text-dim)', marginTop: 4 }}>
              ${(intercepts.held_amount || 0).toLocaleString()} held
            </div>
          </Card>

          {/* Risk Distribution */}
          <Card title="Risk Distribution">
            {['HIGH', 'MEDIUM', 'LOW'].map(tier => {
              const count = dist[tier] || 0
              const pct = ((count / total) * 100).toFixed(1)
              const tc = TIER_COLORS[tier]
              return (
                <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: tc.dot, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, fontWeight: 600, color: tc.text, width: 55 }}>{tier}</span>
                  <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--c-surface2)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: tc.dot, borderRadius: 3 }} />
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--c-text-dim)', width: 40, textAlign: 'right' }}>{count}</span>
                </div>
              )
            })}
          </Card>

          {/* Workflow Health */}
          <Card title="Workflow Health">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <StatLine label="Open PMR" value={workflow.open_pmr || 0} color={workflow.open_pmr > 5 ? '#f59e0b' : '#22c55e'} />
              <StatLine label="Pending CBR" value={workflow.pending_cbr || 0} color={workflow.pending_cbr > 5 ? '#f59e0b' : '#22c55e'} />
              <StatLine label="Past TAT" value={workflow.past_tat || 0} color={workflow.past_tat > 0 ? '#ef4444' : '#22c55e'} />
            </div>
          </Card>
        </div>

        {/* Bottom row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {/* Top Rules Triggered */}
          <Card title="Top Rules Triggered">
            {topRules.length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--c-text-dim)' }}>No rules triggered</div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={thStyle}>Rule</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {topRules.slice(0, 10).map(([ruleId, count], i) => (
                    <tr key={i}>
                      <td style={{ padding: '4px 0', color: 'var(--c-blue)', fontFamily: 'ui-monospace, monospace', fontWeight: 600, fontSize: 11 }}>{ruleId}</td>
                      <td style={{ padding: '4px 0', textAlign: 'right', color: 'var(--c-text)', fontWeight: 600 }}>{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {/* Patterns Detected */}
          <Card title={`Patterns Detected (${stats.patterns_detected || 0})`}>
            {patterns.length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--c-text-dim)' }}>No patterns detected</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {patterns.slice(0, 10).map((p, i) => (
                  <div key={i} style={{
                    padding: '8px 10px', borderRadius: 8, background: 'var(--c-surface2)',
                    border: '1px solid var(--c-border)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 6,
                        background: p.severity === 'HIGH' ? 'rgba(239,68,68,0.12)' : p.severity === 'MEDIUM' ? 'rgba(245,158,11,0.12)' : 'rgba(107,114,128,0.12)',
                        color: p.severity === 'HIGH' ? '#fca5a5' : p.severity === 'MEDIUM' ? '#fcd34d' : '#9ca3af',
                      }}>
                        {p.severity}
                      </span>
                      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--c-text)' }}>
                        {p.pattern_type?.replace(/_/g, ' ')}
                      </span>
                      <span style={{ fontSize: 10, color: 'var(--c-text-dim)', marginLeft: 'auto' }}>
                        {p.entity_count} entities
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--c-text-dim)' }}>
                      {p.description?.slice(0, 100)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}


function Card({ title, children }) {
  return (
    <div style={{
      padding: 20, borderRadius: 'var(--r-card)',
      background: 'var(--c-surface)', border: '1px solid var(--c-border)',
      boxShadow: 'var(--c-shadow-sm)',
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--c-text-dim)', marginBottom: 12 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function StatLine({ label, value, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span style={{ fontSize: 12, color: 'var(--c-text-dim)' }}>{label}</span>
      <span style={{ fontSize: 16, fontWeight: 700, color }}>{value}</span>
    </div>
  )
}

const thStyle = {
  padding: '4px 0', fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.05em', color: 'var(--c-text-dim)', borderBottom: '1px solid var(--c-border)',
  textAlign: 'left',
}
