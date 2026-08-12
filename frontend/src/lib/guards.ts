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

/** Allows staff and admin. Use for admin-section pages that staff should also reach. */
export function requireStaff() {
  const { token, user } = useAuthStore.getState()
  if (!token) throw redirect({ to: '/login' })
  if (user?.role !== 'staff' && user?.role !== 'admin') throw redirect({ to: '/' })
}
