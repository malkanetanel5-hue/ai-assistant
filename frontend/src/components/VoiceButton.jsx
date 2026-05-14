import { useRef, useState } from 'react'

const API = ''

// Detect the best supported audio MIME type for the current browser/OS.
// iOS Safari supports audio/mp4 (AAC); Chrome/Firefox prefer webm/opus.
function bestMimeType() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',          // iOS Safari 14.3+
    'audio/ogg;codecs=opus',
    '',                   // browser default
  ]
  return candidates.find((t) => !t || MediaRecorder.isTypeSupported(t)) ?? ''
}

// Map MIME type → file extension for the Whisper API upload
function ext(mime) {
  if (mime.includes('mp4')) return '.mp4'
  if (mime.includes('ogg')) return '.ogg'
  return '.webm'
}

export default function VoiceButton({ onTranscript, disabled }) {
  const [state, setState] = useState('idle') // 'idle' | 'recording' | 'transcribing'
  const recorderRef = useRef(null)
  const chunksRef   = useRef([])
  const streamRef   = useRef(null)
  const mimeRef     = useRef('')

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
      alert('Your browser does not support microphone access.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current  = stream
      chunksRef.current  = []
      mimeRef.current    = bestMimeType()

      const mr = new MediaRecorder(stream, mimeRef.current ? { mimeType: mimeRef.current } : undefined)
      recorderRef.current = mr

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = async () => {
        streamRef.current?.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: mimeRef.current || 'audio/webm' })
        await transcribe(blob)
      }

      mr.start(200)
      setState('recording')
    } catch (err) {
      console.error('Mic error:', err)
      // On mobile, a friendlier prompt — alert is synchronous so it won't be
      // silenced by iOS's gesture-activation requirement
      alert('Microphone access was denied. Please allow it in your browser settings and try again.')
    }
  }

  function stopRecording() {
    recorderRef.current?.stop()
    setState('transcribing')
  }

  async function transcribe(blob) {
    try {
      const filename = `recording${ext(mimeRef.current)}`
      const form = new FormData()
      form.append('audio', blob, filename)

      const res = await fetch(`${API}/voice/transcribe`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        console.error('Transcription error:', err.detail)
        return
      }
      const data = await res.json()
      if (data.transcript?.trim()) onTranscript(data.transcript.trim())
    } catch (err) {
      console.error('Transcription fetch failed:', err)
    } finally {
      setState('idle')
    }
  }

  function handleClick() {
    if (state === 'idle')      startRecording()
    else if (state === 'recording') stopRecording()
    // 'transcribing' — ignore, show spinner
  }

  const label = { idle: '🎙', recording: '⏹', transcribing: '…' }[state]
  const title = {
    idle:         'Tap to record voice input',
    recording:    'Tap to stop and transcribe',
    transcribing: 'Transcribing…',
  }[state]

  return (
    <button
      className={`btn-mic btn-mic--${state}`}
      onClick={handleClick}
      disabled={disabled || state === 'transcribing'}
      title={title}
      aria-label={title}
    >
      {label}
    </button>
  )
}
