import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Star, Mic, AudioLines } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { feedbackApi } from '@/lib/api'
import { useCategories } from '@/hooks/useCategories'
import { formatDateTime } from '@/lib/format'
import type { Feedback, FeedbackProcessingStatus } from '@/lib/types'

export const Route = createFileRoute('/admin/_admin/feedback')({
  component: AdminFeedbackPage,
})

const SENTIMENT_STYLES: Record<string, string> = {
  positive: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
  neutral: 'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300',
  negative: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300',
}

const PROCESSING_STYLES: Record<FeedbackProcessingStatus, string> = {
  pending: 'bg-slate-100 text-slate-600',
  processing: 'bg-amber-100 text-amber-700',
  done: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

function AdminFeedbackPage() {
  const { data: categories } = useCategories()
  const [sentiment, setSentiment] = useState<string>('all')
  const [selected, setSelected] = useState<Feedback | null>(null)

  const { data, isPending, isError } = useQuery({
    queryKey: ['admin', 'feedback', sentiment],
    queryFn: () =>
      feedbackApi.list(
        sentiment === 'all' ? {} : { sentiment: sentiment as 'positive' | 'neutral' | 'negative' },
      ),
  })

  const transcript = useQuery({
    queryKey: ['feedback', 'transcript', selected?.id],
    queryFn: () => feedbackApi.transcript(selected!.id),
    enabled: selected != null,
  })

  const rows = data ?? []

  return (
    <div>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Feedback</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Review patient feedback, transcripts and detected sentiment.
        </p>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {['all', 'positive', 'neutral', 'negative'].map((value) => (
          <Button
            key={value}
            variant={sentiment === value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSentiment(value)}
          >
            {value}
          </Button>
        ))}
      </div>

      {isPending ? (
        <PageLoader />
      ) : isError ? (
        <EmptyState title="Could not load feedback" />
      ) : rows.length === 0 ? (
        <div className="mt-6">
          <EmptyState title="No feedback yet" description="Patient feedback will appear here." />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rating</TableHead>
                <TableHead>Comment</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Audio</TableHead>
                <TableHead>Sentiment</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((feedback) => (
                <TableRow
                  key={feedback.id}
                  className="cursor-pointer"
                  onClick={() => setSelected(feedback)}
                >
                  <TableCell>
                    <span className="flex items-center gap-1">
                      <Star className="size-3.5 fill-amber-400 text-amber-400" />
                      {feedback.rating}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-72 truncate text-muted-foreground">
                    {feedback.text_comment ?? '—'}
                  </TableCell>
                  <TableCell>
                    {categories?.find((c) => c.id === feedback.category_id)?.name ?? '—'}
                  </TableCell>
                  <TableCell>
                    {feedback.audio_file ? (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <AudioLines className="size-3.5" /> recorded
                      </span>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell>
                    {feedback.sentiment ? (
                      <Badge className={SENTIMENT_STYLES[feedback.sentiment]}>
                        {feedback.sentiment}
                      </Badge>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={PROCESSING_STYLES[feedback.processing_status]}>
                      {feedback.processing_status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(feedback.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={selected != null} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Feedback #{selected?.id}</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex items-center gap-1 text-sm font-medium">
                  <Star className="size-4 fill-amber-400 text-amber-400" />
                  {selected.rating}/5
                </span>
                {selected.sentiment && (
                  <Badge className={SENTIMENT_STYLES[selected.sentiment]}>
                    {selected.sentiment}
                  </Badge>
                )}
                <Badge variant="outline">{selected.processing_status}</Badge>
              </div>

              {selected.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selected.tags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}

              {selected.text_comment && (
                <div className="rounded-lg bg-muted p-3 text-sm">{selected.text_comment}</div>
              )}

              <div>
                <p className="mb-1 flex items-center gap-1.5 text-sm font-medium">
                  <Mic className="size-4" /> Transcript
                </p>
                {transcript.isPending ? (
                  <PageLoader />
                ) : transcript.data?.transcript ? (
                  <p className="rounded-lg bg-muted p-3 text-sm">{transcript.data.transcript}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {selected.audio_file ? 'Transcription is processing…' : 'No voice feedback.'}
                  </p>
                )}
                {transcript.data?.keywords && transcript.data.keywords.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {transcript.data.keywords.map((keyword) => (
                      <Badge key={keyword} variant="outline">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
