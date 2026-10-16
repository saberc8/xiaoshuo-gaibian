import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const apiUrl = loadEnv(mode, '..', 'NOVEL_').NOVEL_API_URL || 'http://127.0.0.1:8010'
  return { plugins: [react()], server: { proxy: { '/api': apiUrl } }, preview: { proxy: { '/api': apiUrl } } }
})
