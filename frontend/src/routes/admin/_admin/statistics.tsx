import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { requireAdmin } from '@/lib/guards'
import { toast } from 'sonner'
import { Bar, BarChart, CartesianGrid, XAxis, YAxis, Cell } from 'recharts'
import { Download, TrendingUp } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { adminApi } from '@/lib/api'

export const Route = createFileRoute('/admin/_admin/statistics')({
  beforeLoad: () => requireAdmin(),
  component: AdminStatisticsPage,
})

const PALETTE = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#ec4899',
  '#84cc16',
  '#f97316',
  '#6366f1',
]

function AdminStatisticsPage() {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [applied, setApplied] = useState<{ from?: string; to?: string }>({})

  const byCategory = useQuery({
    queryKey: ['admin', 'by-category', applied],
    queryFn: () =>
      adminApi.statsByCategory(applied.from, applied.to),
  })

  const overview = useQuery({ queryKey: ['admin', 'stats'], queryFn: adminApi.statsOverview })

  const data = (byCategory.data ?? []).map((row, i) => ({
    name: row.category_name,
    visits: row.visit_count,
    fill: PALETTE[i % PALETTE.length],
  }))

  const config: ChartConfig = {
    visits: { label: 'Visits' },
  }

  const exportCsv = async () => {
    try {
      await adminApi.statsExportCsv(applied)
      toast.success('Export job started')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Export not available yet')
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Statistics</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Visits per medical category — the signal for drug-demand forecasting.
          </p>
        </div>
        <Button variant="outline" onClick={exportCsv}>
          <Download className="size-4" /> Export CSV
        </Button>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="size-4" /> Visits by category
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-6 flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">From</Label>
              <Input
                type="date"
                className="h-8"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">To</Label>
              <Input
                type="date"
                className="h-8"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
            <Button
              size="sm"
              onClick={() => setApplied({ from: dateFrom || undefined, to: dateTo || undefined })}
            >
              Apply range
            </Button>
          </div>

          {byCategory.isPending ? (
            <PageLoader />
          ) : data.length === 0 ? (
            <EmptyState title="No visit data in this range" />
          ) : (
            <ChartContainer config={config} className="h-72">
              <BarChart data={data} margin={{ left: 0, right: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} interval={0} />
                <YAxis tickLine={false} axisLine={false} allowDecimals={false} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="visits" radius={[6, 6, 0, 0]}>
                  {data.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        <StatCard label="Users" value={overview.data?.users_count} />
        <StatCard label="Appointments" value={overview.data?.appointments_count} />
        <StatCard label="Feedback" value={overview.data?.feedback_count} />
        <StatCard label="Revenue (UZS)" value={overview.data?.revenue} />
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value?: number }) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold">
          {value != null ? value.toLocaleString() : '—'}
        </p>
      </CardContent>
    </Card>
  )
}
