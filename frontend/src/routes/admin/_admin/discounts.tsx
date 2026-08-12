import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { requireAdmin } from '@/lib/guards'
import { toast } from 'sonner'
import { Plus, Pencil, Trash2, Copy } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
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
import { adminApi, databaseApi } from '@/lib/api'
import { copyToClipboard, formatDate } from '@/lib/format'
import type { Discount } from '@/lib/types'

export const Route = createFileRoute('/admin/_admin/discounts')({
  beforeLoad: () => requireAdmin(),
  component: AdminDiscountsPage,
})

interface DiscountForm {
  user_id: string
  title: string
  code: string
  percent_off: string
  expires_at: string
}

const emptyForm = (): DiscountForm => ({
  user_id: '',
  title: '',
  code: '',
  percent_off: '10',
  expires_at: '',
})

function AdminDiscountsPage() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Discount | null>(null)
  const [deleting, setDeleting] = useState<Discount | null>(null)
  const [form, setForm] = useState<DiscountForm>(emptyForm())

  const { data, isPending, isError } = useQuery({
    queryKey: ['admin', 'discounts'],
    queryFn: () => adminApi.listDiscounts({ limit: 200 }),
  })
  const users = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => databaseApi.listUsers({ limit: 200 }),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin', 'discounts'] })

  const createMutation = useMutation({
    mutationFn: (body: NonNullable<ReturnType<typeof toPayload>>) => adminApi.createDiscount(body),
    onSuccess: () => {
      toast.success('Discount created')
      setDialogOpen(false)
      invalidate()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Create failed'),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, is_used }: { id: number; is_used: boolean }) =>
      adminApi.updateDiscount(id, { is_used }),
    onSuccess: () => {
      toast.success('Discount updated')
      invalidate()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Update failed'),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteDiscount(id),
    onSuccess: () => {
      toast.success('Discount deactivated')
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
  const openEdit = (discount: Discount) => {
    setEditing(discount)
    setForm({
      user_id: String(discount.user_id),
      title: discount.title,
      code: discount.code,
      percent_off: String(discount.percent_off),
      expires_at: discount.expires_at ? discount.expires_at.slice(0, 10) : '',
    })
    setDialogOpen(true)
  }

  const submit = () => {
    if (editing) {
      if (!form.user_id) {
        toast.error('User is required')
        return
      }
      updateMutation.mutate({ id: editing.id, is_used: editing.is_used })
      setDialogOpen(false)
      return
    }
    const body = toPayload(form)
    if (body) createMutation.mutate(body)
  }

  const busy = createMutation.isPending || deleteMutation.isPending
  const userName = (id: number) => users.data?.find((u) => u.id === id)?.full_name ?? `User #${id}`

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Discounts</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Reward codes issued to patients for leaving feedback.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="size-4" /> Create discount
        </Button>
      </div>

      {isPending ? (
        <PageLoader />
      ) : isError ? (
        <EmptyState title="Could not load discounts" />
      ) : (data?.length ?? 0) === 0 ? (
        <div className="mt-6">
          <EmptyState title="No discounts yet" action={<Button onClick={openCreate}>Create one</Button>} />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>User</TableHead>
                <TableHead>% off</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((discount) => (
                <TableRow key={discount.id}>
                  <TableCell className="font-mono font-semibold">{discount.code}</TableCell>
                  <TableCell>{discount.title}</TableCell>
                  <TableCell className="text-muted-foreground">{userName(discount.user_id)}</TableCell>
                  <TableCell>{discount.percent_off}%</TableCell>
                  <TableCell className="text-muted-foreground">
                    {discount.expires_at ? formatDate(discount.expires_at) : '—'}
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={!discount.is_used}
                      onCheckedChange={(checked) =>
                        updateMutation.mutate({ id: discount.id, is_used: !checked })
                      }
                      aria-label="Active"
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => copyToClipboard(discount.code).then(() => toast.success('Code copied'))}
                      >
                        <Copy className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(discount)}>
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-destructive"
                        onClick={() => setDeleting(discount)}
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
            <DialogTitle>{editing ? 'Edit discount' : 'Create discount'}</DialogTitle>
            <DialogDescription>
              Set the reward code rules. Codes are drawn from this pool when patients submit
              feedback.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="space-y-1.5">
              <Label>Patient</Label>
              <select
                value={form.user_id}
                onChange={(e) => setForm({ ...form, user_id: e.target.value })}
                className="h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="">Select user…</option>
                {(users.data ?? []).map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.phone ?? u.email ?? `#${u.id}`})
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Title</Label>
                <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>Code</Label>
                <Input
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  placeholder="MED10"
                />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Percent off</Label>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={form.percent_off}
                  onChange={(e) => setForm({ ...form, percent_off: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Expires (optional)</Label>
                <Input
                  type="date"
                  value={form.expires_at}
                  onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
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
              disabled={busy || !form.code.trim() || !form.title.trim() || !form.user_id}
            >
              {busy ? 'Saving…' : editing ? 'Save changes' : 'Create discount'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleting != null} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate discount?</AlertDialogTitle>
            <AlertDialogDescription>
              Code “{deleting?.code}” will be deactivated for user {deleting ? userName(deleting.user_id) : ''}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground"
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
            >
              Deactivate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function toPayload(form: DiscountForm) {
  if (!form.code.trim() || !form.title.trim() || !form.user_id) {
    toast.error('Code, title and user are required')
    return null
  }
  return {
    user_id: Number(form.user_id),
    title: form.title.trim(),
    code: form.code.trim().toUpperCase(),
    percent_off: Math.min(100, Math.max(1, Number(form.percent_off) || 10)),
    expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
  }
}
