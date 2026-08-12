export type UserRole = 'patient' | 'staff' | 'admin'

export interface User {
  id: number
  full_name: string
  username: string | null
  phone: string | null
  email: string | null
  role: UserRole
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Hospital {
  id: number
  name: string
  address: string
  city: string
  lat: number
  lng: number
  rating_avg: number
  created_at: string
  phone_numbers?: string[]
  working_hours?: Record<string, string>
}

export interface DoctorSummary {
  id: number
  hospital_id: number
  medical_category_id: number
  full_name: string
  experience_years: number
  rating_avg: number
}

export interface HospitalDetail extends Hospital {
  phone_numbers: string[]
  working_hours: Record<string, string>
  doctors: DoctorSummary[]
}

export interface HospitalLeaderboardEntry {
  rank: number
  id: number
  name: string
  city: string
  rating_avg: number
  weighted_score: number
}

export interface MedicalCategory {
  id: number
  name: string
}

export type AppointmentStatus = 'scheduled' | 'completed' | 'cancelled'

export interface Appointment {
  id: number
  user_id: number
  hospital_id: number | null
  doctor_id: number | null
  queue_number: number | null
  status: AppointmentStatus
  scheduled_at: string
  created_at: string
}

/** Same shape as Appointment — the queue service backs onto the appointments table. */
export type QueueEntry = Appointment

export interface Notification {
  id: number
  user_id: number
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export type PaymentProvider = 'stripe' | 'payme' | 'uzum'

export interface PaymentDetail {
  id: number
  user_id: number
  appointment_id: number
  provider: PaymentProvider
  external_id: string | null
  amount: number
  currency: string
  status: string
  created_at: string
  updated_at: string
}

export interface CheckoutResponse {
  payment_id: number
  provider: PaymentProvider
  checkout_url: string | null
  token: string | null
}

export interface Discount {
  id: number
  user_id: number
  title: string
  code: string
  percent_off: number
  expires_at: string | null
  is_used: boolean
  created_at: string
}

export type FeedbackSentiment = 'positive' | 'neutral' | 'negative'
export type FeedbackProcessingStatus = 'pending' | 'processing' | 'done' | 'failed'

export interface FeedbackAnswer {
  question_id: number
  question: string
  rating: number | null
  comment: string | null
}

export interface Feedback {
  id: number
  user_id: number
  appointment_id: number
  hospital_id: number | null
  doctor_id: number | null
  category_id: number | null
  rating: number | null
  tags: string[]
  text_comment: string | null
  answers: FeedbackAnswer[]
  audio_file: string | null
  transcript: string | null
  sentiment: FeedbackSentiment | null
  processing_status: FeedbackProcessingStatus
  created_at: string
}

export interface FeedbackTranscript {
  id: number
  transcript: string | null
  sentiment: FeedbackSentiment | null
  keywords: string[] | null
  processing_status: FeedbackProcessingStatus
}

export interface AuditLogEntry {
  id: number
  actor_id: number
  action: string
  entity: string
  entity_id: number | null
  created_at: string
}

export interface StatsOverview {
  users_count: number
  appointments_count: number
  feedback_count: number
  revenue: number
}

export interface CategoryVisitStat {
  category_id: number
  category_name: string
  visit_count: number
}

export type SortOption = 'rating' | 'distance'
