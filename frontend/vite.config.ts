import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"
import fs from "node:fs"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from '@tanstack/router-plugin/vite'

const SERVICES = {
  auth: process.env.AUTH_API_URL || 'http://localhost:8004',
  hospitals: process.env.HOSPITALS_API_URL || 'http://localhost:8006',
  admin: process.env.ADMIN_API_URL || 'http://localhost:8007',
  feedback: process.env.FEEDBACK_API_URL || 'http://localhost:8008',
  database: process.env.DATABASE_API_URL || 'http://localhost:8005',
  ai: process.env.AI_API_URL || 'http://localhost:8011',
  notifications: process.env.NOTIFICATIONS_API_URL || 'http://localhost:8009',
}

// Self-signed TLS certs for LAN/mobile testing (needed for Web Push).
// Generate them with the script in certs/README.md — without them the server runs on HTTP.
const certDir = path.resolve(import.meta.dirname, 'certs')
const tlsKey = path.join(certDir, 'key.pem')
const tlsCert = path.join(certDir, 'cert.pem')
const hasTls = fs.existsSync(tlsKey) && fs.existsSync(tlsCert)

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    // Expose the dev server to the local network (bind to 0.0.0.0)
    // so other devices can open the site via http(s)://<LAN-IP>:5173
    host: true,
    https: hasTls ? { key: fs.readFileSync(tlsKey), cert: fs.readFileSync(tlsCert) } : undefined,
    proxy: {
      // auth service (port 8004)
      '/api/v1/auth': { target: SERVICES.auth, changeOrigin: true },
      // public hospitals read API (port 8006)
      '/api/hospitals': { target: SERVICES.hospitals, changeOrigin: true },
      // feedback service (port 8008)
      '/api/feedback': { target: SERVICES.feedback, changeOrigin: true },
      // admin service (port 8007) - CRUD routes are exposed at /api/hospitals|doctors|categories|discounts
      '/api/admin/hospitals': {
        target: SERVICES.admin,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/admin\/hospitals/, '/api/hospitals'),
      },
      '/api/admin/doctors': {
        target: SERVICES.admin,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/admin\/doctors/, '/api/doctors'),
      },
      '/api/admin/categories': {
        target: SERVICES.admin,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/admin\/categories/, '/api/categories'),
      },
      '/api/admin/discounts': {
        target: SERVICES.admin,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/admin\/discounts/, '/api/discounts'),
      },
      // admin service (port 8007) - stats + audit log
      '/api/admin': { target: SERVICES.admin, changeOrigin: true },
      // database service (port 8005) - appointments, notifications, discounts, users, categories
      '/api/v1/database': { target: SERVICES.database, changeOrigin: true },
      // ai service (port 8011) - chat + audio chat
      '/api/ai': { target: SERVICES.ai, changeOrigin: true },
      // notifications service (port 8009) - in-app + web push
      '/api/notifications': { target: SERVICES.notifications, changeOrigin: true },
    },
  },
})
