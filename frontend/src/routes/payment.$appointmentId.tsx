import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { CreditCard, ShieldCheck, CheckCircle2, ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { requireAuth } from '@/lib/guards'
import { databaseApi } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/payment/$appointmentId')({
  beforeLoad: () => requireAuth(),
  component: PaymentPage,
})

interface Provider {
  id: string
  name: string
  tagline: string
  color: string
}

const PROVIDERS: Provider[] = [
  { id: 'payme', name: 'Payme', tagline: 'Pay by phone number', color: 'bg-[#33b5e5]' },
  { id: 'click', name: 'Click', tagline: 'Pay by invoice', color: 'bg-[#ffd200]' },
  { id: 'uzum', name: 'Uzum Bank', tagline: 'Pay by app', color: 'bg-[#7000ff]' },
]

function PaymentPage() {
  const { appointmentId } = Route.useParams()
  const [provider, setProvider] = useState<Provider | null>(null)
  const [status, setStatus] = useState<'select' | 'processing' | 'done'>('select')

  const appointment = useQuery({
    queryKey: ['appointment', Number(appointmentId)],
    queryFn: () => databaseApi.getAppointment(Number(appointmentId)),
  })

  const startPayment = (p: Provider) => {
    setProvider(p)
    setStatus('processing')
    setTimeout(() => setStatus('done'), 1800)
  }

  if (appointment.isPending) return <PageLoader />
  if (appointment.isError || !appointment.data)
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <EmptyState title="Appointment not found" />
      </div>
    )

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <Button variant="ghost" size="sm" className="mb-4" render={<Link to="/profile/appointments" />}>
        <ArrowLeft className="size-4" /> My appointments
      </Button>

      {status === 'done' ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <CheckCircle2 className="size-14 text-emerald-500" />
            <h1 className="text-xl font-semibold">Payment successful</h1>
            <p className="max-w-sm text-sm text-muted-foreground">
              Your queue slot on {formatDateTime(appointment.data.scheduled_at)} is reserved via{' '}
              {provider?.name}. In production this redirects to the provider's hosted checkout
              (PayTechUZ) so your card data never touches MedByte.
            </p>
            <div className="mt-2 flex gap-2">
              <Button render={<Link to="/profile/appointments" />}>View appointment</Button>
              <Button variant="outline" render={<Link to="/discounts" />}>
                My discounts
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="mb-6 flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <CreditCard className="size-5" />
            </span>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Payment</h1>
              <p className="text-sm text-muted-foreground">
                Booking for {formatDateTime(appointment.data.scheduled_at)}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => startPayment(p)}
                disabled={status === 'processing'}
                className={cn(
                  'flex w-full items-center gap-4 rounded-xl border p-4 text-left transition-colors',
                  'hover:border-ring hover:bg-muted/50',
                  provider?.id === p.id && 'border-primary ring-1 ring-primary',
                  status === 'processing' && 'opacity-60',
                )}
              >
                <span
                  className={cn(
                    'flex size-10 shrink-0 items-center justify-center rounded-lg font-bold text-white',
                    p.color,
                  )}
                >
                  {p.name[0]}
                </span>
                <div className="flex-1">
                  <p className="font-medium">{p.name}</p>
                  <p className="text-sm text-muted-foreground">{p.tagline}</p>
                </div>
                {provider?.id === p.id && status === 'processing' ? (
                  <Badge variant="secondary">Connecting…</Badge>
                ) : (
                  <Badge variant="outline">Select</Badge>
                )}
              </button>
            ))}
          </div>

          <div className="mt-6 flex items-start gap-2 rounded-xl bg-muted p-3 text-sm text-muted-foreground">
            <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
            <p>
              Payment is processed by the selected provider's hosted checkout. Card details are never
              stored on MedByte servers. A reminder to leave feedback is sent 1–2 hours after your
              visit.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
