import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { Plus, Pencil, Trash2, Star } from 'lucide-react'

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
import { useCategories } from '@/hooks/useCategories'
import type { DoctorSummary } from '@/lib/types'

export const Route = createFileRoute('/admin/_admin/doctors')({
  component: AdminDoctorsPage,
})

interface DoctorForm {
  hospital_id: string
  medical_category_id: string
  full_name: string
  experience_years: string
}

const emptyForm = (): DoctorForm => ({
  hospital_id: '',
  medical_category_id: '',
  full_name: '',
  experience_years: '0',
})

function AdminDoctorsPage() {
  const queryClient = useQueryClient()
  const { data: categories } = useCategories()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<DoctorSummary | null>(null)
  const [deleting, setDeleting] = useState<DoctorSummary | null>(null)
  const [form, setForm] = useState<DoctorForm>(emptyForm())

  const { data, isPending, isError } = useQuery({
    queryKey: ['admin', 'doctors'],
    queryFn: () => adminApi.listDoctors({ limit: 200 }),
  })
  const hospitals = useQuery({
    queryKey: ['admin', 'hospitals'],
    queryFn: () => adminApi.listHospitals({ limit: 200 }),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'doctors'] })
    queryClient.invalidateQueries({ queryKey: ['hospitals'] })
  }

  const createMutation = useMutation({
    mutationFn: (body: NonNullable<ReturnType<typeof toPayload>>) => adminApi.createDoctor(body),
    onSuccess: () => {
      toast.success('Doctor created')
      setDialogOpen(false)
      invalidate()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Create failed'),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: NonNullable<ReturnType<typeof toPayload>> }) =>
      adminApi.updateDoctor(id, body),
    onSuccess: () => {
      toast.success('Doctor updated')
      setDialogOpen(false)
      invalidate()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Update failed'),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteDoctor(id),
    onSuccess: () => {
      toast.success('Doctor deleted')
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
  const openEdit = (doctor: DoctorSummary) => {
    setEditing(doctor)
    setForm({
      hospital_id: String(doctor.hospital_id),
      medical_category_id: String(doctor.medical_category_id),
      full_name: doctor.full_name,
      experience_years: String(doctor.experience_years),
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
  const hospitalName = (id: number) => hospitals.data?.find((h) => h.id === id)?.name ?? `#${id}`

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Doctors</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage doctors linked to hospitals and medical categories.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="size-4" /> Add doctor
        </Button>
      </div>

      {isPending ? (
        <PageLoader />
      ) : isError ? (
        <EmptyState title="Could not load doctors" />
      ) : (data?.length ?? 0) === 0 ? (
        <div className="mt-6">
          <EmptyState title="No doctors yet" action={<Button onClick={openCreate}>Add the first</Button>} />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Hospital</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Experience</TableHead>
                <TableHead>Rating</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((doctor) => (
                <TableRow key={doctor.id}>
                  <TableCell className="font-medium">{doctor.full_name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {hospitalName(doctor.hospital_id)}
                  </TableCell>
                  <TableCell>
                    {categories?.find((c) => c.id === doctor.medical_category_id)?.name ?? '—'}
                  </TableCell>
                  <TableCell>{doctor.experience_years} yrs</TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1 text-sm">
                      <Star className="size-3.5 fill-amber-400 text-amber-400" />
                      {doctor.rating_avg.toFixed(1)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(doctor)}>
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-destructive"
                        onClick={() => setDeleting(doctor)}
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
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit doctor' : 'Add doctor'}</DialogTitle>
            <DialogDescription>Link a doctor to a hospital and category.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="space-y-1.5">
              <Label>Hospital</Label>
              <select
                value={form.hospital_id}
                onChange={(e) => setForm({ ...form, hospital_id: e.target.value })}
                className="h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="">Select hospital…</option>
                {(hospitals.data ?? []).map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Category</Label>
              <select
                value={form.medical_category_id}
                onChange={(e) => setForm({ ...form, medical_category_id: e.target.value })}
                className="h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="">Select category…</option>
                {(categories ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Full name</Label>
              <Input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Experience (years)</Label>
              <Input
                type="number"
                min={0}
                value={form.experience_years}
                onChange={(e) => setForm({ ...form, experience_years: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={submit}
              disabled={busy || !form.full_name.trim() || !form.hospital_id || !form.medical_category_id}
            >
              {busy ? 'Saving…' : editing ? 'Save changes' : 'Create doctor'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleting != null} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete doctor?</AlertDialogTitle>
            <AlertDialogDescription>
              This will delete “{deleting?.full_name}”. The action is recorded in the audit log.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground"
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

function toPayload(form: DoctorForm) {
  if (!form.full_name.trim() || !form.hospital_id || !form.medical_category_id) {
    toast.error('Name, hospital and category are required')
    return null
  }
  return {
    hospital_id: Number(form.hospital_id),
    medical_category_id: Number(form.medical_category_id),
    full_name: form.full_name.trim(),
    experience_years: Math.max(0, Number(form.experience_years) || 0),
  }
}
