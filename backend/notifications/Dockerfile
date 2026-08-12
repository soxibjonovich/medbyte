FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/notifications ./backend/notifications

WORKDIR /app/backend/notifications
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS final

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /app /app
ENV PATH="/app/backend/notifications/.venv/bin:$PATH"

WORKDIR /app/backend/notifications

USER appuser

EXPOSE 8000

CMD ["uvicorn", "notifications.main:app", "--host", "0.0.0.0", "--port", "8000"]
