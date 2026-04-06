import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: '..',  // Read .env from root directory
  server: {
    proxy: {
      '/api': {
        target: 'https://api.veto-net.org',
        changeOrigin: true,
      }
    }
  }
})
