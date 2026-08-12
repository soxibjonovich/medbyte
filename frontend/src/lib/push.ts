// Web Push is removed from the frontend. The backend still supports email/in-app notifications.

export function pushSupported(): boolean {
  return false
}

export async function requestNotificationPermission(): Promise<boolean> {
  return false
}

export async function getOrCreatePushSubscription(): Promise<PushSubscription | null> {
  return null
}

export async function sendSubscriptionToBackend(): Promise<void> {
  return
}

export function preflightPushSubscription(): Promise<PushSubscription | null> {
  return Promise.resolve(null)
}
