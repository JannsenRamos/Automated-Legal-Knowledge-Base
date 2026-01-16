import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { serverConfig } from './frontend/vite.server.config.js'

export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_PATH || "/Automated-Legal-Knowledge-Base",
  server: serverConfig
})