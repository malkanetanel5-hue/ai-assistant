import { useEffect, useState } from 'react'
import AuthPanel from './components/AuthPanel'
import CalendarSidebar from './components/CalendarSidebar'
import ChatPanel from './components/ChatPanel'
import './App.css'

const API = ''

// Reactive media query hook
function useIsMobile() {
  const [mobile, setMobile] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches
  )
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 767px)')
    const handler = (e) => setMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])
  return mobile
}

// Persistent boolean (survives page reload)
function usePersistentBool(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      const s = localStorage.getItem(key)
      return s !== null ? s === 'true' : defaultValue
    } catch { return defaultValue }
  })
  function set(next) {
    const v = typeof next === 'function' ? next(value) : next
    setValue(v)
    try { localStorage.setItem(key, String(v)) } catch {}
  }
  return [value, set]
}

function StatusDot({ ok }) {
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: ok ? 'var(--green)' : 'var(--red)',
      marginRight: 6, flexShrink: 0,
      boxShadow: ok ? '0 0 5px var(--green)' : '0 0 5px var(--red)',
    }} />
  )
}

const DESKTOP_VIEWS = ['Chat', 'Calendar', 'Settings']
const MOBILE_VIEWS  = ['Chat', 'Schedule', 'More']  // "More" holds auth + settings on mobile

export default function App() {
  const isMobile = useIsMobile()
  const [backendOk, setBackendOk]         = useState(null)
  const [isAuthenticated, setIsAuth]      = useState(false)
  const [view, setView]                   = useState('Chat')
  const [calOpen, setCalOpen]             = usePersistentBool('cal-sidebar-open', true)
  const [pinned, setPinned]               = usePersistentBool('window-pinned', false)
  const [showMobileAuth, setShowMobileAuth] = useState(false)

  useEffect(() => {
    async function ping() {
      try { await fetch(`${API}/health`); setBackendOk(true) }
      catch { setBackendOk(false) }
    }
    ping()
    const id = setInterval(ping, 15_000)
    return () => clearInterval(id)
  }, [])

  async function handlePinToggle() {
    if (window.electronAPI?.toggleAlwaysOnTop) {
      const next = await window.electronAPI.toggleAlwaysOnTop()
      setPinned(next)
    } else {
      setPinned((v) => !v)
    }
  }

  // ── Desktop layout ────────────────────────────────────────────────────────
  if (!isMobile) {
    return (
      <div className="layout">
        <aside className="sidebar">
          <div className="logo">
            AI Assistant
            <button
              className={`pin-btn${pinned ? ' pin-btn--active' : ''}`}
              onClick={handlePinToggle}
              title={pinned ? 'Unpin window' : 'Pin window on top'}
            >📌</button>
          </div>

          <nav className="nav">
            {DESKTOP_VIEWS.map((v) => (
              <button
                key={v}
                className={`nav-item${view === v ? ' active' : ''}`}
                onClick={() => setView(v)}
              >
                {{ Chat: '💬', Calendar: '📅', Settings: '⚙️' }[v]} {v}
              </button>
            ))}
          </nav>

          <div className="sidebar-footer">
            <AuthPanel onAuthChange={setIsAuth} />
            <div className="status-pill">
              <StatusDot ok={backendOk === true} />
              {backendOk === null ? 'Connecting…' : backendOk ? 'Online' : 'Backend offline'}
            </div>
          </div>
        </aside>

        <main className="main">
          <header className="topbar">
            <h1 className="page-title">{view}</h1>
            {view === 'Chat' && (
              <button
                className={`btn-icon${calOpen ? ' btn-icon--active' : ''}`}
                title={calOpen ? 'Hide schedule' : 'Show schedule'}
                onClick={() => setCalOpen((v) => !v)}
              >📅</button>
            )}
          </header>

          <div className="content-area">
            <div className="content">
              {view === 'Chat'     && <ChatPanel isAuthenticated={isAuthenticated} />}
              {view === 'Calendar' && <CalendarSidebar isAuthenticated={isAuthenticated} fullscreen />}
              {view === 'Settings' && (
                <div className="placeholder">
                  <span style={{ fontSize: 40 }}>⚙️</span>
                  <p>Settings — coming in Phase 4</p>
                </div>
              )}
            </div>

            {view === 'Chat' && calOpen && (
              <CalendarSidebar isAuthenticated={isAuthenticated} />
            )}
          </div>
        </main>
      </div>
    )
  }

  // ── Mobile layout ─────────────────────────────────────────────────────────
  return (
    <div className="layout layout--mobile">
      {/* Slim top bar */}
      <header className="topbar topbar--mobile">
        <span className="logo-mobile">AI Assistant</span>
        <div className="topbar-right">
          <StatusDot ok={backendOk === true} />
          {isAuthenticated
            ? <span className="auth-badge auth-badge--ok">Google ✓</span>
            : <button className="auth-badge" onClick={() => { setView('More'); setShowMobileAuth(true) }}>
                Connect Google
              </button>
          }
        </div>
      </header>

      {/* Main content area */}
      <main className="mobile-content">
        {view === 'Chat'     && <ChatPanel isAuthenticated={isAuthenticated} />}
        {view === 'Schedule' && <CalendarSidebar isAuthenticated={isAuthenticated} fullscreen />}
        {view === 'More'     && (
          <div className="mobile-more">
            <h2 className="more-title">Account & Settings</h2>
            <AuthPanel onAuthChange={setIsAuth} />
            <div className="status-pill" style={{ marginTop: 12 }}>
              <StatusDot ok={backendOk === true} />
              {backendOk === null ? 'Connecting…' : backendOk ? 'Backend online' : 'Backend offline'}
            </div>
            <p className="muted" style={{ marginTop: 20, fontSize: 12 }}>
              Full settings panel coming in Phase 4.
            </p>
          </div>
        )}
      </main>

      {/* Bottom navigation bar */}
      <nav className="bottom-nav">
        {[
          { id: 'Chat',     icon: '💬', label: 'Chat' },
          { id: 'Schedule', icon: '📅', label: 'Schedule' },
          { id: 'More',     icon: '⚙️', label: 'More' },
        ].map(({ id, icon, label }) => (
          <button
            key={id}
            className={`bottom-nav-item${view === id ? ' active' : ''}`}
            onClick={() => setView(id)}
          >
            <span className="bottom-nav-icon">{icon}</span>
            <span className="bottom-nav-label">{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
