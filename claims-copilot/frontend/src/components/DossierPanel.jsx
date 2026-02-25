import Markdown from 'react-markdown'

export default function DossierPanel({ dossier, findings, isComplete }) {
  if (!dossier && (!findings || Object.keys(findings).length === 0)) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="text-4xl opacity-20">📄</div>
          <p className="text-sm" style={{ color: 'var(--c-text-dim)' }}>
            Investigation dossier will appear here
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Dossier */}
      {dossier && (
        <div
          className="rounded-xl p-5"
          style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="2" width="14" height="16" rx="2" stroke="#3b82f6" strokeWidth="1.5" />
              <line x1="6" y1="6" x2="14" y2="6" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="6" y1="9" x2="14" y2="9" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="6" y1="12" x2="11" y2="12" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <h2 className="text-base font-semibold" style={{ color: '#e2e8f0' }}>
              Investigation Dossier
            </h2>
            {isComplete && (
              <span
                className="ml-auto text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase"
                style={{ background: '#14532d', color: '#86efac', border: '1px solid #22c55e' }}
              >
                Complete
              </span>
            )}
          </div>
          <div className="dossier-content text-sm leading-relaxed">
            <Markdown>{dossier}</Markdown>
          </div>
        </div>
      )}

      {/* Findings (shown when no dossier yet but findings exist) */}
      {!dossier && findings && Object.keys(findings).length > 0 && (
        <div
          className="rounded-xl p-5"
          style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}
        >
          <h2 className="text-base font-semibold mb-3" style={{ color: '#e2e8f0' }}>
            Findings (In Progress)
          </h2>
          <div className="space-y-3">
            {Object.entries(findings).map(([key, value]) => (
              <div key={key}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--c-accent)' }}>
                  {key.replace(/_/g, ' ')}
                </div>
                <div
                  className="text-xs font-mono p-3 rounded-lg whitespace-pre-wrap"
                  style={{ background: 'var(--c-surface2)', color: 'var(--c-text-dim)' }}
                >
                  {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
