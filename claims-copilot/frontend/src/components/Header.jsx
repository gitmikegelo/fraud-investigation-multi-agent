const PHASE_META = {
  'start':       { color: '#6b7a94', label: 'Starting' },
  'scan':        { color: '#06b6d4', label: 'Scanning' },
  'investigate': { color: '#3b82f6', label: 'Investigating' },
  'compile':     { color: '#f59e0b', label: 'Compiling' },
  'done':        { color: '#22c55e', label: 'Done' },
  '—':           { color: '#6b7a94', label: 'Idle' },
}

export default function Header({ status, phase, loopCount, elapsed, onStart }) {
  const phaseMeta = PHASE_META[phase] || PHASE_META['—']
  const isRunning = status === 'running'
  const isComplete = status === 'complete'

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`
  }

  return (
    <header
      className="flex items-center justify-between px-6 py-3"
      style={{ background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)' }}
    >
      {/* Left: Brand */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="7" fill="#3b82f6" fillOpacity="0.15" />
            <path d="M8 14.5L12 18.5L20 10" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-lg font-semibold tracking-tight" style={{ color: '#e2e8f0' }}>
            ARIA
          </span>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--c-surface2)', color: 'var(--c-text-dim)' }}>
          AI Investigation
        </span>
      </div>

      {/* Center: Status */}
      <div className="flex items-center gap-6">
        {/* Phase indicator */}
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{
              background: phaseMeta.color,
              boxShadow: isRunning ? `0 0 8px ${phaseMeta.color}` : 'none',
            }}
          />
          <span className="text-sm font-medium" style={{ color: phaseMeta.color }}>
            {phaseMeta.label}
          </span>
        </div>

        {/* Loop count */}
        {loopCount > 0 && (
          <div className="text-xs" style={{ color: 'var(--c-text-dim)' }}>
            Loop <span className="font-mono font-semibold" style={{ color: 'var(--c-text)' }}>{loopCount}</span>
          </div>
        )}

        {/* Timer */}
        {(isRunning || isComplete) && (
          <div className="text-xs font-mono" style={{ color: 'var(--c-text-dim)' }}>
            ⏱ {formatTime(elapsed)}
          </div>
        )}
      </div>

      {/* Right: Action button */}
      <button
        onClick={onStart}
        disabled={isRunning}
        className="px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          background: isRunning
            ? 'var(--c-surface2)'
            : isComplete
              ? 'linear-gradient(135deg, #22c55e, #16a34a)'
              : 'linear-gradient(135deg, #3b82f6, #6366f1)',
          color: '#fff',
          border: 'none',
        }}
      >
        {isRunning ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="50 20" />
            </svg>
            Running…
          </span>
        ) : isComplete ? (
          '↻ Run Again'
        ) : (
          '▶ Start Investigation'
        )}
      </button>
    </header>
  )
}
