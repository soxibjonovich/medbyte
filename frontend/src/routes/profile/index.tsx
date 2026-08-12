import { createFileRoute, Link } from '@tanstack/react-router'
import { useState } from 'react'
import {
  HeartPulse,
  Bell,
  TicketPercent,
  LogOut,
  Mail,
  Phone,
  CalendarDays,
  Save,
} from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { requireAuth } from '@/lib/guards'
import { databaseApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { formatDate, initials } from '@/lib/format'

export const Route = createFileRoute('/profile/')({
  beforeLoad: () => requireAuth(),
  component: ProfilePage,
})

function ProfilePage() {
  const { user, setUser, clearSession } = useAuthStore()
  const queryClient = useQueryClient()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')

  const updateProfile = useMutation({
    mutationFn: () =>
      databaseApi.updateUser(user!.id, {
        full_name: fullName,
        email: email || null,
      }),
    onSuccess: (updated) => {
      setUser(updated)
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('Profile updated')
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Update failed'),
  })

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">My profile</h1>

      <div className="mt-6 grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card>
          <CardContent className="flex flex-col items-center gap-3 pt-6 text-center">
            <Avatar className="size-16 text-lg">
              <AvatarFallback>{initials(user?.full_name ?? 'U')}</AvatarFallback>
            </Avatar>
            <div>
              <p className="font-medium">{user?.full_name}</p>
              <Badge variant="secondary" className="mt-1 capitalize">
                {user?.role}
              </Badge>
            </div>
            <dl className="w-full space-y-2 text-sm">
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <Phone className="size-3.5" /> {user?.phone ?? '—'}
              </div>
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <Mail className="size-3.5" /> {user?.email ?? '—'}
              </div>
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <CalendarDays className="size-3.5" /> Joined {user ? formatDate(user.created_at) : '—'}
              </div>
            </dl>
            <Button variant="outline" className="mt-2 w-full" onClick={clearSession}>
              <LogOut className="size-4" /> Log out
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <Link to="/profile/appointments">
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="flex flex-col items-start gap-2">
                  <HeartPulse className="size-5 text-primary" />
                  <p className="font-medium">Appointments</p>
                  <p className="text-sm text-muted-foreground">Queue tickets & status</p>
                </CardContent>
              </Card>
            </Link>
            <Link to="/notifications">
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="flex flex-col items-start gap-2">
                  <Bell className="size-5 text-primary" />
                  <p className="font-medium">Notifications</p>
                  <p className="text-sm text-muted-foreground">Updates & reminders</p>
                </CardContent>
              </Card>
            </Link>
            <Link to="/discounts">
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="flex flex-col items-start gap-2">
                  <TicketPercent className="size-5 text-primary" />
                  <p className="font-medium">Discounts</p>
                  <p className="text-sm text-muted-foreground">Reward codes wallet</p>
                </CardContent>
              </Card>
            </Link>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Personal information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
              <Button
                onClick={() => updateProfile.mutate()}
                disabled={updateProfile.isPending || !fullName.trim()}
              >
                <Save className="size-4" />
                {updateProfile.isPending ? 'Saving…' : 'Save changes'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
