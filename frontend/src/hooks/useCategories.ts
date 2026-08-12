import { useQuery } from '@tanstack/react-query'
import { categoriesApi } from '@/lib/api'
import type { MedicalCategory } from '@/lib/types'

/** Fallback list so filters still work when the categories endpoint is unreachable. */
const FALLBACK_CATEGORIES: MedicalCategory[] = [
  { id: 1, name: 'Cardiology' },
  { id: 2, name: 'Dentistry' },
  { id: 3, name: 'Pediatrics' },
  { id: 4, name: 'Neurology' },
  { id: 5, name: 'Dermatology' },
  { id: 6, name: 'Gynecology' },
  { id: 7, name: 'Ophthalmology' },
  { id: 8, name: 'Orthopedics' },
  { id: 9, name: 'Therapy' },
  { id: 10, name: 'ENT' },
]

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
    placeholderData: FALLBACK_CATEGORIES,
    staleTime: 10 * 60 * 1000,
  })
}
