import { redirect } from '@tanstack/react-router'
import { useAuthStore } from '@/stores/auth'

export function requireAuth() {
  if (!useAuthStore.getState().token) {
    throw redirect({ to: '/login' })
  }
}

export function requireAdmin() {
  const { token, user } = useAuthStore.getState()
  if (!token) throw redirect({ to: '/login' })
  if (user?.role !== 'admin') throw redirect({ to: '/' })
}
