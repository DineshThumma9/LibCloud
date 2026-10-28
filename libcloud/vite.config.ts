import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/framecloud': 'http://localhost:8000',
      '/libcloud': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/s/': 'http://localhost:8000',
    },
  },
})
