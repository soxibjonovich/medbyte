import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Trophy, ArrowUpDown, MapPin, Star, Search, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { useCategories } from '@/hooks/useCategories'
import { hospitalsApi } from '@/lib/api'
import type { HospitalLeaderboardEntry } from '@/lib/types'
import { Link } from '@tanstack/react-router'

interface LeaderboardSearch {
  q?: string
  category?: number
  city?: string
}

export const Route = createFileRoute('/leaderboard')({
  validateSearch: (search: Record<string, unknown>): LeaderboardSearch => ({
    q: typeof search.q === 'string' ? search.q : undefined,
    category: typeof search.category === 'number' ? search.category : undefined,
    city: typeof search.city === 'string' ? search.city : undefined,
  }),
  component: LeaderboardPage,
})

function LeaderboardPage() {
  const { q, category, city } = Route.useSearch()
  const navigate = useNavigate()
  const [sortBy, setSortBy] = useState<'score' | 'rating'>('score')
  const [localQuery, setLocalQuery] = useState(q ?? '')
  const { data: categories } = useCategories()

  const leaderboard = useQuery({
    queryKey: ['leaderboard', category],
    queryFn: () => hospitalsApi.leaderboard(category),
  })

  const cities = useMemo(() => {
    const list = leaderboard.data ?? []
    return [...new Set(list.map((h) => h.city))].sort()
  }, [leaderboard.data])

  const setSearch = (patch: Partial<LeaderboardSearch>) => {
    navigate({
      to: '/leaderboard',
      search: (prev: LeaderboardSearch) => ({ ...prev, ...patch }),
    })
  }

  const rows = useMemo(() => {
    let list = [...(leaderboard.data ?? [])]
    if (q) list = list.filter((h) => h.name.toLowerCase().includes(q.toLowerCase()))
    if (city) list = list.filter((h) => h.city === city)
    if (sortBy === 'rating') list.sort((a, b) => b.rating_avg - a.rating_avg)
    else list.sort((a, b) => b.weighted_score - a.weighted_score)
    return list.map((h, i) => ({ ...h, rank: i + 1 }))
  }, [leaderboard.data, q, city, sortBy])

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearch({ q: localQuery.trim() || undefined })
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-8 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Trophy className="size-5" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold">Hospital leaderboard</h1>
            <p className="text-sm text-muted-foreground">
              Ranked by a weighted score of reputation and distance.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <form onSubmit={submitSearch} className="relative max-w-md">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={localQuery}
              onChange={(e) => setLocalQuery(e.target.value)}
              placeholder="Search by hospital name…"
              className="pl-9"
            />
          </form>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant={category === undefined ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSearch({ category: undefined })}
            >
              All
            </Button>
            {(categories ?? []).map((c) => (
              <Button
                key={c.id}
                variant={category === c.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSearch({ category: c.id })}
              >
                {c.name}
              </Button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border px-1.5 py-1">
              <Button
                variant={sortBy === 'score' ? 'secondary' : 'ghost'}
                size="xs"
                onClick={() => setSortBy('score')}
              >
                <ArrowUpDown className="size-3" /> Score
              </Button>
              <Button
                variant={sortBy === 'rating' ? 'secondary' : 'ghost'}
                size="xs"
                onClick={() => setSortBy('rating')}
              >
                <Star className="size-3" /> Rating
              </Button>
            </div>

            <select
              value={city ?? ''}
              onChange={(e) => setSearch({ city: e.target.value || undefined })}
              className="h-8 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">All cities</option>
              {cities.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            {(q || city || category !== undefined) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate({ to: '/leaderboard', search: {} })}
              >
                <X className="size-3.5" /> Clear filters
              </Button>
            )}
          </div>
        </div>
      </div>

      {leaderboard.isPending ? (
        <PageLoader />
      ) : leaderboard.isError ? (
        <EmptyState
          title="Could not load the leaderboard"
          description="The hospitals service may be offline. Try again later."
        />
      ) : rows.length === 0 ? (
        <EmptyState title="No hospitals found" description="Try adjusting your filters." />
      ) : (
        <div className="divide-y rounded-xl border">
          {rows.map((entry: HospitalLeaderboardEntry & { rank: number }) => (
            <RankRow key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  )
}

function RankRow({ entry }: { entry: HospitalLeaderboardEntry & { rank: number } }) {
  return (
    <Link
      to="/hospitals/$hospitalId"
      params={{ hospitalId: String(entry.id) }}
      className="flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-muted/50"
    >
      <span className="w-8 shrink-0 text-center text-lg font-semibold text-muted-foreground">
        {entry.rank <= 3 ? (
          <span
            className={
              entry.rank === 1
                ? 'text-amber-500'
                : entry.rank === 2
                  ? 'text-slate-400'
                  : 'text-orange-400'
            }
          >
            {entry.rank}
          </span>
        ) : (
          entry.rank
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{entry.name}</p>
        <p className="flex items-center gap-1 text-sm text-muted-foreground">
          <MapPin className="size-3" /> {entry.city}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <Badge variant="secondary">
          <Star className="size-3 fill-amber-400 text-amber-400" /> {entry.rating_avg.toFixed(1)}
        </Badge>
        <span className="text-xs text-muted-foreground">
          score {entry.weighted_score.toFixed(2)}
        </span>
      </div>
    </Link>
  )
}
