import { Link } from '@tanstack/react-router'
import { MapPin, Star } from 'lucide-react'

import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { HospitalImage } from '@/components/shared/hospital-image'
import { RatingStars } from '@/components/shared/rating-stars'
import type { Hospital } from '@/lib/types'

export function HospitalCard({ hospital, index = 0 }: { hospital: Hospital; index?: number }) {
  return (
    <Link to="/hospitals/$hospitalId" params={{ hospitalId: String(hospital.id) }} className="group">
      <Card className="h-full overflow-hidden transition-shadow hover:shadow-md">
        <HospitalImage name={hospital.name} index={index} className="h-36 w-full" />
        <CardContent className="pt-4">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium leading-snug group-hover:underline">{hospital.name}</h3>
            <div className="flex shrink-0 items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs font-medium">
              <Star className="size-3 fill-amber-400 text-amber-400" />
              {hospital.rating_avg.toFixed(1)}
            </div>
          </div>
          <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="size-3.5" />
            {hospital.address}
          </p>
        </CardContent>
        <CardFooter>
          <RatingStars value={hospital.rating_avg} />
        </CardFooter>
      </Card>
    </Link>
  )
}
