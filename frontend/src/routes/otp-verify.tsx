import { createFileRoute, Link } from '@tanstack/react-router'
import { useState } from 'react'
import { CheckCircle2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp'
import { AuthShell } from '@/components/auth/auth-shell'

export const Route = createFileRoute('/otp-verify')({
  component: OTPVerifyPage,
})

function OTPVerifyPage() {
  const [value, setValue] = useState('')
  const [verified, setVerified] = useState(false)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (value.length === 6) setVerified(true)
  }

  return (
    <AuthShell
      title="Verify your phone"
      subtitle="Enter the 6-digit code sent via SMS"
      footer={
        <Link to="/register" className="font-medium text-primary hover:underline">
          Back to sign up
        </Link>
      }
    >
      {verified ? (
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <CheckCircle2 className="size-12 text-emerald-500" />
          <p className="font-medium">Phone verified</p>
          <p className="text-sm text-muted-foreground">
            Your account is active. You can now log in and start booking.
          </p>
          <Button className="mt-2" render={<Link to="/login" />}>
            Go to login
          </Button>
        </div>
      ) : (
        <>
          <form onSubmit={submit} className="flex flex-col items-center gap-4">
            <InputOTP maxLength={6} value={value} onChange={setValue}>
              <InputOTPGroup>
                {Array.from({ length: 6 }).map((_, i) => (
                  <InputOTPSlot key={i} index={i} />
                ))}
              </InputOTPGroup>
            </InputOTP>
            <Button type="submit" className="w-full" size="lg" disabled={value.length !== 6}>
              Verify code
            </Button>
          </form>
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Note: SMS OTP dispatch is wired through Eskiz.uz on the backend. In this demo the code
            is verified client-side.
          </p>
        </>
      )}
    </AuthShell>
  )
}
