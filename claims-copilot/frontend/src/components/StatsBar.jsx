export default function StatsBar({ result, isComplete }) {
  if (!isComplete || !result) return null

  const stats = [
    { label: 'Total Steps', value: result.iterations, icon: '🔄' },
    { label: 'Wall Time', value: `${result.total_time}s`, icon: '⏱' },
    { label: 'Final Phase', value: result.phase, icon: '📋' },
    { label: 'Evidence', value: result.evidence_sufficient ? 'Sufficient' : 'Insufficient', icon: result.evidence_sufficient ? '✅' : '⚠️' },
    { label: 'Loop Count', value: result.loop_count, icon: '🔁' },
  ]

  return (
    <div
      className="flex items-center gap-1 px-6 py-2 overflow-x-auto"
      style={{ background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)' }}
    >
      {stats.map((s, i) => (
        <div
          key={i}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
          style={{ background: 'var(--c-surface2)' }}
        >
          <span className="text-sm">{s.icon}</span>
          <div>
            <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--c-text-dim)' }}>
              {s.label}
            </div>
            <div className="text-sm font-semibold" style={{ color: 'var(--c-text)' }}>
              {s.value}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
