import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const target = env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        '/api': { target, changeOrigin: true, ws: true },
        '/orders/': { target, changeOrigin: true },
        '/health': { target, changeOrigin: true },
        '/fleet/capacity': { target, changeOrigin: true },
      },
    },
  }
})
