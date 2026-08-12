import { createRootRoute, Outlet, useLocation } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'

import { AppHeader } from '@/components/layout/app-header'
import { AppFooter } from '@/components/layout/app-footer'
import { TooltipProvider } from '@/components/ui/tooltip'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

function RootLayout() {
  const location = useLocation()
  const isAdminArea = location.pathname.startsWith('/admin')

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <div className="flex min-h-screen flex-col">
          {!isAdminArea && <AppHeader />}
          <main className="flex-1">
            <Outlet />
          </main>
          {!isAdminArea && <AppFooter />}
        </div>
        <Toaster richColors position="top-center" />
      </TooltipProvider>
    </QueryClientProvider>
  )
}

export const Route = createRootRoute({ component: RootLayout })
