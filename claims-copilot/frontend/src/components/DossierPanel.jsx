import { useRef, useCallback, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import html2pdf from 'html2pdf.js'

export default function DossierPanel({ dossier, findings, isComplete }) {
  const dossierRef = useRef(null)
  const [generating, setGenerating] = useState(false)

  const handleDownloadPDF = useCallback(async () => {
    if (!dossierRef.current) return
    setGenerating(true)
    try {
      const el = dossierRef.current
      const opt = {
        margin:      [0.5, 0.6, 0.5, 0.6],
        filename:    `fraud_dossier_${new Date().toISOString().slice(0, 10)}.pdf`,
        image:       { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF:       { unit: 'in', format: 'letter', orientation: 'portrait' },
        pagebreak:   { mode: ['avoid-all', 'css', 'legacy'] },
      }
      await html2pdf().set(opt).from(el).save()
    } finally {
      setGenerating(false)
    }
  }, [])

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
          style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="2" width="14" height="16" rx="2" stroke="#3b82f6" strokeWidth="1.5" />
              <line x1="6" y1="6" x2="14" y2="6" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="6" y1="9" x2="14" y2="9" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="6" y1="12" x2="11" y2="12" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <h2 className="text-base font-semibold" style={{ color: 'var(--c-text)' }}>
              Investigation Dossier
            </h2>
            {isComplete && (
              <span
                className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase"
                style={{ background: 'var(--c-green-bg)', color: 'var(--c-green)', border: '1px solid var(--c-green-border)' }}
              >
                Complete
              </span>
            )}
            {isComplete && (
              <button
                onClick={handleDownloadPDF}
                disabled={generating}
                className="ml-auto flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all cursor-pointer"
                style={{
                  background: generating ? 'var(--c-surface2)' : 'var(--c-accent)',
                  color: '#fff',
                  border: 'none',
                  opacity: generating ? 0.6 : 1,
                }}
              >
                {generating ? (
                  <>
                    <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Generating…
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Download PDF
                  </>
                )}
              </button>
            )}
          </div>

          {/* Hidden clone for PDF (light theme, print-friendly) */}
          <div style={{ position: 'absolute', left: '-9999px', top: 0 }}>
            <div ref={dossierRef} className="dossier-pdf-content">
              <Markdown remarkPlugins={[remarkGfm]}>{dossier}</Markdown>
            </div>
          </div>

          <div className="dossier-content text-sm leading-relaxed">
            <Markdown remarkPlugins={[remarkGfm]}>{dossier}</Markdown>
          </div>
        </div>
      )}

      {/* Findings (shown when no dossier yet but findings exist) */}
      {!dossier && findings && Object.keys(findings).length > 0 && (
        <div
          className="rounded-xl p-5"
          style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
        >
          <h2 className="text-base font-semibold mb-3" style={{ color: 'var(--c-text)' }}>
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
