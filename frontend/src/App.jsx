import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertCircle, CircleHelp, GitBranch, Lightbulb, Loader2, Search, Send, WifiOff } from 'lucide-react'
import { analyzeChange, getAnalysisHistory, sendChatFollowup } from './api/analyzeChange'
import ComponentCard from './components/ComponentCard'
import ImpactGraph from './components/ImpactGraph'
import { buildMitigationMap, getRiskColor } from './utils/risk'
import './App.css'

const EXAMPLE_CHANGE = 'Increase auth token expiry from 1 hour to 24 hours'

export default function App() {
  const [changeText, setChangeText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [chatHistory, setChatHistory] = useState([])
  const [chatMessage, setChatMessage] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState(null)
  const [recentAnalyses, setRecentAnalyses] = useState([])
  const [graphSize, setGraphSize] = useState({ width: 800, height: 420 })
  const graphWrapperRef = useRef(null)
  const chatHistoryRef = useRef(null)

  useEffect(() => {
    const element = graphWrapperRef.current
    if (!element) return undefined

    const observer = new ResizeObserver(([entry]) => {
      const { width } = entry.contentRect
      setGraphSize({
        width: Math.max(Math.floor(width), 320),
        height: Math.min(Math.max(Math.floor(width * 0.55), 360), 560),
      })
    })

    observer.observe(element)
    return () => observer.disconnect()
  }, [analysis])

  useEffect(() => {
    chatHistoryRef.current?.scrollTo({ top: chatHistoryRef.current.scrollHeight, behavior: 'smooth' })
  }, [chatHistory, chatLoading])

  const loadHistory = useCallback(async () => {
    try {
      setRecentAnalyses(await getAnalysisHistory())
    } catch {
      setRecentAnalyses([])
    }
  }, [])

  useEffect(() => {
    void loadHistory()
  }, [loadHistory])

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault()

      const trimmed = changeText.trim()
      if (!trimmed) {
        setError('Please describe the proposed change before submitting.')
        setAnalysis(null)
        return
      }

      setLoading(true)
      setError(null)
      setAnalysis(null)
      setChatHistory([])
      setChatMessage('')
      setChatError(null)

      try {
        const result = await analyzeChange(trimmed)
        setAnalysis(result)
        void loadHistory()
      } catch (err) {
        if (err instanceof TypeError) {
          setError(
            'Unable to reach the analysis server. Make sure the backend is running at http://localhost:8000.',
          )
        } else {
          setError(err.message || 'Something went wrong while analyzing the change.')
        }
      } finally {
        setLoading(false)
      }
    },
    [changeText, loadHistory],
  )

  const loadSavedAnalysis = useCallback((entry) => {
    setChangeText(entry.change_description)
    setAnalysis(entry.result)
    setError(null)
    setChatHistory([])
    setChatMessage('')
    setChatError(null)
  }, [])

  const handleChatSubmit = useCallback(
    async (event) => {
      event.preventDefault()
      const trimmed = chatMessage.trim()
      if (!trimmed || !analysis || chatLoading) return

      const nextHistory = [...chatHistory, { role: 'user', content: trimmed }]
      setChatHistory(nextHistory)
      setChatMessage('')
      setChatError(null)
      setChatLoading(true)

      try {
        const response = await sendChatFollowup(trimmed, chatHistory, analysis)
        setChatHistory((history) => [...history, { role: 'assistant', content: response }])
      } catch (err) {
        setChatError(err.message || 'Unable to answer the follow-up question.')
      } finally {
        setChatLoading(false)
      }
    },
    [analysis, chatHistory, chatLoading, chatMessage],
  )

  const affectedComponents = analysis?.affected_components ?? []
  const mitigationMap = useMemo(
    () => buildMitigationMap(analysis?.mitigations),
    [analysis?.mitigations],
  )
  const hasResults = Boolean(analysis)
  const isUnclear = analysis?.status === 'unclear'
  const isEmpty = hasResults && !isUnclear && affectedComponents.length === 0

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__brand">
          <GitBranch className="app-header__icon" aria-hidden="true" />
          <div>
            <h1>Change Impact Analyzer</h1>
            <p>Map downstream risk before you deploy a change</p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className={affectedComponents.length > 0 && !loading ? 'analysis-workspace' : ''}>
        <section className="panel input-panel">
          <form className="change-form" onSubmit={handleSubmit}>
            <label htmlFor="change-description" className="change-form__label">
              Proposed change
            </label>
            <textarea
              id="change-description"
              className="change-form__input"
              placeholder="Describe the change you plan to make, e.g. increase auth token expiry to 24 hours..."
              value={changeText}
              onChange={(event) => setChangeText(event.target.value)}
              rows={4}
              disabled={loading}
            />
            <div className="change-form__actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setChangeText(EXAMPLE_CHANGE)}
                disabled={loading}
              >
                Use example
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="btn__icon spin" aria-hidden="true" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Search className="btn__icon" aria-hidden="true" />
                    Analyze impact
                  </>
                )}
              </button>
            </div>
          </form>
        </section>

        {recentAnalyses.length > 0 && (
          <section className="panel history-panel" aria-label="Recent analyses">
            <div className="panel__header">
              <h2>Recent Analyses</h2>
              <p>Reload a previous impact assessment.</p>
            </div>
            <div className="history-list">
              {recentAnalyses.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  className="history-item"
                  onClick={() => loadSavedAnalysis(entry)}
                >
                  <span className="history-item__description">{entry.change_description}</span>
                  <span className="history-item__meta">
                    {entry.target_node} · {entry.timestamp}
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}

        {error && (
          <section className="panel alert alert-error" role="alert">
            <AlertCircle className="alert__icon" aria-hidden="true" />
            <div>
              <strong>Analysis failed</strong>
              <p>{error}</p>
            </div>
          </section>
        )}

        {loading && (
          <section className="panel loading-panel">
            <Loader2 className="loading-panel__icon spin" aria-hidden="true" />
            <p>Tracing dependencies and scoring risk across affected components...</p>
          </section>
        )}

        {!loading && isUnclear && (
          <section className="panel alert alert-unclear" role="status">
            <CircleHelp className="alert__icon" aria-hidden="true" />
            <div>
              <strong>Choose a specific component</strong>
              <p>{analysis.message}</p>
              <div className="valid-components" aria-label="Valid components">
                {analysis.valid_components.map((component) => (
                  <code key={component}>{component}</code>
                ))}
              </div>
            </div>
          </section>
        )}

        {!loading && isEmpty && (
          <section className="panel alert alert-info" role="status">
            <WifiOff className="alert__icon" aria-hidden="true" />
            <div>
              <strong>No downstream impact detected</strong>
              <p>
                The change targets <code>{analysis.targeted_node}</code>, but no affected
                components were found within the configured graph depth.
              </p>
            </div>
          </section>
        )}

        {!loading && affectedComponents.length > 0 && (
          <>
            {analysis.overall_recommendation && (
              <section className="panel recommendation-panel" role="status">
                <Lightbulb className="recommendation-panel__icon" aria-hidden="true" />
                <div>
                  <strong>Recommended approach</strong>
                  <p>{analysis.overall_recommendation}</p>
                </div>
              </section>
            )}

            <section className="panel graph-panel">
              <div className="panel__header">
                <h2>Impact graph</h2>
                <p>
                  Target: <code>{analysis.targeted_node}</code> · {affectedComponents.length}{' '}
                  affected component{affectedComponents.length === 1 ? '' : 's'}
                </p>
              </div>

              <div className="graph-legend">
                {['Low', 'Medium', 'High', 'Critical'].map((level) => (
                  <span key={level} className="legend-item">
                    <span
                      className="legend-dot"
                      style={{ backgroundColor: getRiskColor(level) }}
                    />
                    {level}
                  </span>
                ))}
                <span className="legend-item">
                  <span className="legend-dot legend-dot--target" />
                  Target node
                </span>
              </div>

              <div className="graph-wrapper" ref={graphWrapperRef}>
                <ImpactGraph analysis={analysis} width={graphSize.width} height={graphSize.height} />
              </div>
            </section>

            <div className="results-chat-layout">
              <section className="panel results-panel">
                <div className="panel__header">
                  <h2>Affected components</h2>
                  <p>Sorted by hop distance from the change target</p>
                </div>

                <div className="component-list">
                  {[...affectedComponents]
                    .sort((a, b) => (a.hop_distance ?? 99) - (b.hop_distance ?? 99))
                    .map((component) => (
                      <ComponentCard
                        key={component.node_id}
                        component={component}
                        mitigation={mitigationMap[component.node_id]}
                      />
                    ))}
                </div>
              </section>

              <section className="panel chat-panel" aria-label="Analysis follow-up chat">
                <div className="panel__header">
                  <h2>Ask about this analysis</h2>
                  <p>Answers are grounded in the current graph and incident history.</p>
                </div>

                <div className="chat-history" ref={chatHistoryRef} aria-live="polite">
                  {chatHistory.length === 0 ? (
                    <p className="chat-history__empty">
                      Ask about a component, incident, dependency, or what-if scenario.
                    </p>
                  ) : (
                    chatHistory.map((message, index) => (
                      <div key={`${message.role}-${index}`} className={`chat-message chat-message--${message.role}`}>
                        <span className="chat-message__role">{message.role === 'user' ? 'You' : 'Analyzer'}</span>
                        <p>{message.content}</p>
                      </div>
                    ))
                  )}
                  {chatLoading && (
                    <div className="chat-message chat-message--assistant chat-message--loading">
                      <Loader2 className="spin" aria-hidden="true" />
                      <span>Checking the graph and incident history...</span>
                    </div>
                  )}
                </div>

                {chatError && <p className="chat-error" role="alert">{chatError}</p>}

                <form className="chat-form" onSubmit={handleChatSubmit}>
                  <label className="sr-only" htmlFor="chat-message">Follow-up question</label>
                  <input
                    id="chat-message"
                    value={chatMessage}
                    onChange={(event) => setChatMessage(event.target.value)}
                    placeholder="e.g. What could affect payment-service?"
                    disabled={chatLoading}
                  />
                  <button type="submit" className="btn btn-primary" disabled={chatLoading || !chatMessage.trim()}>
                    <Send className="btn__icon" aria-hidden="true" />
                    Send
                  </button>
                </form>
              </section>
            </div>
          </>
        )}
        </div>
      </main>
    </div>
  )
}
