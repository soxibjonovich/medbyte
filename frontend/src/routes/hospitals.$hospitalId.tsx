import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, MapPin, Phone, Clock, Navigation, Star, CalendarPlus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { HospitalImage } from '@/components/shared/hospital-image'
import { RatingStars } from '@/components/shared/rating-stars'
import { CategoryBadge } from '@/components/shared/category-badge'
import { MapEmbed, getDirectionsUrl } from '@/components/shared/map-embed'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { hospitalsApi } from '@/lib/api'

export const Route = createFileRoute('/hospitals/$hospitalId')({
  component: HospitalDetailPage,
})

function HospitalDetailPage() {
  const { hospitalId } = Route.useParams()
  const id = Number(hospitalId)

  const { data, isPending, isError } = useQuery({
    queryKey: ['hospital', id],
    queryFn: () => hospitalsApi.get(id),
  })

  if (isPending) return <PageLoader />
  if (isError || !data)
    return (
      <div className="mx-auto max-w-6xl px-4 py-10">
        <EmptyState title="Hospital not found" description="This hospital may have been removed." />
      </div>
    )

  return (
    <div>
      <div className="mx-auto max-w-6xl px-4 py-6">
        <Button variant="ghost" size="sm" render={<Link to="/leaderboard" />}>
          <ArrowLeft className="size-4" /> Back to leaderboard
        </Button>
      </div>

      <div className="mx-auto max-w-6xl px-4">
        <HospitalImage name={data.name} className="h-56 w-full rounded-2xl sm:h-72" />

        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">{data.name}</h1>
            <p className="mt-1 flex items-center gap-1 text-muted-foreground">
              <MapPin className="size-4" />
              {data.address} · {data.city}
            </p>
            <div className="mt-2 flex items-center gap-3">
              <RatingStars value={data.rating_avg} size="md" />
              <Badge variant="secondary">
                <Star className="size-3 fill-amber-400 text-amber-400" />
                {data.rating_avg.toFixed(1)}
              </Badge>
            </div>
          </div>
          <a
            href={getDirectionsUrl(data.lat, data.lng)}
            target="_blank"
            rel="noreferrer"
            className="shrink-0"
          >
            <Button variant="outline">
              <Navigation className="size-4" /> Get directions
            </Button>
          </a>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_380px]">
          <div>
            <h2 className="mb-4 text-lg font-semibold">Doctors ({data.doctors.length})</h2>
            {data.doctors.length === 0 ? (
              <EmptyState
                title="No doctors listed"
                description="Doctor profiles will appear here once added."
              />
            ) : (
              <div className="space-y-3">
                {data.doctors.map((doctor) => (
                  <Card key={doctor.id}>
                    <CardContent className="flex items-center gap-4">
                      <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-semibold">
                        {doctor.full_name
                          .split(' ')
                          .map((p) => p[0])
                          .slice(0, 2)
                          .join('')}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{doctor.full_name}</p>
                        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                          <CategoryBadge categoryId={doctor.medical_category_id} />
                          <span>{doctor.experience_years} yrs experience</span>
                        </div>
                        <div className="mt-1">
                          <RatingStars value={doctor.rating_avg} />
                        </div>
                      </div>
                      <Button
                        size="sm"
                        render={
                          <Link to="/booking/$doctorId" params={{ doctorId: String(doctor.id) }} />
                        }
                      >
                        <CalendarPlus className="size-4" /> Book
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="size-4" /> Working hours
                </CardTitle>
              </CardHeader>
              <CardContent>
                {Object.keys(data.working_hours ?? {}).length === 0 ? (
                  <p className="text-sm text-muted-foreground">Not specified</p>
                ) : (
                  <dl className="space-y-1.5 text-sm">
                    {Object.entries(data.working_hours ?? {}).map(([day, hours]) => (
                      <div key={day} className="flex justify-between gap-4">
                        <dt className="text-muted-foreground capitalize">{day}</dt>
                        <dd>{hours}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Phone className="size-4" /> Phone numbers
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(data.phone_numbers?.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground">Not specified</p>
                ) : (
                  <div className="space-y-1.5">
                    {data.phone_numbers.map((phone) => (
                      <a
                        key={phone}
                        href={`tel:${phone}`}
                        className="flex items-center gap-2 text-sm text-primary hover:underline"
                      >
                        <Phone className="size-3.5" /> {phone}
                      </a>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="size-4" /> Location
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <MapEmbed lat={data.lat} lng={data.lng} className="h-56 w-full rounded-b-xl" />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
