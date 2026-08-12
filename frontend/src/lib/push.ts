import { API, VAPID_PUBLIC_KEY } from './config'
import { useAuthStore } from '@/stores/auth'

function urlBase64ToUint8Array(base64Url: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64Url.length % 4)) % 4)
  const base64 = (base64Url + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const bytes = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  return bytes
}

function bytesMatch(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false
  return a.every((value, i) => value === b[i])
}

/** The VAPID key the backend signs with — must match the one the browser subscribed with. */
function applicationServerKeyMatches(subscription: PushSubscription): boolean {
  const current = subscription.options?.applicationServerKey
  if (!current) return true // some browsers omit it — don't force a resubscribe blindly
  const bytes = current instanceof ArrayBuffer ? new Uint8Array(current) : new Uint8Array(current)
  return bytesMatch(bytes, urlBase64ToUint8Array(VAPID_PUBLIC_KEY))
}

function bufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function pushSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

export async function requestNotificationPermission(): Promise<boolean> {
  if (!pushSupported()) return false
  if (Notification.permission === 'granted') return true
  if (Notification.permission === 'denied') return false
  const permission = await Notification.requestPermission()
  return permission === 'granted'
}

export async function getOrCreatePushSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null
  const granted = await requestNotificationPermission()
  if (!granted) return null
  try {
    const registration = await navigator.serviceWorker.register('/sw.js')
    await navigator.serviceWorker.ready
    let subscription = await registration.pushManager.getSubscription()
    if (subscription && !applicationServerKeyMatches(subscription)) {
      await subscription.unsubscribe().catch(() => {})
      subscription = null
    }
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      })
    }
    return subscription
  } catch {
    return null
  }
}

/** Send the browser push subscription to the backend for the current user. */
export async function sendSubscriptionToBackend(subscription: PushSubscription): Promise<void> {
  const token = useAuthStore.getState().token
  if (!token) return
  const p256dh = subscription.getKey('p256dh')
  const auth = subscription.getKey('auth')
  if (!p256dh || !auth) return

  const res = await fetch(`${API.notifications}/push-subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: {
        p256dh: bufferToBase64Url(p256dh),
        auth: bufferToBase64Url(auth),
      },
    }),
  })
  if (!res.ok) throw new Error('failed to register push subscription')
}

let pendingSubscription: Promise<PushSubscription | null> | null = null

/**
 * Start creating the push subscription right away (inside the user's click gesture,
 * before any network awaits) so mobile browsers don't reject the subscribe call.
 */
export function preflightPushSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return Promise.resolve(null)
  pendingSubscription = getOrCreatePushSubscription()
  return pendingSubscription
}
