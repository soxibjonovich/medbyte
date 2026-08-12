import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { requireAdmin } from '@/lib/guards'
import { toast } from 'sonner'
import { Plus, Pencil, Trash2, Star, MapPin } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
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
import { adminApi } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import type { Hospital } from '@/lib/types'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/admin/_admin/hospitals')({
  beforeLoad: () => requireAdmin(),
  component: AdminHospitalsPage,
})

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

interface HospitalForm {
  name: string
  address: string
  city: string
  lat: string
  lng: string
  phone_numbers: string
  working_hours: Record<string, string>
}

const emptyForm = (): HospitalForm => ({
  name: '',
  address: '',
  city: '',
  lat: '',
  lng: '',
  phone_numbers: '',
  working_hours: Object.fromEntries(DAYS.map((d) => [d, ''])),
})

function AdminHospitalsPage() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Hospital | null>(null)
  const [deleting, setDeleting] = useState<Hospital | null>(null)
  const [form, setForm] = useState<HospitalForm>(emptyForm())

  const { data, isPending, isError } = useQuery({
    queryKey: ['admin', 'hospitals'],
    queryFn: () => adminApi.listHospitals({ limit: 200 }),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin', 'hospitals'] })

  const createMutation = useMutation({
    mutationFn: (body: NonNullable<ReturnType<typeof toPayload>>) => adminApi.createHospital(body),
    onSuccess: () => {
      toast.success('Hospital created')
      setDialogOpen(false)
      invalidate()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Create failed'),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: NonNullable<ReturnType<typeof toPayload>> }) =>
      adminApi.updateHospital(id, body),
    onSuccess: () => {
      toast.success('Hospital updated')
      setDialogOpen(false)
      invalidate()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Update failed'),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteHospital(id),
    onSuccess: () => {
      toast.success('Hospital deleted')
      setDeleting(null)
      invalidate()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Delete failed'),
  })

  const openCreate = () => {
    setEditing(null)
    setForm(emptyForm())
    setDialogOpen(true)
  }
  const openEdit = (hospital: Hospital) => {
    setEditing(hospital)
    setForm({
      name: hospital.name,
      address: hospital.address,
      city: hospital.city,
      lat: String(hospital.lat),
      lng: String(hospital.lng),
      phone_numbers: (hospital.phone_numbers ?? []).join(', '),
      working_hours: {
        ...Object.fromEntries(DAYS.map((d) => [d, ''])),
        ...(hospital.working_hours ?? {}),
      },
    })
    setDialogOpen(true)
  }

  const submit = () => {
    const body = toPayload(form)
    if (!body) return
    if (editing) updateMutation.mutate({ id: editing.id, body })
    else createMutation.mutate(body)
  }

  const busy = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Hospitals</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage hospitals, location, phones and working hours.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="size-4" /> Add hospital
        </Button>
      </div>

      {isPending ? (
        <PageLoader />
      ) : isError ? (
        <EmptyState title="Could not load hospitals" />
      ) : (data?.length ?? 0) === 0 ? (
        <div className="mt-6">
          <EmptyState title="No hospitals yet" action={<Button onClick={openCreate}>Add the first</Button>} />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Address</TableHead>
                <TableHead>City</TableHead>
                <TableHead>Lat</TableHead>
                <TableHead>Lng</TableHead>
                <TableHead>Rating</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((hospital) => (
                <TableRow key={hospital.id}>
                  <TableCell className="font-mono text-muted-foreground">{hospital.id}</TableCell>
                  <TableCell className="font-medium">{hospital.name}</TableCell>
                  <TableCell className="text-muted-foreground">{hospital.address}</TableCell>
                  <TableCell className="text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <MapPin className="size-3.5" /> {hospital.city}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-muted-foreground">{hospital.lat}</TableCell>
                  <TableCell className="font-mono text-muted-foreground">{hospital.lng}</TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1 text-sm">
                      <Star className="size-3.5 fill-amber-400 text-amber-400" />
                      {hospital.rating_avg.toFixed(1)}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(hospital.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(hospital)}>
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-destructive"
                        onClick={() => setDeleting(hospital)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit hospital' : 'Add hospital'}</DialogTitle>
            <DialogDescription>
              Fill in the hospital details. Phones are comma-separated.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Name">
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </Field>
              <Field label="City">
                <Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
              </Field>
            </div>
            <Field label="Address">
              <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Latitude">
                <Input
                  type="number"
                  step="any"
                  value={form.lat}
                  onChange={(e) => setForm({ ...form, lat: e.target.value })}
                />
              </Field>
              <Field label="Longitude">
                <Input
                  type="number"
                  step="any"
                  value={form.lng}
                  onChange={(e) => setForm({ ...form, lng: e.target.value })}
                />
              </Field>
            </div>
            <Field label="Phone numbers (comma separated)">
              <Input
                value={form.phone_numbers}
                onChange={(e) => setForm({ ...form, phone_numbers: e.target.value })}
                placeholder="+998 71 200 00 00, +998 90 123 45 67"
              />
            </Field>
            <div>
              <p className="mb-2 text-sm font-medium">Working hours</p>
              <div className="grid grid-cols-2 gap-3">
                {DAYS.map((day) => (
                  <div key={day} className="flex items-center gap-2">
                    <Label className="w-20 shrink-0 text-xs text-muted-foreground">{day}</Label>
                    <Input
                      className="h-8"
                      value={form.working_hours[day] ?? ''}
                      onChange={(e) =>
                        setForm({ ...form, working_hours: { ...form.working_hours, [day]: e.target.value } })
                      }
                      placeholder="09:00–18:00"
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={busy || !form.name.trim()}>
              {busy ? 'Saving…' : editing ? 'Save changes' : 'Create hospital'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleting != null} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete hospital?</AlertDialogTitle>
            <AlertDialogDescription>
              This will soft-delete “{deleting?.name}”. This action is logged and can be reviewed in
              the audit log.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className={cn('bg-destructive text-destructive-foreground')}
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  )
}

function toPayload(form: HospitalForm) {
  const lat = Number(form.lat)
  const lng = Number(form.lng)
  if (!form.name.trim() || !form.address.trim() || !form.city.trim() || Number.isNaN(lat) || Number.isNaN(lng)) {
    toast.error('Name, address, city and valid coordinates are required')
    return null
  }
  return {
    name: form.name.trim(),
    address: form.address.trim(),
    city: form.city.trim(),
    lat,
    lng,
    phone_numbers: form.phone_numbers
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean),
    working_hours: Object.fromEntries(
      DAYS.map((d) => [d, form.working_hours[d]?.trim()]).filter(([, v]) => v),
    ),
  }
}
