import { createFileRoute, Link } from '@tanstack/react-router'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { CreditCard, ShieldCheck, ArrowLeft, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { requireAuth } from '@/lib/guards'
import { databaseApi, paymentApi } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { PaymentProvider } from '@/lib/types'

export const Route = createFileRoute('/payment/$appointmentId')({
  beforeLoad: () => requireAuth(),
  component: PaymentPage,
})

interface Provider {
  id: PaymentProvider
  name: string
  tagline: string
  color: string
  test?: boolean
}

const PROVIDERS: Provider[] = [
  { id: 'stripe', name: 'Stripe', tagline: 'Hosted Stripe Checkout (test mode)', color: 'bg-[#635bff]', test: true },
  { id: 'payme', name: 'Payme', tagline: 'Pay by phone number', color: 'bg-[#33b5e5]' },
  { id: 'uzum', name: 'Uzum Bank', tagline: 'Pay by app', color: 'bg-[#7000ff]' },
]

function PaymentPage() {
  const { appointmentId } = Route.useParams()
  const [provider, setProvider] = useState<Provider | null>(null)

  const appointment = useQuery({
    queryKey: ['appointment', Number(appointmentId)],
    queryFn: () => databaseApi.getAppointment(Number(appointmentId)),
  })

  const checkout = useMutation({
    mutationFn: (p: Provider) =>
      paymentApi.checkout({ appointment_id: Number(appointmentId), provider: p.id }),
    onSuccess: (data, p) => {
      if (data.checkout_url) {
        window.location.assign(data.checkout_url)
        return
      }
      toast.error(`${p.name} checkout returned no URL`)
      setProvider(null)
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Checkout failed')
      setProvider(null)
    },
  })

  const startPayment = (p: Provider) => {
    if (p.id !== 'stripe') {
      toast.info(`${p.name} checkout is not implemented in this demo yet — use the Stripe test checkout`)
      return
    }
    setProvider(p)
    checkout.mutate(p)
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
            disabled={checkout.isPending}
            className={cn(
              'flex w-full items-center gap-4 rounded-xl border p-4 text-left transition-colors',
              'hover:border-ring hover:bg-muted/50',
              provider?.id === p.id && 'border-primary ring-1 ring-primary',
              checkout.isPending && 'opacity-60',
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
              <div className="flex items-center gap-2">
                <p className="font-medium">{p.name}</p>
                {p.test && <Badge variant="secondary">Test mode</Badge>}
              </div>
              <p className="text-sm text-muted-foreground">{p.tagline}</p>
            </div>
            {provider?.id === p.id && checkout.isPending ? (
              <Badge variant="secondary">
                <Loader2 className="size-3 animate-spin" /> Redirecting…
              </Badge>
            ) : (
              <Badge variant="outline">Select</Badge>
            )}
          </button>
        ))}
      </div>

      <div className="mt-6 flex items-start gap-2 rounded-xl bg-muted p-3 text-sm text-muted-foreground">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
        <p>
          Stripe uses its hosted Checkout — your card data never touches MedByte servers. Payme and
          Uzum Bank are placeholders. A reminder to leave feedback is sent 1–2 hours after your
          visit.
        </p>
      </div>
    </div>
  )
}
