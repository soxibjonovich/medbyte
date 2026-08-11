# database

Shared SQLAlchemy models and async session/engine setup for anonfeedback services.

Currently implements the `User` entity (`id`, `full_name`, `phone`, `email`, `password_hash`, `role`, `created_at`).

Set `DATABASE_URL` to point at Postgres, e.g. `postgresql+asyncpg://user:pass@host:5432/db`.
