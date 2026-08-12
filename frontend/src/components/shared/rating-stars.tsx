import { Star } from 'lucide-react'
import { cn } from '@/lib/utils'

export function RatingStars({
  value,
  className,
  size = 'sm',
  onRate,
}: {
  value: number
  className?: string
  size?: 'sm' | 'md' | 'lg'
  onRate?: (rating: number) => void
}) {
  const sizes = { sm: 'size-3.5', md: 'size-5', lg: 'size-7' }
  return (
    <div className={cn('flex items-center gap-0.5', className)}>
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          disabled={!onRate}
          onClick={() => onRate?.(i)}
          className={cn(
            'disabled:cursor-default',
            onRate && 'cursor-pointer transition-transform hover:scale-110',
          )}
          aria-label={`${i} star${i > 1 ? 's' : ''}`}
        >
          <Star
            className={cn(
              sizes[size],
              i <= Math.round(value)
                ? 'fill-amber-400 text-amber-400'
                : 'fill-muted text-muted',
            )}
          />
        </button>
      ))}
      {value > 0 && (
        <span className="ml-1.5 text-xs font-medium text-muted-foreground">
          {value.toFixed(1)}
        </span>
      )}
    </div>
  )
}
