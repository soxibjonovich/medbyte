import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { CalendarDays, User as UserIcon, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { adminApi, databaseApi, hospitalsApi } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import type { AppointmentStatus } from '@/lib/types'

export const Route = createFileRoute('/admin/_admin/appointments')({
  component: AdminAppointmentsPage,
})

const STATUS_STYLES: Record<AppointmentStatus, string> = {
  scheduled: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
  completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
  cancelled: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300',
}

function AdminAppointmentsPage() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<'all' | AppointmentStatus>('all')

  const { data, isPending, isError } = useQuery({
    queryKey: ['admin', 'appointments'],
    queryFn: () => databaseApi.listAppointments({ limit: 200 }),
  })
  const users = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => databaseApi.listUsers({ limit: 200 }),
  })
  // Best-effort lookups — fall back to the raw id if these fail.
  const hospitals = useQuery({
    queryKey: ['hospitals', 'all'],
    queryFn: () => hospitalsApi.list({ limit: 200 }),
    retry: false,
  })
  const doctors = useQuery({
    queryKey: ['admin', 'doctors'],
    queryFn: () => adminApi.listDoctors({ limit: 200 }),
    retry: false,
  })

  const cancelMutation = useMutation({
    mutationFn: (id: number) => databaseApi.updateAppointment(id, { status: 'cancelled' }),
    onSuccess: () => {
      toast.success('Appointment cancelled')
      queryClient.invalidateQueries({ queryKey: ['admin', 'appointments'] })
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Cancel failed'),
  })

  const rows = useMemo(() => {
    const list = data ?? []
    return filter === 'all' ? list : list.filter((a) => a.status === filter)
  }, [data, filter])

  const userName = (id: number) => users.data?.find((u) => u.id === id)?.full_name ?? `User #${id}`
  const hospitalName = (id: number | null) =>
    id == null ? '—' : hospitals.data?.find((h) => h.id === id)?.name ?? `Hospital #${id}`
  const doctorName = (id: number | null) =>
    id == null ? '—' : doctors.data?.find((d) => d.id === id)?.full_name ?? `Doctor #${id}`

  return (
    <div>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Appointments</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Live queue and payment monitor across all hospitals.
        </p>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)} className="mt-6">
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="scheduled">Scheduled</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
          <TabsTrigger value="cancelled">Cancelled</TabsTrigger>
        </TabsList>
      </Tabs>

      {isPending ? (
        <PageLoader />
      ) : isError ? (
        <EmptyState title="Could not load appointments" />
      ) : rows.length === 0 ? (
        <div className="mt-6">
          <EmptyState title="No appointments" />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Patient</TableHead>
                <TableHead>Hospital</TableHead>
                <TableHead>Doctor</TableHead>
                <TableHead>Scheduled</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((appointment) => (
                <TableRow key={appointment.id}>
                  <TableCell className="font-mono text-muted-foreground">
                    #{appointment.queue_number ?? appointment.id}
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5">
                      <UserIcon className="size-3.5 text-muted-foreground" />
                      {userName(appointment.user_id)}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {hospitalName(appointment.hospital_id)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {doctorName(appointment.doctor_id)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <CalendarDays className="size-3.5" />
                      {formatDateTime(appointment.scheduled_at)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge className={STATUS_STYLES[appointment.status]}>
                      {appointment.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(appointment.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    {appointment.status === 'scheduled' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => cancelMutation.mutate(appointment.id)}
                        disabled={cancelMutation.isPending}
                      >
                        <X className="size-4" /> Cancel
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
