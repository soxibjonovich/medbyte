import { Building2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const GRADIENTS = [
  'from-sky-100 to-blue-200',
  'from-emerald-100 to-teal-200',
  'from-rose-100 to-pink-200',
  'from-violet-100 to-purple-200',
  'from-amber-100 to-orange-200',
  'from-cyan-100 to-sky-200',
]

export function HospitalImage({
  name,
  className,
  index = 0,
}: {
  name?: string
  className?: string
  index?: number
}) {
  const gradient = GRADIENTS[index % GRADIENTS.length]
  return (
    <div
      className={cn(
        'flex items-center justify-center bg-gradient-to-br text-slate-500',
        gradient,
        className,
      )}
      aria-hidden
    >
      <Building2 className="size-10" />
      {name && (
        <span className="sr-only">
          Hospital: {name}
        </span>
      )}
    </div>
  )
}
