import { API } from './config'
import { useAuthStore } from '@/stores/auth'
import type {
  Appointment,
  AppointmentStatus,
  AuditLogEntry,
  CategoryVisitStat,
  Discount,
  DoctorSummary,
  Feedback,
  FeedbackSentiment,
  FeedbackTranscript,
  Hospital,
  HospitalDetail,
  HospitalLeaderboardEntry,
  MedicalCategory,
  Notification,
  SortOption,
  StatsOverview,
  TokenResponse,
  User,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type QueryParams = Record<string, string | number | boolean | null | undefined>

export function buildQuery(params?: QueryParams | object): string {
  if (!params) return ''
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') continue
    qs.set(key, String(value))
  }
  const s = qs.toString()
  return s ? `?${s}` : ''
}

async function apiFetch<T>(base: string, path: string, options: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().token
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${base}${path}`, { ...options, headers })

  if (!res.ok) {
    let message = res.statusText
    try {
      const data = await res.json()
      if (typeof data?.detail === 'string') message = data.detail
      else if (data?.detail) message = JSON.stringify(data.detail)
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(res.status, message)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/* ------------------------------------------------------------------ */
/* Auth                                                                */
/* ------------------------------------------------------------------ */

export const authApi = {
  register: (body: {
    full_name: string
    username: string
    phone?: string
    email?: string
    password: string
  }) => apiFetch<TokenResponse>(API.auth, '/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { username: string; password: string }) =>
    apiFetch<TokenResponse>(API.auth, '/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => apiFetch<User>(API.auth, '/me'),
}

/* ------------------------------------------------------------------ */
/* Public hospitals                                                    */
/* ------------------------------------------------------------------ */

export interface HospitalListParams {
  category?: number
  city?: string
  sort?: SortOption
  lat?: number
  lng?: number
  limit?: number
  offset?: number
}

export const hospitalsApi = {
  list: (params: HospitalListParams = {}) =>
    apiFetch<Hospital[]>(API.hospitals, `${buildQuery(params)}`),
  leaderboard: (category?: number) =>
    apiFetch<HospitalLeaderboardEntry[]>(
      API.hospitals,
      `/leaderboard${buildQuery({ category })}`,
    ),
  get: (id: number) => apiFetch<HospitalDetail>(API.hospitals, `/${id}`),
}

/* ------------------------------------------------------------------ */
/* Categories (public read via database service)                       */
/* ------------------------------------------------------------------ */

export const categoriesApi = {
  list: () => apiFetch<MedicalCategory[]>(API.database, '/medical-categories'),
}

/* ------------------------------------------------------------------ */
/* Database service (personal data + records)                          */
/* ------------------------------------------------------------------ */

export const databaseApi = {
  /* doctors */
  getDoctor: (id: number) => apiFetch<DoctorSummary>(API.database, `/doctors/${id}`),
  listDoctors: (params: { hospital_id?: number; category?: number } = {}) =>
    apiFetch<DoctorSummary[]>(API.database, `/doctors${buildQuery(params)}`),

  /* appointments */
  listAppointments: (params: { user_id?: number; limit?: number; offset?: number } = {}) =>
    apiFetch<Appointment[]>(API.database, `/appointments${buildQuery(params)}`),
  getAppointment: (id: number) => apiFetch<Appointment>(API.database, `/appointments/${id}`),
  createAppointment: (body: {
    user_id: number
    hospital_id?: number | null
    doctor_id?: number | null
    queue_number?: number | null
    status?: AppointmentStatus
    scheduled_at: string
  }) => apiFetch<Appointment>(API.database, '/appointments', { method: 'POST', body: JSON.stringify(body) }),
  updateAppointment: (id: number, body: { status?: AppointmentStatus; scheduled_at?: string }) =>
    apiFetch<Appointment>(API.database, `/appointments/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  /* notifications */
  listNotifications: (params: { user_id?: number; limit?: number; offset?: number } = {}) =>
    apiFetch<Notification[]>(API.database, `/notifications${buildQuery(params)}`),
  createNotification: (body: { user_id: number; title: string; message: string }) =>
    apiFetch<Notification>(API.database, '/notifications', { method: 'POST', body: JSON.stringify(body) }),
  markNotificationRead: (id: number) =>
    apiFetch<Notification>(API.database, `/notifications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_read: true }),
    }),

  /* discounts */
  listDiscounts: (params: { user_id?: number; limit?: number; offset?: number } = {}) =>
    apiFetch<Discount[]>(API.database, `/discounts${buildQuery(params)}`),

  /* feedback (user-scoped read) */
  listFeedback: (params: { user_id?: number; limit?: number; offset?: number } = {}) =>
    apiFetch<Feedback[]>(API.database, `/feedback${buildQuery(params)}`),

  /* users (admin management) */
  listUsers: (params: { limit?: number; offset?: number } = {}) =>
    apiFetch<User[]>(API.database, `/users${buildQuery(params)}`),
  updateUser: (id: number, body: Partial<Pick<User, 'full_name' | 'phone' | 'email' | 'role'>>) =>
    apiFetch<User>(API.database, `/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
}

/* ------------------------------------------------------------------ */
/* Admin service (stats, audit log, CRUD)                              */
/* ------------------------------------------------------------------ */

export interface DiscountCreateInput {
  user_id: number
  title: string
  code: string
  percent_off: number
  expires_at?: string | null
}

export interface HospitalCreateInput {
  name: string
  address: string
  city: string
  lat: number
  lng: number
  phone_numbers?: string[]
  working_hours?: Record<string, string>
}

export interface DoctorCreateInput {
  hospital_id: number
  medical_category_id: number
  full_name: string
  experience_years: number
}

export const adminApi = {
  /* stats */
  statsOverview: () => apiFetch<StatsOverview>(API.admin, '/stats/overview'),
  statsByCategory: (dateFrom?: string, dateTo?: string) =>
    apiFetch<CategoryVisitStat[]>(
      API.admin,
      `/stats/by-category${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  statsExportCsv: (filters: { from?: string; to?: string }) =>
    apiFetch<unknown>(
      API.admin,
      `/stats/export${buildQuery({ format: 'csv', filters: filters.from || filters.to ? JSON.stringify(filters) : undefined })}`,
    ),
  auditLog: (params: { limit?: number; offset?: number } = {}) =>
    apiFetch<AuditLogEntry[]>(API.admin, `/audit-log${buildQuery(params)}`),

  /* hospitals CRUD */
  listHospitals: (params: HospitalListParams = {}) =>
    apiFetch<Hospital[]>(API.admin, `/hospitals${buildQuery(params)}`),
  createHospital: (body: HospitalCreateInput) =>
    apiFetch<Hospital>(API.admin, '/hospitals', { method: 'POST', body: JSON.stringify(body) }),
  updateHospital: (id: number, body: Partial<HospitalCreateInput>) =>
    apiFetch<Hospital>(API.admin, `/hospitals/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteHospital: (id: number) => apiFetch<void>(API.admin, `/hospitals/${id}`, { method: 'DELETE' }),

  /* doctors CRUD */
  listDoctors: (params: { hospital_id?: number; category?: number; limit?: number; offset?: number } = {}) =>
    apiFetch<DoctorSummary[]>(API.admin, `/doctors${buildQuery(params)}`),
  createDoctor: (body: DoctorCreateInput) =>
    apiFetch<DoctorSummary>(API.admin, '/doctors', { method: 'POST', body: JSON.stringify(body) }),
  updateDoctor: (id: number, body: Partial<DoctorCreateInput>) =>
    apiFetch<DoctorSummary>(API.admin, `/doctors/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteDoctor: (id: number) => apiFetch<void>(API.admin, `/doctors/${id}`, { method: 'DELETE' }),

  /* categories CRUD */
  createCategory: (body: { name: string }) =>
    apiFetch<MedicalCategory>(API.admin, '/categories', { method: 'POST', body: JSON.stringify(body) }),
  updateCategory: (id: number, body: { name: string }) =>
    apiFetch<MedicalCategory>(API.admin, `/categories/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteCategory: (id: number) => apiFetch<void>(API.admin, `/categories/${id}`, { method: 'DELETE' }),

  /* discounts CRUD */
  listDiscounts: (params: { user_id?: number; limit?: number; offset?: number } = {}) =>
    apiFetch<Discount[]>(API.admin, `/discounts${buildQuery(params)}`),
  createDiscount: (body: DiscountCreateInput) =>
    apiFetch<Discount>(API.admin, '/discounts', { method: 'POST', body: JSON.stringify(body) }),
  updateDiscount: (id: number, body: { is_used: boolean }) =>
    apiFetch<Discount>(API.admin, `/discounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteDiscount: (id: number) => apiFetch<void>(API.admin, `/discounts/${id}`, { method: 'DELETE' }),
}

/* ------------------------------------------------------------------ */
/* AI service                                                          */
/* ------------------------------------------------------------------ */

export interface AIChatRequest {
  message: string
  conversation_id?: string | null
  user_geo?: string | null
}

export interface AIChatResponse {
  conversation_id: string | null
  reply: string
}

export const aiApi = {
  chat: (body: AIChatRequest) =>
    apiFetch<AIChatResponse>(API.ai, '/chat', { method: 'POST', body: JSON.stringify(body) }),
}

/* ------------------------------------------------------------------ */
/* Notifications service (in-app + web push)                           */
/* ------------------------------------------------------------------ */

export const notificationsApi = {
  send: (body: { title: string; message: string }) =>
    apiFetch<Notification>(API.notifications, '/send', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}

/* ------------------------------------------------------------------ */
/* Feedback service                                                    */
/* ------------------------------------------------------------------ */

export interface FeedbackSubmitInput {
  appointment_id: number
  rating: number
  tags?: string[]
  text_comment?: string | null
  audio_file?: File | null
}

export const feedbackApi = {
  submit: (input: FeedbackSubmitInput) => {
    const form = new FormData()
    form.append('appointment_id', String(input.appointment_id))
    form.append('rating', String(input.rating))
    for (const tag of input.tags ?? []) form.append('tags', tag)
    if (input.text_comment) form.append('text_comment', input.text_comment)
    if (input.audio_file) form.append('audio_file', input.audio_file)
    return apiFetch<Feedback>(API.feedback, '', { method: 'POST', body: form })
  },
  list: (params: {
    hospital_id?: number
    category_id?: number
    sentiment?: FeedbackSentiment
    date_from?: string
    date_to?: string
    limit?: number
    offset?: number
  } = {}) =>
    apiFetch<Feedback[]>(
      API.feedback,
      `${buildQuery(params)}`,
    ),
  get: (id: number) => apiFetch<Feedback>(API.feedback, `/${id}`),
  transcript: (id: number) => apiFetch<FeedbackTranscript>(API.feedback, `/${id}/transcript`),
}
