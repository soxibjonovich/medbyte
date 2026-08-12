import { useRef, useState, useEffect } from 'react'
import { Mic, Square, Play, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'

type RecorderState = 'idle' | 'recording' | 'recorded'

export function VoiceRecorder({ onAudioReady }: { onAudioReady: (file: File | null) => void }) {
  const [state, setState] = useState<RecorderState>('idle')
  const [elapsed, setElapsed] = useState(0)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef<number>(0)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const drawWaveform = () => {
    const canvas = canvasRef.current
    const analyser = analyserRef.current
    if (!canvas || !analyser) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const data = new Uint8Array(analyser.fftSize)
    analyser.getByteTimeDomainData(data)

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const barCount = 48
    const barWidth = canvas.width / barCount
    for (let i = 0; i < barCount; i++) {
      const idx = Math.floor((i / barCount) * data.length)
      const value = (data[idx] - 128) / 128 // -1..1
      const height = Math.max(2, Math.abs(value) * canvas.height)
      const x = i * barWidth
      const y = (canvas.height - height) / 2
      ctx.fillStyle = '#16a34a'
      ctx.fillRect(x + 1, y, barWidth - 2, height)
    }
    rafRef.current = requestAnimationFrame(drawWaveform)
  }

  const start = async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : undefined,
      })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        const url = URL.createObjectURL(blob)
        setAudioUrl(url)
        onAudioReady(new File([blob], `voice-${Date.now()}.webm`, { type: recorder.mimeType }))
        analyserRef.current = null
        audioCtx.close()
        stream.getTracks().forEach((t) => t.stop())
      }

      recorder.start()
      setState('recording')
      setElapsed(0)
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
      drawWaveform()
    } catch {
      setError('Microphone access denied. You can still submit text feedback.')
    }
  }

  const stop = () => {
    mediaRecorderRef.current?.stop()
    if (timerRef.current) clearInterval(timerRef.current)
    cancelAnimationFrame(rafRef.current)
    setState('recorded')
  }

  const clear = () => {
    setAudioUrl(null)
    setState('idle')
    setElapsed(0)
    onAudioReady(null)
  }

  const formatTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  return (
    <div className="rounded-xl border p-4">
      <div className="flex items-center gap-3">
        <canvas
          ref={canvasRef}
          className="h-12 flex-1 rounded-lg bg-muted"
          width={320}
          height={48}
        />
        <span className="font-mono text-sm tabular-nums">{formatTime(elapsed)}</span>
      </div>

      {state === 'idle' && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button type="button" onClick={start} variant="secondary" size="sm">
            <Mic className="size-4" /> Record voice feedback
          </Button>
          {error && <span className="text-xs text-destructive">{error}</span>}
        </div>
      )}

      {state === 'recording' && (
        <div className="mt-3 flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs font-medium text-destructive">
            <span className="size-2 animate-pulse rounded-full bg-destructive" /> Recording…
          </span>
          <Button type="button" onClick={stop} size="sm" variant="destructive">
            <Square className="size-4" /> Stop
          </Button>
        </div>
      )}

      {state === 'recorded' && audioUrl && (
        <div className="mt-3 flex items-center gap-2">
          <audio controls src={audioUrl} className="h-9 flex-1" />
          <Button type="button" variant="ghost" size="icon-sm" onClick={clear} aria-label="Re-record">
            <Trash2 className="size-4" />
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={start}>
            <Play className="size-4" /> Re-record
          </Button>
        </div>
      )}
    </div>
  )
}
