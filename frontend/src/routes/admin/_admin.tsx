import { createFileRoute, Link, Outlet, useLocation } from '@tanstack/react-router'
import {
  LayoutDashboard,
  Building2,
  Stethoscope,
  TicketPercent,
  CalendarDays,
  MessageSquare,
  BarChart3,
  Users,
  ScrollText,
  LogOut,
  ExternalLink,
  Menu,
  Radio,
} from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { requireStaff } from '@/lib/guards'
import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

// Staff and admin can both reach the admin section layout; individual leaf
// routes that are genuinely admin-only re-guard themselves with requireAdmin().
export const Route = createFileRoute('/admin/_admin')({
  beforeLoad: () => requireStaff(),
  component: AdminLayout,
})

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

const NAV: NavItem[] = [
  { label: 'Overview', to: '/admin', icon: LayoutDashboard },
  { label: 'Hospitals', to: '/admin/hospitals', icon: Building2 },
  { label: 'Doctors', to: '/admin/doctors', icon: Stethoscope },
  { label: 'Discounts', to: '/admin/discounts', icon: TicketPercent },
  { label: 'Appointments', to: '/admin/appointments', icon: CalendarDays },
  { label: 'Live queue', to: '/admin/queue', icon: Radio },
  { label: 'Feedback', to: '/admin/feedback', icon: MessageSquare },
  { label: 'Statistics', to: '/admin/statistics', icon: BarChart3 },
  { label: 'Users', to: '/admin/users', icon: Users },
  { label: 'Audit log', to: '/admin/audit-log', icon: ScrollText },
]

function AdminLayout() {
  const user = useAuthStore((s) => s.user)
  const clearSession = useAuthStore((s) => s.clearSession)
  const location = useLocation()
  const [open, setOpen] = useState(false)

  const nav = (
    <nav className="flex flex-col gap-1 p-3">
      {NAV.map(({ label, to, icon: Icon }) => (
        <Link
          key={to}
          to={to}
          onClick={() => setOpen(false)}
          className={cn(
            'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            location.pathname === to
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground',
          )}
        >
          <Icon className="size-4 shrink-0" />
          {label}
        </Link>
      ))}
    </nav>
  )

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-60 shrink-0 border-r bg-muted/30 md:block">
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <LayoutDashboard className="size-4" />
          </span>
          <span className="font-semibold">MedByte Admin</span>
        </div>
        {nav}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger render={<Button variant="ghost" size="icon" className="md:hidden" />}>
              <Menu className="size-5" />
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              {nav}
            </SheetContent>
          </Sheet>

          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{user?.full_name}</p>
            <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
          </div>

          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" size="sm" render={<Link to="/" />}>
              <ExternalLink className="size-4" /> View site
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={clearSession} aria-label="Log out">
              <LogOut className="size-4" />
            </Button>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
