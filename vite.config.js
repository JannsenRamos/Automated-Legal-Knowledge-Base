import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { serverConfig } from './vite.server.config.js'

export default defineConfig({
  plugins: [react()],
  server: serverConfig
})