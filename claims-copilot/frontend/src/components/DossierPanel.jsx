import { useRef, useCallback, useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import html2pdf from 'html2pdf.js'

const TIER_DOT = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#6b7280' }

function tier(score) {
  if (score >= 60) return 'HIGH'
  if (score >= 30) return 'MEDIUM'
  return 'LOW'
}

export default function DossierPanel({ caseId }) {
  const dossierRef = useRef(null)
  const letterRef = useRef(null)
  const [generating, setGenerating] = useState(false)
  const [aiGenerating, setAiGenerating] = useState(false)
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(false)
  const [aiDossier, setAiDossier] = useState(null)
  const [aiError, setAiError] = useState(null)
  const [letter, setLetter] = useState(null)
  const [letterGenerating, setLetterGenerating] = useState(false)
  const [letterError, setLetterError] = useState(null)
  const [letterOpen, setLetterOpen] = useState(false)
  const [letterPdfGenerating, setLetterPdfGenerating] = useState(false)

  useEffect(() => {
    if (!caseId) { setClaim(null); setAiDossier(null); setAiError(null); setLetter(null); setLetterError(null); setLetterOpen(false); return }
    setLetter(null); setLetterError(null); setLetterOpen(false)
    const load = async () => {
      setLoading(true)
      setAiDossier(null)
      setAiError(null)
      let claimData = null
      try {
        const res = await fetch(`http://${window.location.hostname}:8000/api/claims/${caseId}`)
        claimData = await res.json()
        setClaim(claimData)
        // If a previously generated AI dossier is cached on the claim, show it
        if (claimData.dossier) { setAiDossier(claimData.dossier); setLoading(false); return }
      } catch { setLoading(false); return }
      setLoading(false)

      // Auto-generate AI dossier on first open
      setAiGenerating(true)
      try {
        const genRes = await fetch(
          `http://${window.location.hostname}:8000/api/claims/${caseId}/generate_dossier`,
          { method: 'POST' }
        )
        const genData = await genRes.json()
        if (genData.error) setAiError(genData.error)
        else setAiDossier(genData.dossier)
      } catch {
        setAiError('AI generation failed. Showing standard dossier.')
      } finally {
        setAiGenerating(false)
      }
    }
    load()
  }, [caseId])

  const handleGenerateAI = useCallback(async () => {
    if (!caseId) return
    setAiGenerating(true)
    setAiError(null)
    try {
      const res = await fetch(
        `http://${window.location.hostname}:8000/api/claims/${caseId}/generate_dossier`,
        { method: 'POST' }
      )
      const data = await res.json()
      if (data.error) { setAiError(data.error); return }
      setAiDossier(data.dossier)
    } catch (e) {
      setAiError('Failed to generate dossier. Check backend connection.')
    } finally {
      setAiGenerating(false)
    }
  }, [caseId])

  const handleGenerateLetter = useCallback(async () => {
    if (!caseId) return
    setLetterOpen(true)
    // Reuse an already-generated letter if present
    if (letter) return
    setLetterGenerating(true)
    setLetterError(null)
    try {
      const res = await fetch(
        `http://${window.location.hostname}:8000/api/claims/${caseId}/generate_letter`,
        { method: 'POST' }
      )
      const data = await res.json()
      if (data.error) { setLetterError(data.error); return }
      setLetter(data.letter)
    } catch {
      setLetterError('Failed to generate letter. Check backend connection.')
    } finally {
      setLetterGenerating(false)
    }
  }, [caseId, letter])

  const handleDownloadLetterPDF = useCallback(async () => {
    if (!letterRef.current) return
    setLetterPdfGenerating(true)
    try {
      const opt = {
        margin:      [0.75, 0.75, 0.75, 0.75],
        filename:    `claimant_letter_${caseId || 'unknown'}_${new Date().toISOString().slice(0, 10)}.pdf`,
        image:       { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF:       { unit: 'in', format: 'letter', orientation: 'portrait' },
        pagebreak:   { mode: ['avoid-all', 'css', 'legacy'] },
      }
      await html2pdf().set(opt).from(letterRef.current).save()
    } finally {
      setLetterPdfGenerating(false)
    }
  }, [caseId])

  const handleDownloadPDF = useCallback(async () => {
    if (!dossierRef.current) return
    setGenerating(true)
    try {
      const opt = {
        margin:      [0.5, 0.6, 0.5, 0.6],
        filename:    `claim_dossier_${caseId || 'unknown'}_${new Date().toISOString().slice(0, 10)}.pdf`,
        image:       { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF:       { unit: 'in', format: 'letter', orientation: 'portrait' },
        pagebreak:   { mode: ['avoid-all', 'css', 'legacy'] },
      }
      await html2pdf().set(opt).from(dossierRef.current).save()
    } finally {
      setGenerating(false)
    }
  }, [caseId])

  if (!caseId) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="text-4xl opacity-20">📄</div>
          <p className="text-sm" style={{ color: 'var(--c-text-dim)' }}>
            Select a claim from the queue to view its dossier
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>Loading claim data…</div>
  }

  if (!claim) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>Claim not found.</div>
  }

  const rs = claim.risk_score || 0
  const t = tier(rs)
  const rules = claim.rules_triggered || []
  const docs = claim.document_flags || []
  const checklist = claim.checklist_state || {}
  const steps = checklist.steps || []

  const dossierMarkdown = aiDossier || buildDossierMarkdown(claim, rules, docs, steps)

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 24 }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
          padding: '16px 20px', borderRadius: 'var(--r-card)',
          background: 'var(--c-surface)', border: '1px solid var(--c-border)',
          boxShadow: 'var(--c-shadow-sm)',
        }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <rect x="3" y="2" width="14" height="16" rx="2" stroke="var(--c-blue)" strokeWidth="1.5" />
            <line x1="6" y1="6" x2="14" y2="6" stroke="var(--c-blue)" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="6" y1="9" x2="14" y2="9" stroke="var(--c-blue)" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="6" y1="12" x2="11" y2="12" stroke="var(--c-blue)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <div style={{ flex: 1 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--c-text)', margin: 0 }}>
              Claim Dossier — {claim.case_id}
            </h2>
            <div style={{ fontSize: 12, color: 'var(--c-text-dim)', marginTop: 2 }}>
              {claim.subject_name} · {claim.claim_type?.replace(/_/g, ' ')} · ${(claim.claim_amount || 0).toLocaleString()}
              {aiDossier && <span style={{ marginLeft: 8, color: '#22c55e', fontWeight: 600 }}>✦ AI-Generated</span>}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: TIER_DOT[t] }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: TIER_DOT[t] }}>{rs}</span>
          </div>
          {/* Generate AI Dossier button */}
          <button
            onClick={handleGenerateAI}
            disabled={aiGenerating}
            title="Use Claude to write a comprehensive narrative dossier"
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 600, padding: '7px 16px', borderRadius: 'var(--r-btn)',
              textTransform: 'uppercase', letterSpacing: '0.04em',
              background: aiGenerating ? 'var(--c-accent-soft)' : 'linear-gradient(90deg, #a100ff, #d6298a)',
              color: aiGenerating ? 'var(--c-accent)' : '#fff',
              border: 'none',
              cursor: aiGenerating ? 'default' : 'pointer',
              opacity: aiGenerating ? 0.8 : 1, transition: 'all 0.15s',
            }}
          >
            {aiGenerating ? (
              <><span className="animate-pulse">✦</span> Writing…</>
            ) : (
              <><span>✦</span> {aiDossier ? 'Regenerate' : 'Generate AI Dossier'}</>
            )}
          </button>
          <button
            onClick={handleGenerateLetter}
            disabled={letterGenerating}
            title="Generate a short, plain-language letter to send to the claimant"
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 600, padding: '7px 16px', borderRadius: 'var(--r-btn)',
              textTransform: 'uppercase', letterSpacing: '0.04em',
              background: 'transparent',
              color: 'var(--c-blue)', border: '1px solid var(--c-blue)',
              cursor: letterGenerating ? 'default' : 'pointer',
              opacity: letterGenerating ? 0.6 : 1,
            }}
          >
            {letterGenerating ? 'Writing…' : '✉ Claimant Letter'}
          </button>
          <button
            onClick={handleDownloadPDF}
            disabled={generating}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 600, padding: '7px 16px', borderRadius: 'var(--r-btn)',
              textTransform: 'uppercase', letterSpacing: '0.04em',
              background: 'transparent',
              color: 'var(--c-accent)', border: '1px solid var(--c-accent)',
              cursor: generating ? 'default' : 'pointer',
              opacity: generating ? 0.6 : 1,
            }}
          >
            {generating ? 'Generating…' : 'Download PDF'}
          </button>
        </div>

        {/* AI error */}
        {aiError && (
          <div style={{
            marginBottom: 12, padding: '10px 16px', borderRadius: 8,
            background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
            fontSize: 12, color: '#ef4444',
          }}>
            ⚠ {aiError}
          </div>
        )}

        {/* AI generating progress */}
        {aiGenerating && (
          <div style={{
            marginBottom: 12, padding: '12px 16px', borderRadius: 'var(--r-btn)',
            background: 'var(--c-accent-faint)', border: '1px solid var(--c-accent-soft)',
            fontSize: 12, color: 'var(--c-accent)', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span className="animate-pulse">✦</span>
            Claude is reading all intelligence layers and writing the full investigation report…
          </div>
        )}

        {/* Hidden PDF clone */}
        <div style={{ position: 'absolute', left: '-9999px', top: 0 }}>
          <div ref={dossierRef} className="dossier-pdf-content">
            <Markdown remarkPlugins={[remarkGfm]}>{dossierMarkdown}</Markdown>
          </div>
        </div>

        {/* Rendered dossier */}
        <div
          className="dossier-content"
          style={{
            padding: 24, borderRadius: 'var(--r-card)',
            background: 'var(--c-surface)', border: '1px solid var(--c-border)',
            boxShadow: 'var(--c-shadow-sm)',
            fontSize: 13, lineHeight: 1.7,
          }}
        >
          <Markdown remarkPlugins={[remarkGfm]}>{dossierMarkdown}</Markdown>
        </div>
      </div>

      {/* Claimant letter modal */}
      {letterOpen && (
        <div
          onClick={() => setLetterOpen(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%', maxWidth: 680, maxHeight: '90vh', display: 'flex', flexDirection: 'column',
              borderRadius: 'var(--r-card)', background: 'var(--c-surface)',
              border: '1px solid var(--c-border)', boxShadow: 'var(--c-shadow-md, 0 10px 40px rgba(0,0,0,0.3))',
              overflow: 'hidden',
            }}
          >
            {/* Modal header */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px',
              borderBottom: '1px solid var(--c-border)',
            }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-text)', margin: 0 }}>
                  Claimant Letter — {claim.case_id}
                </h3>
                <div style={{ fontSize: 11, color: 'var(--c-text-dim)', marginTop: 2 }}>
                  Plain-language notice for {claim.subject_name}
                </div>
              </div>
              {letter && !letterGenerating && (
                <button
                  onClick={handleDownloadLetterPDF}
                  disabled={letterPdfGenerating}
                  style={{
                    fontSize: 11, fontWeight: 600, padding: '7px 14px', borderRadius: 'var(--r-btn)',
                    textTransform: 'uppercase', letterSpacing: '0.04em',
                    background: 'transparent', color: 'var(--c-accent)', border: '1px solid var(--c-accent)',
                    cursor: letterPdfGenerating ? 'default' : 'pointer', opacity: letterPdfGenerating ? 0.6 : 1,
                  }}
                >
                  {letterPdfGenerating ? 'Generating…' : 'Download PDF'}
                </button>
              )}
              <button
                onClick={() => setLetterOpen(false)}
                style={{
                  fontSize: 18, lineHeight: 1, padding: '4px 10px', borderRadius: 'var(--r-btn)',
                  background: 'transparent', color: 'var(--c-text-dim)', border: 'none', cursor: 'pointer',
                }}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Modal body */}
            <div style={{ padding: 24, overflow: 'auto' }}>
              {letterGenerating && (
                <div style={{ textAlign: 'center', color: 'var(--c-blue)', fontSize: 13, padding: 20 }}>
                  <span className="animate-pulse">✉</span> Drafting the claimant letter…
                </div>
              )}
              {letterError && (
                <div style={{
                  padding: '10px 16px', borderRadius: 8,
                  background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                  fontSize: 12, color: '#ef4444',
                }}>
                  ⚠ {letterError}
                </div>
              )}
              {letter && !letterGenerating && (
                <div
                  className="dossier-content"
                  style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--c-text)' }}
                >
                  <Markdown remarkPlugins={[remarkGfm]}>{letter}</Markdown>
                </div>
              )}
              {/* Hidden PDF clone (white background for print) */}
              <div style={{ position: 'absolute', left: '-9999px', top: 0 }}>
                <div ref={letterRef} className="dossier-pdf-content" style={{ color: '#111' }}>
                  {letter && <Markdown remarkPlugins={[remarkGfm]}>{letter}</Markdown>}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


function buildDossierMarkdown(claim, rules, docs, steps) {
  const rs = claim.risk_score || 0
  const t = tier(rs)
  const ruleBlock = rules.length > 0
    ? rules.map(r => `| ${r.rule_id} | ${r.name} | ${r.severity} | ${r.detail || '—'} |`).join('\n')
    : '| — | No rules triggered | — | — |'
  const docBlock = docs.length > 0
    ? docs.map(d => `- **${d.check_id}** (${d.severity}): ${d.detail || d.message || '—'}`).join('\n')
    : '- No document flags'
  const checkBlock = steps.length > 0
    ? steps.map(s => `| ${s.step} | ${s.name} | ${(s.status || 'not_run').replace(/_/g, ' ')} | ${s.detail || '—'} |`).join('\n')
    : '| — | No checklist data | — | — |'

  return `# Travel Insurance Claim Dossier

## Claim Overview

| Field | Value |
|-------|-------|
| **Claim ID** | ${claim.case_id} |
| **Member** | ${claim.subject_name} |
| **Member ID** | ${claim.member_id || '—'} |
| **Employer** | ${claim.employer_name || '—'} |
| **Claim Type** | ${(claim.claim_type || '—').replace(/_/g, ' ')} |
| **Claim Amount** | $${(claim.claim_amount || 0).toLocaleString()} |
| **Coverage Period** | ${claim.coverage_start || '—'} to ${claim.coverage_end || '—'} |
| **Provider** | ${claim.provider_name || '—'} |
| **Status** | ${claim.status || '—'} |
| **Risk Score** | **${rs}** (${t}) |

## Rules Triggered (${rules.length})

| Rule | Name | Severity | Detail |
|------|------|----------|--------|
${ruleBlock}

## Document Analysis

${docBlock}

## Examiner Checklist

| Step | Check | Status | Detail |
|------|-------|--------|--------|
${checkBlock}

## Workflow Tasks

${(claim.workflow_tasks || []).length > 0
    ? (claim.workflow_tasks || []).map(wt => `- **${wt.task}**: ${wt.status || 'pending'} — ${wt.detail || ''}`).join('\n')
    : '- No pending workflow tasks'}

---

*Generated ${new Date().toISOString().slice(0, 16).replace('T', ' ')} · Zurich Travel Guard Claims Examiner Workflow*
`
}
