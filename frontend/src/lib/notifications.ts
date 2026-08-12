import { databaseApi } from './api'
import type { User } from './types'

export async function notifyLogin(user: User) {
  const first = user.full_name.trim().split(/\s+/)[0] || user.username
  const title = `Welcome back, ${first}!`
  const message = `You're signed in to MedByte. New discounts and updates are waiting for you.`

  try {
    await databaseApi.createNotification({ user_id: user.id, title, message })
  } catch {
    /* best-effort */
  }
}
