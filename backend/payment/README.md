# payment

Payment checkout and provider webhooks. Talks to `database` over HTTP; owns no DB tables itself.

Providers: Stripe (implemented, demo mode), Payme and Uzum Bank (routes present, not implemented).

## Env vars

- `DATABASE_SERVICE_URL` — base URL of the database service
- `JWT_SECRET` — shared secret for verifying access tokens
- `STRIPE_SECRET_KEY` — Stripe secret API key (test mode for demo)
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook signing secret
- `PAYMENT_SUCCESS_URL` / `PAYMENT_CANCEL_URL` — redirect targets after Stripe Checkout
- `PAYMENT_DEMO_AMOUNT` — flat demo charge in minor currency units (default 2000 = $20.00)
- `PAYMENT_DEMO_CURRENCY` — default `usd`
