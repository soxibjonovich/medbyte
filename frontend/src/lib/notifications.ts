import { databaseApi, notificationsApi } from './api'
import { getOrCreatePushSubscription, sendSubscriptionToBackend } from './push'
import type { User } from './types'

export async function notifyLogin(
  user: User,
  subscriptionPromise?: Promise<PushSubscription | null>,
) {
  const first = user.full_name.trim().split(/\s+/)[0] || user.username
  const title = `Welcome back, ${first}!`
  const message = `You're signed in to MedByte. New discounts and updates are waiting for you.`

  // Register/refresh the push subscription for this user (best-effort).
  const subscription = (await subscriptionPromise) ?? (await getOrCreatePushSubscription())
  if (subscription) {
    await sendSubscriptionToBackend(subscription).catch(() => {})
  }

  // In-app notification + web push through the notifications service.
  try {
    await notificationsApi.send({ title, message })
  } catch {
    // Fallback: keep at least the in-app record visible.
    try {
      await databaseApi.createNotification({ user_id: user.id, title, message })
    } catch {
      /* best-effort */
    }
  }
}
