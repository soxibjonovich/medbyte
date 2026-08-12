import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { requireAdmin } from '@/lib/guards'
import { Search, ScrollText } from 'lucide-react'

import { Input } from '@/components/ui/input'
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
import { adminApi, databaseApi } from '@/lib/api'
import { formatDateTime } from '@/lib/format'

export const Route = createFileRoute('/admin/_admin/audit-log')({
  beforeLoad: () => requireAdmin(),
  component: AdminAuditLogPage,
})

const ACTION_STYLES: Record<string, string> = {
  create: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
  update: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
  delete: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300',
}

function AdminAuditLogPage() {
  const [query, setQuery] = useState('')

  const log = useQuery({
    queryKey: ['admin', 'audit-log'],
    queryFn: () => adminApi.auditLog({ limit: 200 }),
  })
  const users = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => databaseApi.listUsers({ limit: 200 }),
  })

  const rows = useMemo(() => {
    const list = log.data ?? []
    if (!query) return list
    const q = query.toLowerCase()
    return list.filter(
      (entry) =>
        entry.action.toLowerCase().includes(q) ||
        entry.entity.toLowerCase().includes(q) ||
        String(entry.entity_id ?? '').includes(q),
    )
  }, [log.data, query])

  const actorName = (id: number) => users.data?.find((u) => u.id === id)?.full_name ?? `User #${id}`

  return (
    <div>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Immutable record of every admin create, update and delete action.
        </p>
      </div>

      <div className="relative mt-6 max-w-sm">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by action or entity…"
          className="pl-9"
        />
      </div>

      {log.isPending ? (
        <PageLoader />
      ) : log.isError ? (
        <EmptyState title="Could not load audit log" />
      ) : rows.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            icon={<ScrollText className="size-8" />}
            title="No audit entries"
            description="Admin mutations will be logged here."
          />
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>When</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead>ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(entry.created_at)}
                  </TableCell>
                  <TableCell className="font-medium">{actorName(entry.actor_id)}</TableCell>
                  <TableCell>
                    <Badge className={ACTION_STYLES[entry.action] ?? ''}>{entry.action}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{entry.entity}</TableCell>
                  <TableCell className="font-mono text-muted-foreground">
                    {entry.entity_id ?? '—'}
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
