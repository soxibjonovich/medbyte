import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import {
  Smile,
  Sparkles,
  Timer,
  Handshake,
  CalendarCheck,
  Tag,
  MessageSquareText,
  Clock,
  CheckCircle2,
  ArrowLeft,
  Star,
  ShieldCheck,
  MessagesSquare,
  AlarmClock,
  HeartHandshake,
  Stethoscope,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent } from '@/components/ui/card'
import { PageLoader } from '@/components/shared/loader'
import { EmptyState } from '@/components/shared/empty-state'
import { VoiceRecorder } from '@/components/shared/voice-recorder'
import { requireAuth } from '@/lib/guards'
import { databaseApi, feedbackApi, hospitalsApi } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

export const Route = createFileRoute('/feedback/$appointmentId')({
  beforeLoad: () => requireAuth(),
  component: FeedbackPage,
})

interface LikeTag {
  label: string
  icon: LucideIcon
}

const LIKE_TAGS: LikeTag[] = [
  { label: 'Friendly doctor', icon: Smile },
  { label: 'Clean facility', icon: Sparkles },
  { label: 'Short wait time', icon: Timer },
  { label: 'Polite staff', icon: Handshake },
  { label: 'Easy booking', icon: CalendarCheck },
  { label: 'Fair price', icon: Tag },
  { label: 'Clear explanation', icon: MessageSquareText },
  { label: 'On-time appointment', icon: Clock },
]

interface Characteristic {
  key: 'professionalism' | 'communication' | 'punctuality' | 'attentiveness' | 'effectiveness'
  label: string
  description: string
  icon: LucideIcon
}

const CHARACTERISTICS: Characteristic[] = [
  {
    key: 'professionalism',
    label: 'Professionalism',
    description: 'Polite, ethical and well-prepared',
    icon: ShieldCheck,
  },
  {
    key: 'communication',
    label: 'Communication',
    description: 'Clear explanations, easy to understand',
    icon: MessagesSquare,
  },
  {
    key: 'punctuality',
    label: 'Punctuality',
    description: 'On time — minimal waiting',
    icon: AlarmClock,
  },
  {
    key: 'attentiveness',
    label: 'Attentiveness',
    description: 'Listened carefully to your concerns',
    icon: HeartHandshake,
  },
  {
    key: 'effectiveness',
    label: 'Effectiveness',
    description: 'Diagnosis and advice were helpful',
    icon: Stethoscope,
  },
]

function FeedbackPage() {
  const { appointmentId } = Route.useParams()
  const id = Number(appointmentId)

  const [ratings, setRatings] = useState<Partial<Record<Characteristic['key'], number>>>({})
  const [tags, setTags] = useState<string[]>([])
  const [comment, setComment] = useState('')
  const [audio, setAudio] = useState<File | null>(null)
  const [consent, setConsent] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const ratedValues = CHARACTERISTICS.map((c) => ratings[c.key])
  const allRated = ratedValues.every((value) => value != null)
  const average =
    allRated && ratedValues.length > 0
      ? ratedValues.reduce<number>((sum, value) => sum + (value ?? 0), 0) / CHARACTERISTICS.length
      : 0

  const appointment = useQuery({
    queryKey: ['appointment', id],
    queryFn: () => databaseApi.getAppointment(id),
  })
  const hospital = useQuery({
    queryKey: ['hospital', appointment.data?.hospital_id],
    queryFn: () => hospitalsApi.get(appointment.data!.hospital_id!),
    enabled: appointment.data?.hospital_id != null,
  })

  const submit = useMutation({
    mutationFn: () =>
      feedbackApi.submit({
        appointment_id: id,
        professionalism: ratings.professionalism!,
        communication: ratings.communication!,
        punctuality: ratings.punctuality!,
        attentiveness: ratings.attentiveness!,
        effectiveness: ratings.effectiveness!,
        tags,
        text_comment: comment || null,
        audio_file: audio,
      }),
    onSuccess: () => setSubmitted(true),
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Submission failed'),
  })

  const toggleTag = (label: string) => {
    setTags((prev) => (prev.includes(label) ? prev.filter((t) => t !== label) : [...prev, label]))
  }

  if (appointment.isPending) return <PageLoader />
  if (appointment.isError || !appointment.data)
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <EmptyState title="Appointment not found" />
      </div>
    )

  if (submitted) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <CheckCircle2 className="size-14 text-emerald-500" />
            <h1 className="text-2xl font-semibold">Thank you for your feedback!</h1>
            <p className="max-w-sm text-sm text-muted-foreground">
              Your rating and {audio ? 'voice note' : 'review'} help other patients choose the right
              doctor. A discount reward from the admin will appear in your discounts wallet.
            </p>
            <div className="mt-2 flex gap-2">
              <Button render={<Link to="/discounts" />}>My discounts</Button>
              <Button variant="outline" render={<Link to="/profile/appointments" />}>
                Back to appointments
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Button variant="ghost" size="sm" className="mb-4" render={<Link to="/profile/appointments" />}>
        <ArrowLeft className="size-4" /> My appointments
      </Button>

      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">How was your visit?</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {hospital.data?.name ?? 'Your appointment'} · {formatDateTime(appointment.data.scheduled_at)}
        </p>
      </div>

      <div className="space-y-8">
        <section>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-medium">
              1. Rate the doctor <span className="text-destructive">*</span>
            </h2>
            <p className="text-sm text-muted-foreground">
              Average:{' '}
              <span className="font-semibold text-foreground">
                {allRated ? average.toFixed(1) : '—'}
              </span>
              /5
            </p>
          </div>
          <div className="space-y-4">
            {CHARACTERISTICS.map(({ key, label, description, icon: Icon }) => {
              const value = ratings[key] ?? 0
              return (
                <div key={key} className="rounded-xl border bg-muted/30 p-3">
                  <div className="flex items-center gap-2">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-background text-primary">
                      <Icon className="size-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{label}</p>
                      <p className="text-xs text-muted-foreground">{description}</p>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setRatings((prev) => ({ ...prev, [key]: i }))}
                        className="transition-transform hover:scale-110"
                        aria-label={`${label}: ${i} star${i > 1 ? 's' : ''}`}
                      >
                        <Star
                          className={cn(
                            'size-6',
                            i <= value ? 'fill-amber-400 text-amber-400' : 'fill-muted text-muted',
                          )}
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        <section>
          <h2 className="mb-3 font-medium">2. What did you like most?</h2>
          <div className="flex flex-wrap gap-2">
            {LIKE_TAGS.map(({ label, icon: Icon }) => {
              const active = tags.includes(label)
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => toggleTag(label)}
                  className={cn(
                    'flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors',
                    active
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'hover:border-ring hover:bg-muted',
                  )}
                >
                  <Icon className="size-4" />
                  {label}
                </button>
              )
            })}
          </div>
        </section>

        <section>
          <h2 className="mb-3 font-medium">3. Anything else? (optional)</h2>
          <Textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Share more about your experience…"
            rows={4}
          />
        </section>

        <section>
          <h2 className="mb-3 font-medium">4. Voice feedback (optional)</h2>
          <VoiceRecorder onAudioReady={setAudio} />
          {audio && (
            <label className="mt-3 flex items-start gap-2 text-sm">
              <Checkbox checked={consent} onCheckedChange={(c) => setConsent(Boolean(c))} />
              <span className="text-muted-foreground">
                I consent to my voice recording being stored and processed for transcription
                (speech-to-text) in line with the personal data protection law.
              </span>
            </label>
          )}
        </section>

        <Button
          size="lg"
          className="w-full"
          disabled={rating === 0 || submit.isPending || (audio != null && !consent)}
          onClick={() => submit.mutate()}
        >
          {submit.isPending ? 'Submitting…' : 'Submit feedback'}
        </Button>
        {audio != null && !consent && (
          <p className="text-center text-xs text-destructive">
            Please consent to voice recording before submitting.
          </p>
        )}
      </div>
    </div>
  )
}
