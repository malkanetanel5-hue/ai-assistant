const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  toggleAlwaysOnTop: () => ipcRenderer.invoke('toggle-always-on-top'),
  // Opens a URL in the OS default browser — used for Google OAuth
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
})
