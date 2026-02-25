import { useState, useCallback, useRef, useEffect } from 'react'
import Header from './components/Header'
import GraphView from './components/GraphView'
import EventTimeline from './components/EventTimeline'
import DossierPanel from './components/DossierPanel'
import StatsBar from './components/StatsBar'
import NetworkGraph from './components/NetworkGraph'
import { useInvestigation } from './hooks/useInvestigation'

export default function App() {
  const {
    status,
    activeNode,
    phase,
    loopCount,
    events,
    logs,
    dossier,
    findings,
    result,
    startInvestigation,
    nodeHistory,
    elapsed,
    initialClaims,
  } = useInvestigation()

  const isRunning = status === 'running'
  const isComplete = status === 'complete'
  const [bottomTab, setBottomTab] = useState('dossier') // dossier | network

  // Resizable panel state
  const [leftWidth, setLeftWidth] = useState(55) // percentage
  const [graphHeight, setGraphHeight] = useState(280) // pixels
  const containerRef = useRef(null)
  const isResizingVertical = useRef(false)
  const isResizingHorizontal = useRef(false)

  // Handle vertical resize (left-right panels)
  const handleVerticalMouseDown = useCallback((e) => {
    e.preventDefault()
    isResizingVertical.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [])

  // Handle horizontal resize (graph-bottom panels)
  const handleHorizontalMouseDown = useCallback((e) => {
    e.preventDefault()
    isResizingHorizontal.current = true
    document.body.style.cursor = 'row-resize'
    document.body.style.userSelect = 'none'
  }, [])

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingVertical.current && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        const newWidth = ((e.clientX - rect.left) / rect.width) * 100
        setLeftWidth(Math.min(Math.max(newWidth, 25), 75)) // clamp between 25-75%
      }
      if (isResizingHorizontal.current && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        const newHeight = e.clientY - rect.top
        setGraphHeight(Math.min(Math.max(newHeight, 150), rect.height - 150)) // min 150px for each
      }
    }

    const handleMouseUp = () => {
      isResizingVertical.current = false
      isResizingHorizontal.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--c-bg)' }}>
      {/* Top bar */}
      <Header
        status={status}
        phase={phase}
        loopCount={loopCount}
        elapsed={elapsed}
        onStart={startInvestigation}
      />

      {/* Stats strip */}
      <StatsBar result={result} isComplete={isComplete} />

      {/* Main content - two column layout */}
      <div
        ref={containerRef}
        className="flex-1 flex gap-0 overflow-hidden"
        style={{ height: 'calc(100vh - 120px)' }}
      >
        {/* Left: Graph + Tabbed bottom panel */}
        <div className="flex flex-col min-w-0" style={{ width: `${leftWidth}%` }}>
          {/* Agent flow graph */}
          <div
            className="flex-shrink-0 relative"
            style={{ height: `${graphHeight}px`, borderBottom: '1px solid var(--c-border)' }}
          >
            <GraphView
              activeNode={activeNode}
              phase={phase}
              nodeHistory={nodeHistory}
              isRunning={isRunning}
              initialClaims={initialClaims}
            />
            {/* Horizontal resize handle */}
            <div
              onMouseDown={handleHorizontalMouseDown}
              className="absolute bottom-0 left-0 right-0 h-[6px] cursor-row-resize z-10 group"
              style={{ transform: 'translateY(50%)' }}
            >
              <div
                className="absolute inset-x-0 h-[2px] top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ background: 'var(--c-accent)' }}
              />
            </div>
          </div>

          {/* Bottom panel: tabs for Dossier / Fraud Network */}
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Tab bar */}
            <div
              className="flex items-center gap-0 px-4 flex-shrink-0"
              style={{ borderBottom: '1px solid var(--c-border)' }}
            >
              {[
                { key: 'dossier', label: 'Dossier', icon: '📄' },
                { key: 'network', label: 'Fraud Network', icon: '🕸️' },
              ].map(t => (
                <button
                  key={t.key}
                  onClick={() => setBottomTab(t.key)}
                  className="px-4 py-2 text-sm font-medium transition-colors relative cursor-pointer"
                  style={{
                    color: bottomTab === t.key ? 'var(--c-accent)' : 'var(--c-text-dim)',
                    background: 'transparent',
                    border: 'none',
                  }}
                >
                  <span className="mr-1.5">{t.icon}</span>
                  {t.label}
                  {bottomTab === t.key && (
                    <div
                      className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full"
                      style={{ background: 'var(--c-accent)' }}
                    />
                  )}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-auto">
              {bottomTab === 'dossier' ? (
                <div className="p-4">
                  <DossierPanel dossier={dossier} findings={findings} isComplete={isComplete} />
                </div>
              ) : (
                <NetworkGraph isComplete={isComplete} />
              )}
            </div>
          </div>
        </div>

        {/* Vertical resize handle */}
        <div
          onMouseDown={handleVerticalMouseDown}
          className="w-[6px] cursor-col-resize flex-shrink-0 relative z-10 group"
          style={{ marginLeft: '-3px', marginRight: '-3px' }}
        >
          <div
            className="absolute inset-y-0 w-[2px] left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ background: 'var(--c-accent)' }}
          />
        </div>

        {/* Right: Event timeline */}
        <div
          className="min-w-0 overflow-hidden flex flex-col"
          style={{ width: `${100 - leftWidth}%`, borderLeft: '1px solid var(--c-border)' }}
        >
          <EventTimeline events={events} logs={logs} isRunning={isRunning} />
        </div>
      </div>
    </div>
  )
}
