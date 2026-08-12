import { Link, useNavigate } from '@tanstack/react-router'
import { HeartPulse, Bell, LogOut, LayoutDashboard, User } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuthStore } from '@/stores/auth'
import { initials } from '@/lib/format'

const NAV = [
  { label: 'Hospitals', to: '/leaderboard' },
  { label: 'AI Assistant', to: '/ai-chat' },
]

const USER_NAV = [
  { label: 'Discounts', to: '/discounts' },
  { label: 'Appointments', to: '/profile/appointments' },
]

export function AppHeader() {
  const { token, user, clearSession } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    clearSession()
    navigate({ to: '/' })
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <HeartPulse className="size-4" />
          </span>
          <span className="hidden sm:inline">MedByte</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV.map((item) => (
            <Button key={item.to} variant="ghost" size="sm" render={<Link to={item.to} />}>
              {item.label}
            </Button>
          ))}
          {token &&
            USER_NAV.map((item) => (
              <Button key={item.to} variant="ghost" size="sm" render={<Link to={item.to} />}>
                {item.label}
              </Button>
            ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {token ? (
            <>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Notifications"
                render={<Link to="/notifications" />}
              >
                <Bell className="size-4" />
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger render={<Button variant="ghost" className="gap-2 px-1.5" />}>
                  <Avatar className="size-7">
                    <AvatarFallback>{initials(user?.full_name ?? 'U')}</AvatarFallback>
                  </Avatar>
                  <span className="hidden max-w-32 truncate text-sm font-medium sm:inline">
                    {user?.full_name}
                  </span>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuGroup>
                    <DropdownMenuLabel>Signed in as {user?.full_name}</DropdownMenuLabel>
                  </DropdownMenuGroup>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem render={<Link to="/profile" />}>
                    <User className="size-4" />
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuItem render={<Link to="/profile/appointments" />}>
                    <HeartPulse className="size-4" />
                    My appointments
                  </DropdownMenuItem>
                  <DropdownMenuItem render={<Link to="/discounts" />}>
                    <HeartPulse className="size-4" />
                    My discounts
                  </DropdownMenuItem>
                  {(user?.role === 'admin' || user?.role === 'staff') && (
                    <>
                      <DropdownMenuSeparator />
                      {/* Staff land on the overview (index.tsx) is admin-only, so send them
                          straight to the one page they can actually use. */}
                      <DropdownMenuItem
                        render={<Link to={user?.role === 'admin' ? '/admin' : '/admin/queue'} />}
                      >
                        <LayoutDashboard className="size-4" />
                        Admin dashboard
                      </DropdownMenuItem>
                    </>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout}>
                    <LogOut className="size-4" />
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" render={<Link to="/login" />}>
                Log in
              </Button>
              <Button size="sm" render={<Link to="/register" />}>
                Get started
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
