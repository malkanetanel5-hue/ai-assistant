import { useCallback, useEffect, useState } from 'react'

const API = ''
const REFRESH_MS = 60_000

function timeLabel(iso) {
  if (!iso) return ''
  if (!iso.includes('T')) {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function dateLabel(iso) {
  if (!iso) return ''
  const d = iso.includes('T') ? new Date(iso) : new Date(iso + 'T00:00:00')
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

function urgencyClass(iso) {
  if (!iso || !iso.includes('T')) return ''
  const diff = new Date(iso) - Date.now()
  if (diff < 0) return 'event--past'
  if (diff < 15 * 60_000) return 'event--imminent'
  if (diff < 60 * 60_000) return 'event--soon'
  return ''
}

function groupByDay(events) {
  const groups = {}
  for (const e of events) {
    const key = dateLabel(e.start)
    if (!groups[key]) groups[key] = []
    groups[key].push(e)
  }
  return groups
}

// fullscreen prop: true when shown as the main content on mobile "Schedule" tab
export default function CalendarSidebar({ isAuthenticated, fullscreen = false }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchEvents = useCallback(async () => {
    if (!isAuthenticated) return
    setLoading(true)
    try {
      const res = await fetch(`${API}/calendar/events?max_results=15`)
      if (!res.ok) return
      const data = await res.json()
      setEvents(data.events || [])
      setLastUpdated(new Date())
    } catch {}
    finally { setLoading(false) }
  }, [isAuthenticated])

  useEffect(() => {
    fetchEvents()
    const id = setInterval(fetchEvents, REFRESH_MS)
    return () => clearInterval(id)
  }, [fetchEvents])

  const groups = groupByDay(events)

  return (
    <aside className={`cal-sidebar${fullscreen ? ' cal-sidebar--full' : ''}`}>
      <div className="cal-header">
        <span className="cal-title">Schedule</span>
        <button className="cal-refresh" onClick={fetchEvents} disabled={loading} title="Refresh">
          {loading ? '…' : '↺'}
        </button>
      </div>

      <div className="cal-body">
        {!isAuthenticated && (
          <p className="cal-empty">Connect Google to see your schedule.</p>
        )}
        {isAuthenticated && !loading && events.length === 0 && (
          <p className="cal-empty">No upcoming events.</p>
        )}

        {Object.entries(groups).map(([day, dayEvents]) => (
          <div key={day} className="cal-day-group">
            <div className="cal-day-label">{day}</div>
            {dayEvents.map((e) => (
              <a
                key={e.id}
                className={`cal-event ${urgencyClass(e.start)}`}
                href={e.htmlLink || '#'}
                target="_blank"
                rel="noreferrer"
                title={e.description || e.summary}
              >
                <span className="cal-event-time">{timeLabel(e.start)}</span>
                <span className="cal-event-title">{e.summary}</span>
                {e.attendees?.length > 0 && (
                  <span className="cal-event-guests">
                    {e.attendees.length} guest{e.attendees.length > 1 ? 's' : ''}
                  </span>
                )}
              </a>
            ))}
          </div>
        ))}

        {lastUpdated && (
          <p className="cal-updated">
            Updated {lastUpdated.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </aside>
  )
}
