import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    strictPort: true,
    // In dev mode, proxy all API calls to the FastAPI backend.
    // This means every component can use relative URLs (/auth/status, /chat/, etc.)
    // and they work identically in dev (via this proxy) and production (same origin).
    proxy: {
      '/auth':     { target: 'http://localhost:8000', changeOrigin: true },
      '/calendar': { target: 'http://localhost:8000', changeOrigin: true },
      '/chat':     { target: 'http://localhost:8000', changeOrigin: true },
      '/gmail':    { target: 'http://localhost:8000', changeOrigin: true },
      '/voice':    { target: 'http://localhost:8000', changeOrigin: true },
      '/health':   { target: 'http://localhost:8000', changeOrigin: true },
    },
  },

  build: {
    // Output directly into the FastAPI static directory.
    // `npm run build` in frontend/ → FastAPI serves it at the root URL.
    outDir: '../backend/static',
    emptyOutDir: true,
  },
})
