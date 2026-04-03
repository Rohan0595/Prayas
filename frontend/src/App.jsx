import { useState, useEffect, useRef, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import Sidebar from './components/Sidebar'
import Message from './components/Message'
import UploadModal from './components/UploadModal'
import AuthModal from './components/AuthModal'
import {
  listSessions, createSession, deleteSession,
  getSessionMessages, streamChat, getUploadStatus,
  logout
} from './services/api'
import './styles/main.css'

const MODELS = [
  { value: 'auto', label: '✦ Auto-route' },
  // ── Groq (fast) ──────────────────────────────
  { value: 'groq/llama-3.1-8b-instant', label: '⚡ Llama 3.1 8B (Groq)' },
  { value: 'groq/llama-3.3-70b-versatile', label: '⚡ Llama 3.3 70B (Groq)' },
  { value: 'groq/mixtral-8x7b-32768', label: '⚡ Mixtral 8x7B (Groq)' },
  { value: 'groq/gemma2-9b-it', label: '⚡ Gemma 2 9B (Groq)' },
  // ── Gemini ────────────────────────────────────
  { value: 'gemini/gemini-2.0-flash', label: '✦ Gemini 2.0 Flash' },
  { value: 'gemini/gemini-1.5-flash', label: '✦ Gemini 1.5 Flash' },
  { value: 'gemini/gemini-1.5-pro', label: '✦ Gemini 1.5 Pro' },
]

const EXAMPLE_PROMPTS = [
  'Write a Python function to parse JSON with error handling',
  'Explain quantum entanglement simply',
  'What are the key differences between REST and GraphQL?',
  'Help me debug this React useEffect issue',
]

export default function App() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState('auto')
  const [useAgent, setUseAgent] = useState(false)
  const [useRag, setUseRag] = useState(true)
  const [docCount, setDocCount] = useState(0)
  const [showUpload, setShowUpload] = useState(false)
  const [streamingMsgId, setStreamingMsgId] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [userEmail, setUserEmail] = useState('')

  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const abortRef = useRef(null)

  // ── Scroll to bottom on new messages ──────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Load sessions on mount ─────────────────────────────────────────────────
  useEffect(() => {
    const token = localStorage.getItem('omni_token')
    if (token) {
      setIsAuthenticated(true)
      setUserEmail(localStorage.getItem('omni_user_email') || '')
      loadSessions()
      loadDocStatus()
    }
  }, [])

  const handleLogout = async () => {
    try { await logout() } catch {}
    localStorage.removeItem('omni_token')
    localStorage.removeItem('omni_user_email')
    setIsAuthenticated(false)
    setSessions([])
    setMessages([])
    setActiveSessionId(null)
  }

  const loadSessions = async () => {
    try {
      const data = await listSessions()
      setSessions(data)
    } catch { /* first run — no sessions yet */ }
  }

  const loadDocStatus = async () => {
    try {
      const status = await getUploadStatus()
      setDocCount(status.indexed_chunks)
    } catch { }
  }

  // ── Select a session and load its messages ─────────────────────────────────
  const selectSession = useCallback(async (id) => {
    setActiveSessionId(id)
    try {
      const data = await getSessionMessages(id)
      setMessages(
        data.messages.map((m, i) => ({
          id: i,
          role: m.role,
          content: m.content,
          model: m.model,
        }))
      )
    } catch {
      setMessages([])
    }
  }, [])

  // ── New chat ───────────────────────────────────────────────────────────────
  const handleNewChat = useCallback(() => {
    setActiveSessionId(null)
    setMessages([])
    setInput('')
    textareaRef.current?.focus()
  }, [])

  // ── Delete session ─────────────────────────────────────────────────────────
  const handleDeleteSession = useCallback(async (id) => {
    await deleteSession(id)
    setSessions((prev) => prev.filter((s) => s.id !== id))
    if (id === activeSessionId) {
      setActiveSessionId(null)
      setMessages([])
    }
  }, [activeSessionId])

  // ── Send message ───────────────────────────────────────────────────────────
  const sendMessage = useCallback(async (text) => {
    const trimmed = (text || input).trim()
    if (!trimmed || isLoading) return

    setInput('')
    setIsLoading(true)

    // Optimistically add user message
    const userMsgId = uuidv4()
    setMessages((prev) => [...prev, { id: userMsgId, role: 'user', content: trimmed }])

    // Placeholder for streaming assistant message
    const asstMsgId = uuidv4()
    setMessages((prev) => [...prev, { id: asstMsgId, role: 'assistant', content: '', model: '' }])
    setStreamingMsgId(asstMsgId)

    let resolvedSessionId = activeSessionId
    let modelUsed = selectedModel === 'auto' ? '' : selectedModel

    // Cancel any previous stream
    abortRef.current?.abort()

    abortRef.current = streamChat({
      message: trimmed,
      sessionId: resolvedSessionId,
      model: selectedModel,
      useAgent,
      useRag,
      onMeta: (meta) => {
        // Backend tells us the session_id and chosen model
        const parsed = typeof meta === 'string' ? JSON.parse(meta) : meta
        resolvedSessionId = parsed.session_id
        modelUsed = parsed.model
        setActiveSessionId(parsed.session_id)

        // Update model label in the streaming message
        setMessages((prev) =>
          prev.map((m) => m.id === asstMsgId ? { ...m, model: parsed.model } : m)
        )

        // Refresh session list to show new session
        loadSessions()
      },
      onChunk: (chunk) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId ? { ...m, content: m.content + chunk } : m
          )
        )
      },
      onDone: () => {
        setIsLoading(false)
        setStreamingMsgId(null)
        loadSessions() // refresh title
      },
      onError: (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId
              ? { ...m, content: `⚠️ Error: ${err}` }
              : m
          )
        )
        setIsLoading(false)
        setStreamingMsgId(null)
      },
    })
  }, [input, isLoading, activeSessionId, selectedModel, useAgent, useRag])

  // ── Textarea key handler ───────────────────────────────────────────────────
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ── Auto-resize textarea ───────────────────────────────────────────────────
  const handleInputChange = (e) => {
    setInput(e.target.value)
    const ta = e.target
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'
  }

  if (!isAuthenticated) {
    return <AuthModal onAuthSuccess={(data) => {
      setIsAuthenticated(true)
      setUserEmail(data.email)
      loadSessions()
      loadDocStatus()
    }} />
  }

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        activeModel={selectedModel}
      />

      <div className="main">
        {/* ── Topbar ─── */}
        <div className="topbar">
          <div className="topbar-left">
            <select
              className="model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {MODELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            <button className="btn-ghost" style={{ padding: '6px 10px', fontSize: 11 }} onClick={handleLogout}>
              Logout ({userEmail})
            </button>
          </div>
          <div className="topbar-toggles">
            <button
              className={`toggle-chip ${useAgent ? 'active' : ''}`}
              onClick={() => setUseAgent((v) => !v)}
              title="Enable tool-use agent loop"
            >
              🔧 Agent
            </button>
            <button
              className={`toggle-chip ${useRag ? 'active' : ''}`}
              onClick={() => setUseRag((v) => !v)}
              title="Use uploaded documents as context"
            >
              📚 RAG
              {docCount > 0 && (
                <span className="doc-count">({docCount})</span>
              )}
            </button>
          </div>
        </div>

        {/* ── Messages ─── */}
        <div className="messages-container">
          <div className="messages-inner">
            {messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">✦</div>
                <div className="empty-title">Prayāsa</div>
                <div className="empty-subtitle">
                  Multi-model AI with RAG, tool use, and streaming. Pick a model above or let auto-routing choose.
                </div>
                <div className="example-prompts">
                  {EXAMPLE_PROMPTS.map((p) => (
                    <button
                      key={p}
                      className="example-prompt"
                      onClick={() => sendMessage(p)}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <Message
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  model={msg.model}
                  isStreaming={msg.id === streamingMsgId}
                />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ── Input ─── */}
        <div className="input-area">
          <div className="input-wrapper">
            <div className="input-box">
              <textarea
                ref={textareaRef}
                className="input-textarea"
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Message Prayāsa…"
                rows={1}
                disabled={isLoading}
              />
              <div className="input-actions">
                <button
                  className="upload-btn"
                  onClick={() => setShowUpload(true)}
                  title="Upload document for RAG"
                >
                  📎
                </button>
                <button
                  className="send-btn"
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || isLoading}
                  title="Send (Enter)"
                >
                  {isLoading ? '⏸' : '↑'}
                </button>
              </div>
            </div>
            <div className="input-hint">
              <span><kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for newline</span>
              <span style={{ opacity: 0.5 }}>·</span>
              <span>Powered by LiteLLM · Groq · Gemini</span>
            </div>
          </div>
        </div>
      </div>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={(result) => {
            // Called after a successful upload — update count and close
            if (result.total_chunks >= 0) setDocCount(result.total_chunks)
            setShowUpload(false)
          }}
          onDocCountChange={(count) => {
            // Called after delete — just refresh count, keep modal open
            setDocCount(count)
          }}
        />
      )}
    </div>
  )
}
