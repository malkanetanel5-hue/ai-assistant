import { useEffect, useRef, useState } from 'react'
import VoiceButton from './VoiceButton'

const API = 'https://web-production-82d03.up.railway.app'

const SUGGESTIONS = [
  "What's on my calendar today?",
  'Show my latest unread emails',
  'Search the web for the latest AI news',
  'Schedule a 30-min call with team@example.com tomorrow at 2pm',
]

function Message({ role, content }) {
  return (
    <div className={`msg msg--${role}`}>
      <span className="msg-label">{role === 'user' ? 'You' : 'Assistant'}</span>
      <div className="msg-bubble">{content}</div>
    </div>
  )
}

export default function ChatPanel({ isAuthenticated }) {
  const [history, setHistory]   = useState([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const bottomRef  = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  async function send(overrideText) {
    const text = (overrideText ?? input).trim()
    if (!text || loading) return
    setInput('')
    setError('')
    const userMsg = { role: 'user', content: text }
    setHistory((h) => [...h, userMsg])
    setLoading(true)

    try {
      const res = await fetch(`${API}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(
          res.status === 401
            ? 'Google not connected — tap "Connect Google" first.'
            : data.detail || 'Something went wrong.'
        )
        return
      }
      setHistory((h) => [...h, { role: 'assistant', content: data.response }])
    } catch {
      setError('Could not reach the server. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    // On desktop Enter sends; on mobile Shift+Enter is natural so don't hijack
    if (e.key === 'Enter' && !e.shiftKey && !('ontouchstart' in window)) {
      e.preventDefault()
      send()
    }
  }

  function handleVoiceTranscript(transcript) {
    setInput((prev) => (prev ? `${prev} ${transcript}` : transcript))
    textareaRef.current?.focus()
  }

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {history.length === 0 && (
          <div className="chat-empty">
            <p className="chat-empty-title">Your AI assistant is ready.</p>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((m, i) => <Message key={i} role={m.role} content={m.content} />)}

        {loading && (
          <div className="msg msg--assistant">
            <span className="msg-label">Assistant</span>
            <div className="msg-bubble msg-bubble--loading">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}

        {error && <p className="chat-error">{error}</p>}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <VoiceButton onTranscript={handleVoiceTranscript} disabled={loading} />
        <textarea
          ref={textareaRef}
          className="chat-input"
          rows={2}
          placeholder={isAuthenticated ? 'Ask anything — or tap 🎙 to speak…' : 'Connect Google first…'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button
          className="btn chat-send"
          onClick={() => send()}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  )
}
