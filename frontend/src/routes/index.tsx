import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Search, Sparkles, Trophy, ArrowRight, Stethoscope } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { HospitalCard } from '@/components/shared/hospital-card'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { useCategories } from '@/hooks/useCategories'
import { hospitalsApi } from '@/lib/api'
import { Link } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const { data: categories } = useCategories()

  const featured = useQuery({
    queryKey: ['hospitals', 'featured'],
    queryFn: () => hospitalsApi.list({ sort: 'rating', limit: 6 }),
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    navigate({ to: '/leaderboard', search: { q: query.trim() } })
  }

  return (
    <div>
      <section className="border-b bg-gradient-to-b from-primary/5 to-background">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
          <div className="mx-auto max-w-2xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-medium">
              <Sparkles className="size-3.5" />
              AI-powered symptom triage & queue booking
            </span>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
              Find the right doctor, skip the queue.
            </h1>
            <p className="mt-4 text-muted-foreground">
              Book and pay for a doctor's queue slot in advance, get AI-driven recommendations, and
              earn discounts for sharing your feedback.
            </p>

            <form onSubmit={submit} className="mt-8 flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search hospitals or describe your symptoms…"
                  className="h-11 pl-9"
                />
              </div>
              <Button type="submit" size="lg" className="h-11">
                Search
              </Button>
            </form>

            <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-sm">
              <span className="text-muted-foreground">Popular:</span>
              {(categories ?? []).slice(0, 5).map((c) => (
                <Button
                  key={c.id}
                  variant="ghost"
                  size="sm"
                  className="rounded-full border"
                  onClick={() =>
                    navigate({ to: '/leaderboard', search: { category: c.id } })
                  }
                >
                  {c.name}
                </Button>
              ))}
            </div>
          </div>

          <div className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-3">
            <Card className="items-center gap-1 py-4 text-center">
              <Trophy className="size-6 text-primary" />
              <CardContent className="px-2">
                <p className="font-medium">Ranked leaderboard</p>
                <p className="text-sm text-muted-foreground">Best hospitals by score</p>
              </CardContent>
            </Card>
            <Card className="items-center gap-1 py-4 text-center">
              <Stethoscope className="size-6 text-primary" />
              <CardContent className="px-2">
                <p className="font-medium">AI doctor matching</p>
                <p className="text-sm text-muted-foreground">Symptom → best-fit doctors</p>
              </CardContent>
            </Card>
            <Card className="items-center gap-1 py-4 text-center">
              <Sparkles className="size-6 text-primary" />
              <CardContent className="px-2">
                <p className="font-medium">Feedback rewards</p>
                <p className="text-sm text-muted-foreground">Discounts for every visit</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Featured hospitals</h2>
          <Button variant="ghost" size="sm" render={<Link to="/leaderboard" />}>
            View all <ArrowRight className="size-4" />
          </Button>
        </div>

        {featured.isPending ? (
          <PageLoader />
        ) : featured.isError ? (
          <EmptyState
            title="Could not load hospitals"
            description="The hospitals service may be offline. Try again later."
          />
        ) : (featured.data?.length ?? 0) === 0 ? (
          <EmptyState title="No hospitals yet" description="Hospitals will appear here once added." />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(featured.data ?? []).map((h, i) => (
              <HospitalCard key={h.id} hospital={h} index={i} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
