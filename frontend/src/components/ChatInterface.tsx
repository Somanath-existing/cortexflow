'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import AgentTrace, { type Step } from './AgentTrace'
import ChartDisplay from './ChartDisplay'
import SourceCitations from './SourceCitations'
import { createWebSocket } from '@/lib/websocket'
import type { Source } from '@/lib/websocket'

interface Message {
  role: 'user' | 'assistant' | 'error'
  content: string
  sources?: Source[]
  chartData?: string | null
  agentSteps?: Step[]
}

const SUGGESTIONS = [
  'Why did revenue decline in Kerala last quarter?',
  'Compare Kerala vs Karnataka revenue in Q3 2024 vs Q3 2023',
  'Which customers have the highest churn risk?',
  'What product categories are most at risk in Kerala?',
]

function formatAnswer(text: string) {
  // Convert **bold** markdown to <strong>
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    // Convert bullet lines
    if (part.startsWith('- ') || part.startsWith('• ')) {
      return <span key={i}>{part}</span>
    }
    return <span key={i}>{part}</span>
  })
}

function AssistantMessage({ msg }: { msg: Message }) {
  const lines = msg.content.split('\n')

  return (
    <div className="space-y-1 text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
      {lines.map((line, i) => {
        if (line.startsWith('**') && line.endsWith('**')) {
          return (
            <p key={i} className="font-semibold mt-3 first:mt-0">
              {line.slice(2, -2)}
            </p>
          )
        }
        if (line.startsWith('- ') || line.startsWith('• ')) {
          return (
            <div key={i} className="flex gap-2 ml-2">
              <span style={{ color: 'var(--accent-blue)' }}>·</span>
              <span>{formatAnswer(line.slice(2))}</span>
            </div>
          )
        }
        if (line.trim() === '') return <div key={i} className="h-1" />
        return <p key={i}>{formatAnswer(line)}</p>
      })}
    </div>
  )
}

interface ChatInterfaceProps {
  initialQuery?: string
}

export default function ChatInterface({ initialQuery = '' }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState(initialQuery)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (initialQuery) {
      setInput(initialQuery)
    }
  }, [initialQuery])
  const [liveSteps, setLiveSteps] = useState<Step[]>([])
  const [connected, setConnected] = useState(false)
  const [pendingApproval, setPendingApproval] = useState<{ prompt: string; step: number } | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const sessionId = useRef(`session-${Date.now()}-${Math.random().toString(36).slice(2)}`)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleApproval = useCallback((approved: boolean) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({
      type: 'approval_response',
      action: approved ? 'approve' : 'reject',
      approved,
    }))
    setPendingApproval(null)
    setIsLoading(true)
  }, [])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, liveSteps, scrollToBottom])

  useEffect(() => {
    let ws: WebSocket
    let reconnectTimeout: ReturnType<typeof setTimeout>

    function connect() {
      ws = createWebSocket(sessionId.current)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)

      ws.onclose = () => {
        setConnected(false)
        // Reconnect after 2s if not intentionally closed
        reconnectTimeout = setTimeout(connect, 2000)
      }

      ws.onerror = () => {
        setConnected(false)
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)

        if (data.type === 'status') {
          setLiveSteps((prev) => [...prev, { type: 'status', message: data.message }])
        } else if (data.type === 'agent_step') {
          setLiveSteps((prev) => [
            ...prev,
            { type: 'agent_step', node: data.node, data: data.data },
          ])
        } else if (data.type === 'final_answer') {
          const capturedSteps = [...liveStepsRef.current]
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: data.answer,
              sources: data.sources,
              chartData: data.chart_data,
              agentSteps: capturedSteps,
            },
          ])
          setIsLoading(false)
          setPendingApproval(null)
          setLiveSteps([])
        } else if (data.type === 'approval_required') {
          setPendingApproval({
            prompt: data.prompt,
            step: data.step,
          })
          setIsLoading(false)
        } else if (data.type === 'error') {
          setMessages((prev) => [
            ...prev,
            { role: 'error', content: data.message },
          ])
          setIsLoading(false)
          setPendingApproval(null)
          setLiveSteps([])
        }
      }
    }

    connect()

    return () => {
      clearTimeout(reconnectTimeout)
      ws?.close()
    }
  }, [])

  // Keep a ref to liveSteps so the ws.onmessage closure can read current value
  const liveStepsRef = useRef<Step[]>([])
  useEffect(() => {
    liveStepsRef.current = liveSteps
  }, [liveSteps])

  const sendMessage = useCallback(() => {
    const query = input.trim()
    if (!query || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    setMessages((prev) => [...prev, { role: 'user', content: query }])
    setIsLoading(true)
    setLiveSteps([])
    wsRef.current.send(JSON.stringify({ query }))
    setInput('')
    inputRef.current?.focus()
  }, [input])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const showTrace = isLoading && liveSteps.length > 0

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ backgroundColor: 'var(--bg-base)' }}
    >
      {/* ── Main column ── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header
          className="flex items-center gap-3 px-5 py-3 border-b shrink-0"
          style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-base shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))' }}
          >
            🧠
          </div>
          <div>
            <h1 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
              CortexFlow
            </h1>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Autonomous Enterprise Data Worker
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: connected ? 'var(--accent-green)' : 'var(--accent-red)' }}
            />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {connected ? 'Connected' : 'Reconnecting…'}
            </span>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-6 pb-10">
              <div className="text-center space-y-2">
                <div className="text-4xl">🔍</div>
                <p className="text-base font-medium" style={{ color: 'var(--text-primary)' }}>
                  Ask about your business data
                </p>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  CortexFlow plans, queries, researches, and synthesises — all autonomously.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => { setInput(s); inputRef.current?.focus() }}
                    className="text-left px-4 py-3 rounded-xl text-sm transition-colors"
                    style={{
                      backgroundColor: 'var(--bg-raised)',
                      color: 'var(--text-muted)',
                      border: '1px solid var(--border)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--accent-blue)'
                      e.currentTarget.style.color = 'var(--text-primary)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border)'
                      e.currentTarget.style.color = 'var(--text-muted)'
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'user' ? (
                <div
                  className="max-w-[72%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm"
                  style={{
                    background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))',
                    color: '#fff',
                  }}
                >
                  {msg.content}
                </div>
              ) : msg.role === 'error' ? (
                <div
                  className="max-w-[80%] px-4 py-3 rounded-2xl rounded-tl-sm text-sm"
                  style={{
                    backgroundColor: 'var(--bg-raised)',
                    border: '1px solid var(--accent-red)',
                    color: 'var(--accent-red)',
                  }}
                >
                  ⚠️ {msg.content}
                </div>
              ) : (
                <div
                  className="max-w-[80%] px-4 py-4 rounded-2xl rounded-tl-sm"
                  style={{
                    backgroundColor: 'var(--bg-raised)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <AssistantMessage msg={msg} />
                  {msg.chartData && <ChartDisplay chartJson={msg.chartData} />}
                  {msg.sources && msg.sources.length > 0 && (
                    <SourceCitations sources={msg.sources} />
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Live agent trace inline */}
          {showTrace && (
            <div className="flex justify-start">
              <div
                className="max-w-[80%] w-full px-4 py-4 rounded-2xl rounded-tl-sm"
                style={{
                  backgroundColor: 'var(--bg-raised)',
                  border: '1px solid var(--border)',
                }}
              >
                <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-muted)' }}>
                  Working…
                </p>
                <AgentTrace steps={liveSteps} isLive={true} />
              </div>
            </div>
          )}

          {/* Human-in-the-Loop Approval Card */}
          {pendingApproval && (
            <div className="flex justify-start my-2">
              <div
                className="max-w-[85%] w-full p-5 rounded-2xl border shadow-xl"
                style={{
                  backgroundColor: 'var(--bg-raised)',
                  borderColor: '#f59e0b',
                  boxShadow: '0 8px 30px rgba(245, 158, 11, 0.15)',
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">🛡️</span>
                  <h4 className="text-sm font-semibold" style={{ color: '#f59e0b' }}>
                    Human Authorization Required
                  </h4>
                </div>
                <p className="text-sm mb-4 leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                  {pendingApproval.prompt}
                </p>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleApproval(true)}
                    className="px-4 py-2 text-xs font-semibold rounded-lg text-white transition-all transform hover:scale-105 shadow-md"
                    style={{
                      background: 'linear-gradient(135deg, #10b981, #059669)',
                    }}
                  >
                    ✓ Authorize & Proceed
                  </button>
                  <button
                    onClick={() => handleApproval(false)}
                    className="px-4 py-2 text-xs font-semibold rounded-lg border transition-all hover:bg-red-500/10"
                    style={{
                      borderColor: '#ef4444',
                      color: '#ef4444',
                    }}
                  >
                    ✕ Decline Request
                  </button>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div
          className="px-4 py-3 border-t shrink-0"
          style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}
        >
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your business data…"
              rows={1}
              disabled={isLoading || !connected}
              className="flex-1 resize-none rounded-xl px-4 py-3 text-sm outline-none transition-colors"
              style={{
                backgroundColor: 'var(--bg-raised)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
                maxHeight: '120px',
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent-blue)' }}
              onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)' }}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim() || !connected}
              className="rounded-xl px-4 py-3 text-sm font-medium transition-opacity shrink-0"
              style={{
                background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))',
                color: '#fff',
                opacity: isLoading || !input.trim() || !connected ? 0.45 : 1,
              }}
            >
              {isLoading ? '⏳' : '→'}
            </button>
          </div>
          <p className="text-xs mt-1 ml-1" style={{ color: 'var(--text-muted)' }}>
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>

      {/* ── Trace sidebar (visible only while loading) ── */}
      {showTrace && (
        <aside
          className="w-72 border-l overflow-y-auto p-4 shrink-0 hidden lg:block"
          style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}
        >
          <p
            className="text-xs font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'var(--text-muted)' }}
          >
            Agent Reasoning
          </p>
          <AgentTrace steps={liveSteps} isLive={true} />
        </aside>
      )}
    </div>
  )
}
