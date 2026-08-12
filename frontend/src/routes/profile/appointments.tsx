import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Link } from '@tanstack/react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, MapPin, User as UserIcon, MessageSquarePlus, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { requireAuth } from '@/lib/guards'
import { databaseApi, hospitalsApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, isUpcoming } from '@/lib/format'
import type { Appointment, AppointmentStatus } from '@/lib/types'

export const Route = createFileRoute('/profile/appointments')({
  beforeLoad: () => requireAuth(),
  component: AppointmentsPage,
})

const STATUS_STYLES: Record<AppointmentStatus, { label: string; className: string }> = {
  scheduled: { label: 'Scheduled', className: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300' },
  completed: { label: 'Completed', className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' },
  cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300' },
}

function AppointmentsPage() {
  const user = useAuthStore((s) => s.user)
  const [tab, setTab] = useState<'upcoming' | 'past'>('upcoming')
  const queryClient = useQueryClient()

  const { data, isPending, isError } = useQuery({
    queryKey: ['appointments', user?.id],
    queryFn: () => databaseApi.listAppointments({ user_id: user?.id, limit: 100 }),
    enabled: Boolean(user),
  })

  const cancel = useMutation({
    mutationFn: (id: number) => databaseApi.updateAppointment(id, { status: 'cancelled' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      toast.success('Appointment cancelled')
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Cancel failed'),
  })

  const appointments = useMemo(() => data ?? [], [data])
  const upcoming = appointments.filter(isUpcoming)
  const past = appointments.filter((a) => !isUpcoming(a))
  const shown = tab === 'upcoming' ? upcoming : past

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">My appointments</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Your queue tickets — book, track, and review your visits.
      </p>

      <Tabs value={tab} onValueChange={(v) => setTab(v as 'upcoming' | 'past')} className="mt-6">
        <TabsList>
          <TabsTrigger value="upcoming">Upcoming ({upcoming.length})</TabsTrigger>
          <TabsTrigger value="past">Past ({past.length})</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="mt-6 space-y-3">
        {isPending ? (
          <PageLoader />
        ) : isError ? (
          <EmptyState title="Could not load appointments" />
        ) : shown.length === 0 ? (
          <EmptyState
            title={tab === 'upcoming' ? 'No upcoming appointments' : 'No past appointments'}
            description={
              tab === 'upcoming'
                ? 'Find a hospital and book your first queue slot.'
                : 'Completed visits will appear here.'
            }
          />
        ) : (
          shown.map((appointment) => (
            <AppointmentCard
              key={appointment.id}
              appointment={appointment}
              onCancel={() => cancel.mutate(appointment.id)}
              cancelling={cancel.isPending}
            />
          ))
        )}
      </div>
    </div>
  )
}

function AppointmentCard({
  appointment,
  onCancel,
  cancelling,
}: {
  appointment: Appointment
  onCancel: () => void
  cancelling: boolean
}) {
  const hospital = useQuery({
    queryKey: ['hospital', appointment.hospital_id],
    queryFn: () => hospitalsApi.get(appointment.hospital_id!),
    enabled: appointment.hospital_id != null,
  })
  const doctor = useQuery({
    queryKey: ['doctor', appointment.doctor_id],
    queryFn: () => databaseApi.getDoctor(appointment.doctor_id!),
    enabled: appointment.doctor_id != null,
  })

  const style = STATUS_STYLES[appointment.status]
  const canCancel = appointment.status === 'scheduled' && isUpcoming(appointment)

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-secondary">
          <CalendarDays className="size-5 text-primary" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium">
              {doctor.data?.full_name ?? 'Doctor'} at {hospital.data?.name ?? 'Hospital'}
            </p>
            <Badge className={style.className}>{style.label}</Badge>
          </div>
          <p className="mt-0.5 flex items-center gap-1 text-sm text-muted-foreground">
            <CalendarDays className="size-3.5" />
            {formatDateTime(appointment.scheduled_at)}
          </p>
          {hospital.data && (
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <MapPin className="size-3.5" />
              {hospital.data.address}
            </p>
          )}
          {doctor.data && (
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <UserIcon className="size-3.5" />
              {doctor.data.full_name}
            </p>
          )}
          {appointment.queue_number != null && (
            <p className="mt-1 text-sm">
              Queue number:{' '}
              <span className="font-semibold text-primary">#{appointment.queue_number}</span>
            </p>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          {appointment.status === 'completed' && (
            <Button
              size="sm"
              variant="secondary"
              render={
                <Link to="/feedback/$appointmentId" params={{ appointmentId: String(appointment.id) }} />
              }
            >
              <MessageSquarePlus className="size-4" /> Leave feedback
            </Button>
          )}
          {canCancel && (
            <Button size="sm" variant="outline" onClick={onCancel} disabled={cancelling}>
              <X className="size-4" /> Cancel
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
