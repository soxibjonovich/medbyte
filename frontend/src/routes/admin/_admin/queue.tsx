import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { CalendarDays, Plus, Radio, User as UserIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { databaseApi, hospitalsApi, queueApi, type QueueCreateInput } from '@/lib/api'
import { useQueueSocket } from '@/hooks/useQueueSocket'
import { formatDateTime } from '@/lib/format'
import { requireStaff } from '@/lib/guards'
import { cn } from '@/lib/utils'
import type { AppointmentStatus, QueueEntry } from '@/lib/types'

export const Route = createFileRoute('/admin/_admin/queue')({
  beforeLoad: () => requireStaff(),
  component: AdminQueuePage,
})

const QUEUE_QUERY_KEY = ['admin', 'queue']

const STATUS_STYLES: Record<AppointmentStatus, string> = {
  scheduled: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
  completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
  cancelled: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300',
}

interface QueueForm {
  user_id: string
  hospital_id: string
  doctor_id: string
  queue_number: string
  scheduled_at: string
}

const emptyForm = (): QueueForm => ({
  user_id: '',
  hospital_id: '',
  doctor_id: '',
  queue_number: '',
  scheduled_at: '',
})

/** Prepends/updates an entry by id, so websocket pushes and the POST response don't double up. */
function mergeEntry(list: QueueEntry[] | undefined, entry: QueueEntry): QueueEntry[] {
  const existing = list ?? []
  const idx = existing.findIndex((e) => e.id === entry.id)
  if (idx === -1) return [entry, ...existing]
  const next = [...existing]
  next[idx] = entry
  return next
}

function toPayload(form: QueueForm): QueueCreateInput | null {
  if (!form.user_id.trim()) {
    toast.error('Patient id is required')
    return null
  }
  if (!form.scheduled_at) {
    toast.error('Scheduled time is required')
    return null
  }
  return {
    user_id: Number(form.user_id),
    hospital_id: form.hospital_id.trim() ? Number(form.hospital_id) : null,
    doctor_id: form.doctor_id.trim() ? Number(form.doctor_id) : null,
    queue_number: form.queue_number.trim() ? Number(form.queue_number) : null,
    scheduled_at: new Date(form.scheduled_at).toISOString(),
  }
}

function AdminQueuePage() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState<QueueForm>(emptyForm())

  const { data, isPending, isError } = useQuery({
    queryKey: QUEUE_QUERY_KEY,
    queryFn: () => queueApi.list({ limit: 200 }),
  })

  // Best-effort name lookups — staff may not have access to every list here,
  // in which case we just fall back to showing the raw id.
  const hospitals = useQuery({
    queryKey: ['hospitals', 'all'],
    queryFn: () => hospitalsApi.list({ limit: 200 }),
  })
  const users = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => databaseApi.listUsers({ limit: 200 }),
    retry: false,
  })

  const { connected } = useQueueSocket((entry) => {
    queryClient.setQueryData<QueueEntry[]>(QUEUE_QUERY_KEY, (old) => mergeEntry(old, entry))
  })

  const createMutation = useMutation({
    mutationFn: (body: QueueCreateInput) => queueApi.create(body),
    onSuccess: (entry) => {
      toast.success('Queue entry created')
      setDialogOpen(false)
      setForm(emptyForm())
      queryClient.setQueryData<QueueEntry[]>(QUEUE_QUERY_KEY, (old) => mergeEntry(old, entry))
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Create failed'),
  })

  const openCreate = () => {
    setForm(emptyForm())
    setDialogOpen(true)
  }

  const submit = () => {
    const body = toPayload(form)
    if (body) createMutation.mutate(body)
  }

  const hospitalName = (id: number | null) =>
    id == null ? '—' : hospitals.data?.find((h) => h.id === id)?.name ?? `Hospital #${id}`
  const userName = (id: number) => users.data?.find((u) => u.id === id)?.full_name ?? `User #${id}`

  const rows = data ?? []

  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            Live queue
          </h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
            <Radio
              className={cn(
                'size-3.5',
                connected ? 'text-emerald-500' : 'text-muted-foreground/50',
              )}
            />
            {connected ? 'Live — updates stream in automatically' : 'Reconnecting…'}
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="size-4" /> Add to queue
        </Button>
      </div>

      {isPending ? (
        <PageLoader />
      ) : isError ? (
        <EmptyState title="Could not load the queue" />
      ) : rows.length === 0 ? (
        <div className="mt-6">
          <EmptyState title="Queue is empty" action={<Button onClick={openCreate}>Add an entry</Button>} />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Patient</TableHead>
                <TableHead>Hospital</TableHead>
                <TableHead>Scheduled</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="font-mono text-muted-foreground">
                    #{entry.queue_number ?? entry.id}
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5">
                      <UserIcon className="size-3.5 text-muted-foreground" />
                      {userName(entry.user_id)}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {hospitalName(entry.hospital_id)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <CalendarDays className="size-3.5" />
                      {formatDateTime(entry.scheduled_at)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge className={STATUS_STYLES[entry.status]}>{entry.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add to queue</DialogTitle>
            <DialogDescription>
              Creates a new queue entry — every connected staff/admin dashboard sees it live.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="space-y-1.5">
              <Label>Patient id</Label>
              <Input
                type="number"
                min={1}
                value={form.user_id}
                onChange={(e) => setForm({ ...form, user_id: e.target.value })}
                placeholder="e.g. 42"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Hospital (optional)</Label>
                <select
                  value={form.hospital_id}
                  onChange={(e) => setForm({ ...form, hospital_id: e.target.value })}
                  className="h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="">None</option>
                  {(hospitals.data ?? []).map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label>Doctor id (optional)</Label>
                <Input
                  type="number"
                  min={1}
                  value={form.doctor_id}
                  onChange={(e) => setForm({ ...form, doctor_id: e.target.value })}
                />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Queue number (optional)</Label>
                <Input
                  type="number"
                  min={1}
                  value={form.queue_number}
                  onChange={(e) => setForm({ ...form, queue_number: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Scheduled at</Label>
                <Input
                  type="datetime-local"
                  value={form.scheduled_at}
                  onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={submit}
              disabled={createMutation.isPending || !form.user_id.trim() || !form.scheduled_at}
            >
              {createMutation.isPending ? 'Adding…' : 'Add to queue'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
