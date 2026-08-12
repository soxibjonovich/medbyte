const env = import.meta.env

/**
 * Base URLs for the backend services. In development these are relative paths
 * that are proxied by Vite (see vite.config.ts). In production set the
 * VITE_*_API_URL env vars (or let Nginx route the relative paths).
 */
export const API = {
  auth: (env.VITE_AUTH_API_URL as string) ?? '/api/v1/auth',
  hospitals: (env.VITE_HOSPITALS_API_URL as string) ?? '/api/hospitals',
  feedback: (env.VITE_FEEDBACK_API_URL as string) ?? '/api/feedback',
  admin: (env.VITE_ADMIN_API_URL as string) ?? '/api/admin',
  database: (env.VITE_DATABASE_API_URL as string) ?? '/api/v1/database',
  ai: (env.VITE_AI_API_URL as string) ?? '/api/ai',
  notifications: (env.VITE_NOTIFICATIONS_API_URL as string) ?? '/api/notifications',
  queue: (env.VITE_QUEUE_API_URL as string) ?? '/api/queue',
  payment: (env.VITE_PAYMENT_API_URL as string) ?? '/api/payments',
}

/**
 * Resolves an API base + path to a ws:// or wss:// URL, mirroring the current
 * page's protocol (http -> ws, https -> wss). Works for both relative bases
 * (proxied by Vite/Nginx, resolved against the current origin) and absolute
 * http(s) bases (e.g. VITE_QUEUE_API_URL pointing at a standalone service).
 */
export function apiWsUrl(base: string, path: string): string {
  const url = new URL(`${base}${path}`, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

// Push notifications are removed from the frontend. Email/in-app notification delivery is still available via the backend notifications service.
