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
  const [generating, setGenerating] = useState(false)
  const [aiGenerating, setAiGenerating] = useState(false)
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(false)
  const [aiDossier, setAiDossier] = useState(null)
  const [aiError, setAiError] = useState(null)

  useEffect(() => {
    if (!caseId) { setClaim(null); setAiDossier(null); setAiError(null); return }
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
          padding: '16px 20px', borderRadius: 12,
          background: 'var(--c-surface)', border: '1px solid var(--c-border)',
        }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <rect x="3" y="2" width="14" height="16" rx="2" stroke="#3b82f6" strokeWidth="1.5" />
            <line x1="6" y1="6" x2="14" y2="6" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="6" y1="9" x2="14" y2="9" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="6" y1="12" x2="11" y2="12" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
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
              fontSize: 12, fontWeight: 600, padding: '6px 14px', borderRadius: 8,
              background: aiGenerating ? 'var(--c-surface2)' : 'rgba(99,102,241,0.85)',
              color: aiGenerating ? '#6366f1' : '#fff',
              border: '1px solid rgba(99,102,241,0.3)',
              cursor: aiGenerating ? 'default' : 'pointer',
              opacity: aiGenerating ? 0.7 : 1, transition: 'all 0.15s',
            }}
          >
            {aiGenerating ? (
              <><span className="animate-pulse">✦</span> Writing…</>
            ) : (
              <><span>✦</span> {aiDossier ? 'Regenerate' : 'Generate AI Dossier'}</>
            )}
          </button>
          <button
            onClick={handleDownloadPDF}
            disabled={generating}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 12, fontWeight: 600, padding: '6px 14px', borderRadius: 8,
              background: generating ? 'var(--c-surface2)' : 'var(--c-accent)',
              color: '#fff', border: 'none', cursor: generating ? 'default' : 'pointer',
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
            marginBottom: 12, padding: '12px 16px', borderRadius: 8,
            background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)',
            fontSize: 12, color: '#818cf8', display: 'flex', alignItems: 'center', gap: 8,
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
            padding: 20, borderRadius: 12,
            background: 'var(--c-surface)', border: '1px solid var(--c-border)',
            fontSize: 13, lineHeight: 1.7,
          }}
        >
          <Markdown remarkPlugins={[remarkGfm]}>{dossierMarkdown}</Markdown>
        </div>
      </div>
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

  return `# Supplemental Health Claim Dossier

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

*Generated ${new Date().toISOString().slice(0, 16).replace('T', ' ')} · Prudential Supplemental Health Examiner Workflow*
`
}
