import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    fs: { strict: false },
    proxy: {
      '/catalog': 'http://localhost:8000',
      '/cart': 'http://localhost:8000',
      '/checkout': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/tools': 'http://localhost:8000',
      '/orders': 'http://localhost:8000'
    }
  }
})
