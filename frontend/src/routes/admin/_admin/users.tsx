import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { UserRound, Phone, Mail, ShieldCheck } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
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
import { databaseApi } from '@/lib/api'
import { formatDate } from '@/lib/format'
import type { User } from '@/lib/types'

export const Route = createFileRoute('/admin/_admin/users')({
  component: AdminUsersPage,
})

function AdminUsersPage() {
  const queryClient = useQueryClient()

  const { data, isPending, isError } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => databaseApi.listUsers({ limit: 200 }),
  })

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: User['role'] }) =>
      databaseApi.updateUser(id, { role }),
    onSuccess: (updated) => {
      toast.success(`${updated.full_name} is now ${updated.role}`)
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Update failed'),
  })

  return (
    <div>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Patient and admin accounts, role changes and status.
        </p>
      </div>

      {isPending ? (
        <PageLoader />
      ) : isError ? (
        <EmptyState title="Could not load users" />
      ) : (data?.length ?? 0) === 0 ? (
        <div className="mt-6">
          <EmptyState title="No users yet" />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="text-right">Admin</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <span className="flex items-center gap-2 font-medium">
                      <UserRound className="size-4 text-muted-foreground" />
                      {user.full_name}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    <div className="flex flex-col gap-0.5">
                      <span className="flex items-center gap-1">
                        <Phone className="size-3.5" /> {user.phone ?? '—'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Mail className="size-3.5" /> {user.email ?? '—'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(user.created_at)}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="capitalize">
                      {user.role}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Switch
                      checked={user.role === 'admin'}
                      disabled={roleMutation.isPending}
                      onCheckedChange={(checked) =>
                        roleMutation.mutate({ id: user.id, role: checked ? 'admin' : 'patient' })
                      }
                      aria-label={`Toggle admin for ${user.full_name}`}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <div className="mt-4 flex items-start gap-2 rounded-xl bg-muted p-3 text-sm text-muted-foreground">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
        <p>
          Every role change and admin action is recorded in the audit log for accountability.
        </p>
      </div>
    </div>
  )
}
