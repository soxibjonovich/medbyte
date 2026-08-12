import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Users, CalendarDays, MessageSquare, Banknote, TrendingUp } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { adminApi } from '@/lib/api'
import { formatMoney } from '@/lib/format'

export const Route = createFileRoute('/admin/_admin/')({
  component: AdminOverviewPage,
})

function AdminOverviewPage() {
  const overview = useQuery({ queryKey: ['admin', 'stats'], queryFn: adminApi.statsOverview })
  const byCategory = useQuery({
    queryKey: ['admin', 'by-category'],
    queryFn: () => adminApi.statsByCategory(),
  })

  if (overview.isPending) return <PageLoader />

  const stats = overview.data
  const maxCategory = Math.max(1, ...(byCategory.data ?? []).map((c) => c.visit_count))

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Platform KPIs — operational and commercial analytics.
      </p>

      {overview.isError ? (
        <div className="mt-6">
          <EmptyState title="Could not load stats" />
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard icon={Users} label="Users" value={String(stats?.users_count ?? 0)} />
            <KpiCard
              icon={CalendarDays}
              label="Appointments"
              value={String(stats?.appointments_count ?? 0)}
            />
            <KpiCard
              icon={MessageSquare}
              label="Feedback"
              value={String(stats?.feedback_count ?? 0)}
            />
            <KpiCard
              icon={Banknote}
              label="Revenue"
              value={formatMoney(stats?.revenue ?? 0)}
            />
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="size-4" /> Visits by medical category
                </CardTitle>
              </CardHeader>
              <CardContent>
                {byCategory.isPending ? (
                  <PageLoader />
                ) : (byCategory.data?.length ?? 0) === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">
                    No visit data yet.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {(byCategory.data ?? []).map((c) => (
                      <div key={c.category_id}>
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="font-medium">{c.category_name}</span>
                          <span className="text-muted-foreground">{c.visit_count} visits</span>
                        </div>
                        <Progress value={(c.visit_count / maxCategory) * 100} />
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

function KpiCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Users
  label: string
  value: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="truncate text-xl font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}
