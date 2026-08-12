import { Link } from '@tanstack/react-router'
import { HeartPulse } from 'lucide-react'

export function AppFooter() {
  return (
    <footer className="border-t bg-muted/40">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <HeartPulse className="size-4" />
          </span>
          <span className="font-semibold">MedByte</span>
        </div>
        <div className="flex gap-6 text-sm text-muted-foreground">
          <Link to="/leaderboard" className="hover:text-foreground">
            Hospitals
          </Link>
          <Link to="/ai-chat" className="hover:text-foreground">
            AI Assistant
          </Link>
          <Link to="/register" className="hover:text-foreground">
            Sign up
          </Link>
        </div>
        <p className="text-sm text-muted-foreground">
          © {new Date().getFullYear()} MedByte · Book, pay, and share feedback.
        </p>
      </div>
    </footer>
  )
}
