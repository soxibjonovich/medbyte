import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuthShell } from '@/components/auth/auth-shell'
import { authApi } from '@/lib/api'
import { notifyLogin } from '@/lib/notifications'
import { preflightPushSubscription } from '@/lib/push'
import { useAuthStore } from '@/stores/auth'
import { toast } from 'sonner'

const schema = z.object({
  username: z.string().min(1, 'Enter your username'),
  password: z.string().min(1, 'Password is required'),
})

type FormValues = z.infer<typeof schema>

interface LoginSearch {
  redirect?: string
}

export const Route = createFileRoute('/login')({
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    redirect: typeof search.redirect === 'string' ? search.redirect : undefined,
  }),
  component: LoginPage,
})

function LoginPage() {
  const { redirect } = Route.useSearch()
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    // Start the push subscription inside the click gesture so mobile browsers accept it.
    const subscriptionPromise = preflightPushSubscription()
    try {
      const res = await authApi.login({ username: values.username, password: values.password })
      setSession(res.access_token, res.user)
      toast.success(`Welcome back, ${res.user.full_name}!`)
      void notifyLogin(res.user, subscriptionPromise)
      navigate({ to: redirect ?? '/profile' } as never)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Login failed')
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in with your username and password"
      footer={
        <>
          New to MedByte?{' '}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            placeholder="your_username"
            autoComplete="username"
            {...register('username')}
          />
          {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            {...register('password')}
          />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>
        <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Logging in…' : 'Log in'}
        </Button>
      </form>
    </AuthShell>
  )
}
