# database

Shared SQLAlchemy models and async session/engine setup for anonfeedback services.

Schema is managed with **Alembic** migrations (run automatically via `init_models()` on app startup). Never rely on `Base.metadata.create_all` — it won't alter existing tables.

Set `DATABASE_URL` to point at Postgres, e.g. `postgresql+asyncpg://user:pass@host:5432/db`.

## Migrations

```sh
# after changing a model, generate a new migration
alembic revision --autogenerate -m "describe change"

# apply (also runs on service startup)
alembic upgrade head

# check current version
alembic current
```

Because Alembic is wired for the async engine, run it with `DATABASE_URL` set to the live database.
