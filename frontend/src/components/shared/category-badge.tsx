import { useCategories } from '@/hooks/useCategories'
import { Badge } from '@/components/ui/badge'

export function CategoryBadge({
  categoryId,
  className,
}: {
  categoryId: number | null | undefined
  className?: string
}) {
  const { data } = useCategories()
  const name = data?.find((c) => c.id === categoryId)?.name
  if (!name) return null
  return (
    <Badge variant="secondary" className={className}>
      {name}
    </Badge>
  )
}

export function useCategoryName() {
  const { data } = useCategories()
  return (id: number | null | undefined) => data?.find((c) => c.id === id)?.name
}
