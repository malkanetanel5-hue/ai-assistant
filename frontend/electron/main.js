const { app, BrowserWindow, ipcMain, shell, Tray, Menu, nativeImage } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

const isDev = process.env.NODE_ENV !== 'production'
const VITE_URL = 'http://localhost:5173'
const BACKEND_PORT = process.env.BACKEND_PORT || 8000

let mainWindow = null
let backendProcess = null

// ── Backend lifecycle ────────────────────────────────────────────────────────

function startBackend() {
  const backendDir = path.join(__dirname, '..', '..', 'backend')
  const python = process.platform === 'win32' ? 'python' : 'python3'

  backendProcess = spawn(python, ['-m', 'uvicorn', 'main:app', '--port', BACKEND_PORT, '--reload'], {
    cwd: backendDir,
    env: { ...process.env },
    stdio: 'pipe',
  })

  backendProcess.stdout.on('data', (d) => console.log('[backend]', d.toString().trim()))
  backendProcess.stderr.on('data', (d) => console.error('[backend]', d.toString().trim()))
  backendProcess.on('exit', (code) => console.log(`[backend] exited with code ${code}`))
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
}

// ── Window ───────────────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 800,
    minHeight: 500,
    alwaysOnTop: false,         // flip to true for a persistent overlay
    frame: true,
    backgroundColor: '#0f1117',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev) {
    mainWindow.loadURL(VITE_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => { mainWindow = null })
}

// ── IPC handlers ─────────────────────────────────────────────────────────────

ipcMain.handle('get-backend-url', () => `http://localhost:${BACKEND_PORT}`)

// Open a URL in the user's default browser (used for Google OAuth consent screen)
ipcMain.handle('open-external', (_event, url) => shell.openExternal(url))

ipcMain.handle('toggle-always-on-top', () => {
  if (!mainWindow) return false
  const next = !mainWindow.isAlwaysOnTop()
  mainWindow.setAlwaysOnTop(next)
  return next
})

// ── App events ───────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  if (isDev) {
    // In dev the user runs the backend manually; skip auto-spawn to avoid conflicts
    console.log('[electron] Dev mode: expecting backend already running on', BACKEND_PORT)
  } else {
    startBackend()
  }
  createWindow()
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.on('before-quit', stopBackend)
