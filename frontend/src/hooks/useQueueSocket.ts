import { useEffect, useRef, useState } from 'react'
import { queueApi } from '@/lib/api'
import type { QueueEntry } from '@/lib/types'

interface QueueEntryCreatedMessage {
  type: 'queue_entry_created'
  entry: QueueEntry
}

const MAX_BACKOFF_MS = 15_000

/**
 * Opens the live queue websocket (GET /api/queue/ws?token=...), listens for
 * `queue_entry_created` events, and reconnects with a simple capped backoff
 * on close. The server never expects messages back — this is listen-only.
 */
export function useQueueSocket(onEntryCreated: (entry: QueueEntry) => void) {
  const [connected, setConnected] = useState(false)
  const onEntryCreatedRef = useRef(onEntryCreated)

  useEffect(() => {
    onEntryCreatedRef.current = onEntryCreated
  }, [onEntryCreated])

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let attempt = 0
    let stopped = false

    const connect = () => {
      if (stopped) return
      socket = new WebSocket(queueApi.wsUrl())

      socket.onopen = () => {
        attempt = 0
        setConnected(true)
      }

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as QueueEntryCreatedMessage
          if (message.type === 'queue_entry_created' && message.entry) {
            onEntryCreatedRef.current(message.entry)
          }
        } catch {
          /* ignore malformed messages */
        }
      }

      socket.onclose = (event) => {
        setConnected(false)
        // 4401 (missing/invalid token) and 4403 (role not allowed) won't resolve by
        // retrying — the user needs to re-authenticate or isn't staff/admin.
        if (stopped || event.code === 4401 || event.code === 4403) return
        const delay = Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS)
        attempt += 1
        reconnectTimer = setTimeout(connect, delay)
      }

      socket.onerror = () => {
        socket?.close()
      }
    }

    connect()

    return () => {
      stopped = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [])

  return { connected }
}
