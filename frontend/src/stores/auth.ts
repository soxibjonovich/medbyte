import { create } from 'zustand'
import type { User } from '@/lib/types'

interface AuthState {
  token: string | null
  user: User | null
  setSession: (token: string, user: User) => void
  setUser: (user: User) => void
  clearSession: () => void
}

const STORAGE_KEY = 'medbyte.session'

function loadSession(): { token: string | null; user: User | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { token: null, user: null }
    const parsed = JSON.parse(raw) as { token: string; user: User }
    return { token: parsed.token ?? null, user: parsed.user ?? null }
  } catch {
    return { token: null, user: null }
  }
}

const persisted = loadSession()

export const useAuthStore = create<AuthState>((set, get) => ({
  token: persisted.token,
  user: persisted.user,
  setSession: (token, user) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, user }))
    set({ token, user })
  },
  setUser: (user) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: get().token, user }))
    set({ user })
  },
  clearSession: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ token: null, user: null })
  },
}))

export const isAuthenticated = () => Boolean(useAuthStore.getState().token)
export const isAdmin = () => useAuthStore.getState().user?.role === 'admin'
export const isStaff = () => useAuthStore.getState().user?.role === 'staff'
export const isStaffOrAdmin = () => {
  const role = useAuthStore.getState().user?.role
  return role === 'staff' || role === 'admin'
}
