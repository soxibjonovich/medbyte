import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Bot, User, Send, AlertTriangle, ShieldAlert, CalendarPlus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RatingStars } from '@/components/shared/rating-stars'
import { Spinner } from '@/components/shared/loader'
import { useCategories } from '@/hooks/useCategories'
import { aiApi, hospitalsApi } from '@/lib/api'
import { classifySymptoms, hasRedFlagSymptoms, scoreDoctors, type RankedDoctor } from '@/lib/symptom-ranker'
import type { DoctorSummary } from '@/lib/types'

export const Route = createFileRoute('/ai-chat')({
  component: AIChatPage,
})

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  doctors?: RankedDoctor[]
  redFlag?: boolean
}

const SUGGESTIONS = [
  'I have a persistent headache',
  'My child has a fever',
  'Chest pain when exercising',
  'Toothache for two days',
]

function composeReply(reply: string, matched: string[], doctors: RankedDoctor[]): string {
  const parts = [reply]

  if (matched.length > 0) {
    parts.push(`Based on your description, your symptoms are most likely related to ${matched.join(' or ')}.`)
  }

  if (doctors.length > 0) {
    parts.push(
      'Here are the top-rated doctors I matched for you:',
      doctors
        .map(
          (d, i) =>
            `${i + 1}. ${d.doctor.full_name} — ${d.categoryName} at ${d.hospitalName} (${d.city}), ${d.doctor.experience_years} years of experience, rated ${d.doctor.rating_avg.toFixed(1)}/5.`,
        )
        .join('\n'),
      'Tap the "Book" button next to any doctor to reserve a queue slot in advance.',
    )
  } else {
    parts.push(
      "I couldn't find a matching doctor right now. Try describing your symptoms differently or browse the leaderboard to compare top-rated hospitals near you.",
    )
  }

  parts.push(
    'Remember, these suggestions are informational and not a medical diagnosis. If symptoms persist or get worse, please see a doctor in person.',
  )

  return parts.join('\n\n')
}

function AIChatPage() {
  const { data: categories } = useCategories()
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'intro',
      role: 'assistant',
      text: "Hello! I'm MedByte Assistant. Describe your symptoms and I'll recommend the best-fit doctors nearby. Please remember this is not a medical diagnosis.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)

  const allHospitals = useQuery({
    queryKey: ['hospitals', 'all'],
    queryFn: () => hospitalsApi.list({ sort: 'rating', limit: 200 }),
    enabled: false,
  })

  const recommendDoctors = async (symptoms: string): Promise<RankedDoctor[]> => {
    const matched = classifySymptoms(symptoms)
    const { data: hospitals } = await allHospitals.refetch()
    if (!hospitals) return []

    const top = hospitals.slice(0, 10)
    const details = await Promise.all(
      top.map((h) =>
        hospitalsApi.get(h.id).catch(() => null),
      ),
    )

    const candidates: {
      doctor: DoctorSummary
      categoryName: string
      hospitalName: string
      hospitalId: number
      city: string
    }[] = []

    for (const detail of details) {
      if (!detail) continue
      for (const doctor of detail.doctors) {
        const cat = categories?.find((c) => c.id === doctor.medical_category_id)
        if (!cat) continue
        if (matched.length > 0 && !matched.includes(cat.name)) continue
        candidates.push({
          doctor,
          categoryName: cat.name,
          hospitalName: detail.name,
          hospitalId: detail.id,
          city: detail.city,
        })
      }
    }

    return scoreDoctors(candidates).slice(0, 5)
  }

  const send = async (text?: string) => {
    const content = (text ?? input).trim()
    if (!content || loading) return
    setInput('')

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', text: content },
    ])
    setLoading(true)

    try {
      const { reply, conversation_id } = await aiApi.chat({
        message: content,
        conversation_id: conversationId,
      })
      if (conversation_id) setConversationId(conversation_id)

      const redFlag = hasRedFlagSymptoms(content)
      const matched = classifySymptoms(content)
      const doctors = await recommendDoctors(content)

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: composeReply(reply, matched, doctors),
          doctors,
          redFlag,
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: "Sorry, I ran into a problem reaching the hospital data. Please try again in a moment.",
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-medium">
          <Bot className="size-3.5" /> Symptom triage
        </span>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">AI Assistant</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Describe your symptoms and get ranked doctor suggestions.
        </p>
      </div>

      <div className="flex flex-col gap-4 rounded-2xl border p-4">
        <div className="flex max-h-[55vh] flex-col gap-4 overflow-y-auto pr-1">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner /> Thinking…
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <Button key={s} variant="outline" size="sm" onClick={() => send(s)} disabled={loading}>
              {s}
            </Button>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
          className="flex gap-2"
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. I have a headache and dizziness…"
            rows={2}
            className="resize-none"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
          />
          <Button type="submit" size="icon" className="size-11 shrink-0" disabled={loading}>
            <Send className="size-4" />
          </Button>
        </form>
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
        <ShieldAlert className="mt-0.5 size-4 shrink-0" />
        <p>
          Suggestions are informational and are not a medical diagnosis. If you experience chest
          pain, difficulty breathing, severe bleeding or other emergency symptoms, call an ambulance
          (103) immediately.
        </p>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[85%] items-end gap-2">
          <div className="rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
            {message.text}
          </div>
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary">
            <User className="size-3.5" />
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-2">
      <span className="mt-1 flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary">
        <Bot className="size-3.5" />
      </span>
      <div className="flex max-w-[85%] flex-col gap-3">
        <div className="rounded-2xl rounded-tl-sm bg-muted px-4 py-2.5 text-sm">
          {message.text}
        </div>
        {message.redFlag && (
          <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <p>
              Some symptoms you described may be serious. Please seek urgent medical care if they
              persist.
            </p>
          </div>
        )}
        {message.doctors && message.doctors.length > 0 && (
          <div className="space-y-2">
            {message.doctors.map((d, i) => (
              <Card key={d.doctor.id} size="sm">
                <CardContent className="flex items-center gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{d.doctor.full_name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {d.categoryName} · {d.hospitalName} ({d.city})
                    </p>
                    <div className="mt-0.5">
                      <RatingStars value={d.doctor.rating_avg} />
                    </div>
                  </div>
                  <Badge variant="secondary" className="shrink-0">
                    {d.doctor.experience_years} yrs
                  </Badge>
                  <Button
                    size="sm"
                    className="shrink-0"
                    render={
                      <Link to="/booking/$doctorId" params={{ doctorId: String(d.doctor.id) }} />
                    }
                  >
                    <CalendarPlus className="size-4" /> Book
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        {message.doctors && message.doctors.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No matching doctors found right now. Try different words or check the leaderboard.
          </p>
        )}
      </div>
    </div>
  )
}
