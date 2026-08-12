import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  CreditCard,
  MapPin,
  Stethoscope,
  Ticket,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { CategoryBadge } from '@/components/shared/category-badge'
import { requireAuth } from '@/lib/guards'
import { databaseApi, hospitalsApi, paymentApi } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { PaymentDetail } from '@/lib/types'

interface PaymentSuccessSearch {
  session_id?: string
}

export const Route = createFileRoute('/payment/success')({
  validateSearch: (search: Record<string, unknown>): PaymentSuccessSearch => ({
    session_id: typeof search.session_id === 'string' ? search.session_id : undefined,
  }),
  beforeLoad: () => requireAuth(),
  component: PaymentSuccessPage,
})

const PROVIDER_NAMES: Record<string, string> = {
  stripe: 'Stripe',
  payme: 'Payme',
  uzum: 'Uzum Bank',
}

function formatAmount(amount: number, currency: string): string {
  return `${(amount / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency.toUpperCase()}`
}

function statusBadge(payment: PaymentDetail) {
  if (payment.status === 'paid')
    return <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">Paid</Badge>
  if (payment.status === 'failed' || payment.status === 'cancelled')
    return <Badge variant="destructive">{payment.status}</Badge>
  return <Badge variant="secondary">Pending</Badge>
}

function PaymentSuccessPage() {
  const { session_id } = Route.useSearch()

  const payment = useQuery({
    queryKey: ['payment', 'session', session_id],
    queryFn: () => paymentApi.getBySession(session_id!),
    enabled: Boolean(session_id),
    retry: false,
  })

  const paid = payment.data?.status === 'paid'

  const appointment = useQuery({
    queryKey: ['appointment', payment.data?.appointment_id],
    queryFn: () => databaseApi.getAppointment(payment.data!.appointment_id),
    enabled: payment.data != null,
    refetchInterval: (query) => (paid && !query.state.data?.queue_number ? 2500 : false),
  })

  const hospital = useQuery({
    queryKey: ['hospital', appointment.data?.hospital_id],
    queryFn: () => hospitalsApi.get(appointment.data!.hospital_id!),
    enabled: appointment.data?.hospital_id != null,
  })

  const doctor = useQuery({
    queryKey: ['doctor', appointment.data?.doctor_id],
    queryFn: () => databaseApi.getDoctor(appointment.data!.doctor_id!),
    enabled: appointment.data?.doctor_id != null,
  })

  if (!session_id)
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <EmptyState title="Payment link incomplete" description="Missing Stripe session ID." />
      </div>
    )

  if (payment.isPending) return <PageLoader />
  if (payment.isError || !payment.data)
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <EmptyState title="Payment not found" description="No payment matches this session." />
      </div>
    )

  const queueNumber = appointment.data?.queue_number ?? null

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Button variant="ghost" size="sm" className="mb-4" render={<Link to="/profile/appointments" />}>
        <ArrowLeft className="size-4" /> My appointments
      </Button>

      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
          {paid ? (
            <>
              <span className="flex size-16 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-500/20">
                <CheckCircle2 className="size-9 text-emerald-500" />
              </span>
              <h1 className="text-2xl font-semibold tracking-tight">Payment successful</h1>
              <p className="max-w-md text-sm text-muted-foreground">
                Your booking is confirmed. Show your queue ticket at the hospital entrance.
              </p>
            </>
          ) : (
            <>
              <span className="flex size-16 items-center justify-center rounded-full bg-secondary">
                <CreditCard className="size-9 text-primary" />
              </span>
              <h1 className="text-2xl font-semibold tracking-tight">Payment {payment.data.status}</h1>
              <p className="max-w-md text-sm text-muted-foreground">
                Your payment has not been completed yet.
              </p>
              <Button
                render={
                  <Link
                    to="/payment/$appointmentId"
                    params={{ appointmentId: String(payment.data.appointment_id) }}
                  />
                }
              >
                <CreditCard className="size-4" /> Pay now
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {paid && (
        <Card className="mt-4 border-primary/30 bg-primary/[0.04]">
          <CardContent className="flex items-center gap-4 py-6">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Ticket className="size-6" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-muted-foreground">Your queue number</p>
              {queueNumber != null ? (
                <p className="text-3xl font-bold tracking-tight text-primary">#{queueNumber}</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Assigning your queue number…
                  <span className="ml-2 inline-block animate-pulse">…</span>
                </p>
              )}
            </div>
            {doctor.data && (
              <div className="hidden text-right sm:block">
                <p className="text-sm font-medium">{doctor.data.full_name}</p>
                <CategoryBadge categoryId={doctor.data.medical_category_id} />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="space-y-3 py-5">
            <div className="flex items-center gap-2">
              <CreditCard className="size-4 text-primary" />
              <h2 className="font-semibold">Payment</h2>
            </div>
            <DetailRow label="Amount" value={formatAmount(payment.data.amount, payment.data.currency)} />
            <DetailRow label="Provider" value={PROVIDER_NAMES[payment.data.provider] ?? payment.data.provider} />
            <DetailRow label="Status" value={undefined} custom={statusBadge(payment.data)} />
            <DetailRow label="Payment ID" value={`#${payment.data.id}`} />
            <DetailRow label="Session" value={payment.data.external_id ?? session_id} mono />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 py-5">
            <div className="flex items-center gap-2">
              <CalendarDays className="size-4 text-primary" />
              <h2 className="font-semibold">Appointment</h2>
            </div>
            {appointment.isPending ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : appointment.data ? (
              <>
                <DetailRow
                  label="Doctor"
                  value={doctor.data?.full_name ?? '—'}
                  custom={doctor.data ? <CategoryBadge categoryId={doctor.data.medical_category_id} /> : undefined}
                />
                <DetailRow label="Hospital" value={hospital.data?.name ?? '—'} />
                <DetailRow
                  label="Address"
                  value={
                    hospital.data ? (
                      <span className="flex items-center gap-1">
                        <MapPin className="size-3.5 shrink-0 text-muted-foreground" />
                        {hospital.data.address}, {hospital.data.city}
                      </span>
                    ) : (
                      '—'
                    )
                  }
                />
                <DetailRow label="Date & time" value={formatDateTime(appointment.data.scheduled_at)} />
                <DetailRow
                  label="Queue number"
                  value={appointment.data.queue_number != null ? `#${appointment.data.queue_number}` : 'Assigning…'}
                />
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Appointment details unavailable.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        <Button render={<Link to="/profile/appointments" />}>View appointments</Button>
        <Button variant="outline" render={<Link to="/notifications" />}>
          Notifications
        </Button>
        <Button variant="ghost" render={<Link to="/" />}>
          <Stethoscope className="size-4" /> Back to home
        </Button>
      </div>
    </div>
  )
}

function DetailRow({
  label,
  value,
  custom,
  mono,
}: {
  label: string
  value?: ReactNode
  custom?: ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      {custom ?? <span className={cn('text-right font-medium', mono && 'font-mono')}>{value ?? '—'}</span>}
    </div>
  )
}
