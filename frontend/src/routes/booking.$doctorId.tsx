import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { ArrowLeft, CalendarDays, Clock, User as UserIcon, Stethoscope } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { RatingStars } from '@/components/shared/rating-stars'
import { CategoryBadge } from '@/components/shared/category-badge'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { requireAuth } from '@/lib/guards'
import { databaseApi, hospitalsApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/booking/$doctorId')({
  beforeLoad: () => requireAuth(),
  component: BookingPage,
})

interface Slot {
  date: string // YYYY-MM-DD
  time: string // HH:MM
  label: string
  iso: string
}

function generateSlots(): { dayLabel: string; slots: Slot[] }[] {
  const days: { dayLabel: string; slots: Slot[] }[] = []
  const now = new Date()

  for (let d = 0; d < 7; d++) {
    const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() + d)
    const dayLabel = day.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
    const slots: Slot[] = []
    for (let h = 9; h <= 17; h++) {
      const iso = new Date(
        day.getFullYear(),
        day.getMonth(),
        day.getDate(),
        h,
        0,
      )
      if (iso.getTime() <= now.getTime()) continue
      slots.push({
        date: `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`,
        time: `${String(h).padStart(2, '0')}:00`,
        label: `${String(h).padStart(2, '0')}:00`,
        iso: iso.toISOString(),
      })
    }
    if (slots.length > 0) days.push({ dayLabel, slots })
  }
  return days
}

function BookingPage() {
  const { doctorId } = Route.useParams()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const doctor = useQuery({
    queryKey: ['doctor', Number(doctorId)],
    queryFn: () => databaseApi.getDoctor(Number(doctorId)),
  })
  const hospital = useQuery({
    queryKey: ['hospital', doctor.data?.hospital_id],
    queryFn: () => hospitalsApi.get(doctor.data!.hospital_id),
    enabled: doctor.data != null,
  })

  const days = useMemo(generateSlots, [])
  const [selected, setSelected] = useState<Slot | null>(null)

  const book = useMutation({
    mutationFn: async () => {
      if (!selected || !user) return
      return databaseApi.createAppointment({
        user_id: user.id,
        hospital_id: doctor.data?.hospital_id,
        doctor_id: Number(doctorId),
        status: 'scheduled',
        scheduled_at: selected.iso,
      })
    },
    onSuccess: (appointment) => {
      if (!appointment) return
      toast.success('Slot booked! Proceed to payment.')
      navigate({ to: '/payment/$appointmentId', params: { appointmentId: String(appointment.id) } })
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Booking failed'),
  })

  if (doctor.isPending || (doctor.data && hospital.isPending)) return <PageLoader />
  if (doctor.isError || !doctor.data)
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <EmptyState title="Doctor not found" />
      </div>
    )

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <Button variant="ghost" size="sm" className="mb-4" render={<Link to="/leaderboard" />}>
        <ArrowLeft className="size-4" /> Back
      </Button>

      <Card>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-secondary">
            <Stethoscope className="size-6 text-primary" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-semibold">{doctor.data.full_name}</h1>
              <CategoryBadge categoryId={doctor.data.medical_category_id} />
            </div>
            <p className="text-sm text-muted-foreground">
              {hospital.data?.name} · {hospital.data?.city}
            </p>
            <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <UserIcon className="size-3.5" /> {doctor.data.experience_years} yrs exp.
              </span>
              <RatingStars value={doctor.data.rating_avg} />
            </div>
          </div>
          <Badge variant="secondary" className="shrink-0">
            Consultation fee set by the clinic
          </Badge>
        </CardContent>
      </Card>

      <h2 className="mt-8 mb-3 flex items-center gap-2 text-lg font-semibold">
        <CalendarDays className="size-5 text-primary" /> Choose a slot
      </h2>
      <div className="space-y-4">
        {days.map((day) => (
          <div key={day.dayLabel}>
            <p className="mb-2 text-sm font-medium text-muted-foreground">{day.dayLabel}</p>
            <div className="flex flex-wrap gap-2">
              {day.slots.map((slot) => (
                <button
                  key={slot.iso}
                  type="button"
                  onClick={() => setSelected(slot)}
                  className={cn(
                    'flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm font-medium transition-colors',
                    selected?.iso === slot.iso
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-input hover:border-ring hover:bg-muted',
                  )}
                >
                  <Clock className="size-3.5" />
                  {slot.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="sticky bottom-4 mt-8 flex items-center justify-between gap-4 rounded-2xl border bg-background/95 p-4 shadow-lg backdrop-blur">
        <div>
          <p className="text-sm text-muted-foreground">Selected slot</p>
          <p className="font-medium">
            {selected ? (
              <>
                {new Date(selected.iso).toLocaleString('en-GB', {
                  weekday: 'short',
                  day: 'numeric',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </>
            ) : (
              'Not selected'
            )}
          </p>
        </div>
        <Button size="lg" disabled={!selected || book.isPending} onClick={() => book.mutate()}>
          {book.isPending ? 'Booking…' : 'Continue to payment'}
        </Button>
      </div>
    </div>
  )
}
