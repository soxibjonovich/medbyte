import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { Bell, CheckCheck, Send, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { requireAuth } from '@/lib/guards'
import { databaseApi, notificationsApi } from '@/lib/api'
import { preflightPushSubscription, sendSubscriptionToBackend } from '@/lib/push'
import { useAuthStore } from '@/stores/auth'
import { formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/notifications')({
  beforeLoad: () => requireAuth(),
  component: NotificationsPage,
})

function NotificationsPage() {
  const user = useAuthStore((s) => s.user)
  const queryClient = useQueryClient()
  const [sendingTest, setSendingTest] = useState(false)

  const sendTestPush = async () => {
    setSendingTest(true)
    try {
      const subscription = await preflightPushSubscription()
      if (!subscription) {
        toast.error('Push not supported or permission denied — use HTTPS/localhost')
        return
      }
      await sendSubscriptionToBackend(subscription)
      const result = await notificationsApi.testSend()
      if (result.sent === 0) {
        toast.info('No push subscriptions registered for your account')
      } else {
        toast.success(`Test push sent to ${result.sent} device${result.sent === 1 ? '' : 's'}`)
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Test push failed')
    } finally {
      setSendingTest(false)
    }
  }

  const { data, isPending, isError } = useQuery({
    queryKey: ['notifications', user?.id],
    queryFn: () => databaseApi.listNotifications({ user_id: user?.id, limit: 100 }),
    enabled: Boolean(user),
  })

  const markRead = useMutation({
    mutationFn: (id: number) => databaseApi.markNotificationRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const notifications = data ?? []
  const unreadCount = notifications.filter((n) => !n.is_read).length

  const markAllRead = async () => {
    await Promise.all(
      notifications.filter((n) => !n.is_read).map((n) => databaseApi.markNotificationRead(n.id)),
    )
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
    toast.success('All notifications marked as read')
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Confirmations, feedback reminders and discount alerts.
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" onClick={sendTestPush} disabled={sendingTest}>
              {sendingTest ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              Test push
            </Button>
            {unreadCount > 0 && (
              <Button variant="outline" size="sm" onClick={markAllRead}>
                <CheckCheck className="size-4" /> Mark all read
              </Button>
            )}
          </div>
        </div>

      <div className="mt-6 space-y-2">
        {isPending ? (
          <PageLoader />
        ) : isError ? (
          <EmptyState title="Could not load notifications" />
        ) : notifications.length === 0 ? (
          <EmptyState
            title="No notifications yet"
            description="Updates about your bookings and rewards will appear here."
          />
        ) : (
          notifications.map((notification) => (
            <button
              key={notification.id}
              type="button"
              onClick={() => !notification.is_read && markRead.mutate(notification.id)}
              className={cn(
                'block w-full rounded-xl border p-4 text-left transition-colors',
                notification.is_read
                  ? 'bg-background'
                  : 'bg-primary/[0.04] hover:bg-primary/[0.07]',
              )}
            >
              <div className="flex items-start gap-3">
                <span
                  className={cn(
                    'mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg',
                    notification.is_read ? 'bg-secondary text-muted-foreground' : 'bg-primary/10 text-primary',
                  )}
                >
                  <Bell className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{notification.title}</p>
                    {!notification.is_read && (
                      <Badge variant="secondary" className="shrink-0">
                        New
                      </Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-sm text-muted-foreground">{notification.message}</p>
                  <p className="mt-1 text-xs text-muted-foreground/70">
                    {formatRelativeTime(notification.created_at)}
                  </p>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
