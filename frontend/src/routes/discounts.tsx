import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { TicketPercent, Copy, Check, CalendarX, Lock } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { requireAuth } from '@/lib/guards'
import { databaseApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { copyToClipboard, formatDate } from '@/lib/format'

export const Route = createFileRoute('/discounts')({
  beforeLoad: () => requireAuth(),
  component: DiscountsPage,
})

function DiscountsPage() {
  const user = useAuthStore((s) => s.user)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const { data, isPending, isError } = useQuery({
    queryKey: ['discounts', user?.id],
    queryFn: () => databaseApi.listDiscounts({ user_id: user?.id, limit: 100 }),
    enabled: Boolean(user),
  })

  const discounts = data ?? []

  const copy = async (discount: (typeof discounts)[number]) => {
    await copyToClipboard(discount.code)
    setCopiedId(discount.id)
    setTimeout(() => setCopiedId(null), 2000)
    toast.success('Discount code copied')
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center gap-3">
        <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <TicketPercent className="size-5" />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">My discounts</h1>
          <p className="text-sm text-muted-foreground">
            Reward codes you earned by sharing feedback after visits.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {isPending ? (
          <div className="col-span-full">
            <PageLoader />
          </div>
        ) : isError ? (
          <EmptyState title="Could not load discounts" />
        ) : discounts.length === 0 ? (
          <div className="col-span-full">
            <EmptyState
              title="No discounts yet"
              description="Leave feedback after your next visit to earn a discount code."
            />
          </div>
        ) : (
          discounts.map((discount) => {
            const expired = discount.expires_at && new Date(discount.expires_at) < new Date()
            return (
              <Card
                key={discount.id}
                className={discount.is_used || expired ? 'opacity-70' : ''}
              >
                <CardContent className="flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">{discount.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {discount.percent_off}% off your next booking
                      </p>
                    </div>
                    <Badge
                      variant={
                        discount.is_used || expired
                          ? 'secondary'
                          : 'default'
                      }
                      className="shrink-0"
                    >
                      {discount.is_used ? 'Used' : expired ? 'Expired' : 'Active'}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between gap-2 rounded-lg bg-secondary px-3 py-2">
                    <span className="font-mono text-base font-semibold tracking-wider">
                      {discount.code}
                    </span>
                    <Button
                      size="icon-sm"
                      variant="ghost"
                      onClick={() => copy(discount)}
                      disabled={discount.is_used || Boolean(expired)}
                      aria-label="Copy code"
                    >
                      {copiedId === discount.id ? (
                        <Check className="size-4 text-emerald-500" />
                      ) : discount.is_used || expired ? (
                        <Lock className="size-4" />
                      ) : (
                        <Copy className="size-4" />
                      )}
                    </Button>
                  </div>

                  {discount.expires_at && (
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                      <CalendarX className="size-3.5" /> Expires {formatDate(discount.expires_at)}
                    </p>
                  )}
                </CardContent>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
