import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Base path for GitHub Pages deployment
  base: '/english-compiler/',
  // Required for Pyodide: SharedArrayBuffer needs cross-origin isolation
  server: {
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    },
  },
  // Optimize deps for Pyodide
  optimizeDeps: {
    exclude: ['pyodide'],
  },
  build: {
    // Ensure assets are properly handled
    assetsInlineLimit: 0,
  },
})
