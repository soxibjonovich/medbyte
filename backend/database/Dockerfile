FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/database ./backend/database

WORKDIR /app/backend/database
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS final

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /app /app
ENV PATH="/app/backend/database/.venv/bin:$PATH"

WORKDIR /app/backend/database

USER appuser

EXPOSE 8005

CMD ["uvicorn", "database.main:app", "--host", "0.0.0.0", "--port", "8005"]
