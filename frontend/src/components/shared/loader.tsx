import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('size-4 animate-spin', className)} />
}

export function PageLoader({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-muted-foreground">
      <Spinner className="size-6" />
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function InlineLoader({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center justify-center p-4 text-muted-foreground', className)}>
      <Spinner />
    </div>
  )
}
