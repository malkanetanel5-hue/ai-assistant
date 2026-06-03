import { useEffect, useState } from 'react'

// Relative URLs — Vite proxies to :8000 in dev; same-origin in production
const API = 'https://web-production-82d03.up.railway.app'

export default function AuthPanel({ onAuthChange, compact = false }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function fetchStatus() {
    try {
      const res = await fetch(`${API}/auth/status`)
      const data = await res.json()
      setStatus(data)
      onAuthChange?.(data.authenticated)
    } catch {
      setStatus({ authenticated: false, email: null })
      onAuthChange?.(false)
    }
  }

  async function handleLogin() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/auth/login`)
      if (!res.ok) {
        const err = await res.json()
        setError(err.error || 'Failed to start OAuth flow')
        setLoading(false)
        return
      }
      const { auth_url } = await res.json()
      // Works in Electron (shell.openExternal), plain browser, and mobile
      if (window.electronAPI?.openExternal) {
        window.electronAPI.openExternal(auth_url)
      } else {
        window.open(auth_url, '_blank', 'noopener')
      }
      // Poll until Google finishes the OAuth redirect
      const interval = setInterval(async () => {
        try {
          const r = await fetch(`${API}/auth/status`)
          const d = await r.json()
          if (d.authenticated) {
            clearInterval(interval)
            setStatus(d)
            onAuthChange?.(true)
            setLoading(false)
          }
        } catch {}
      }, 2000)
      setTimeout(() => { clearInterval(interval); setLoading(false) }, 180_000)
    } catch {
      setError('Could not reach the server.')
      setLoading(false)
    }
  }

  async function handleLogout() {
    await fetch(`${API}/auth/logout`, { method: 'POST' })
    setStatus({ authenticated: false, email: null })
    onAuthChange?.(false)
  }

  useEffect(() => {
    // Detect redirect back from Google OAuth
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') === 'success') {
      window.history.replaceState({}, '', '/')
    }
    fetchStatus()
  }, [])

  if (!status) return <p className="muted">Checking Google auth…</p>

  if (status.authenticated) {
    return (
      <div className={`auth-panel auth-panel--ok${compact ? ' auth-panel--compact' : ''}`}>
        <div className="auth-row">
          <span className="auth-dot auth-dot--green" />
          <span className="auth-label">
            {compact ? 'Google connected' : (status.email || 'Google connected')}
          </span>
        </div>
        {!compact && (
          <button className="btn btn--ghost btn--sm" onClick={handleLogout}>
            Disconnect
          </button>
        )}
      </div>
    )
  }

  return (
    <div className={`auth-panel${compact ? ' auth-panel--compact' : ''}`}>
      {!compact && (
        <p className="muted" style={{ marginBottom: 10 }}>
          Connect Google to enable Calendar and Gmail.
        </p>
      )}
      {error && <p className="auth-error">{error}</p>}
      <button className="btn" onClick={handleLogin} disabled={loading}>
        {loading ? 'Waiting for sign-in…' : 'Connect Google'}
      </button>
      {loading && !compact && (
        <p className="muted" style={{ marginTop: 8, fontSize: 11 }}>
          Complete sign-in in the new tab, then return here.
        </p>
      )}
    </div>
  )
}
