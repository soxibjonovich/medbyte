FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/stt-worker ./backend/stt-worker

WORKDIR /app/backend/stt-worker
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS final

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /app /app
ENV PATH="/app/backend/stt-worker/.venv/bin:$PATH"

WORKDIR /app/backend/stt-worker

USER appuser

EXPOSE 8000

CMD ["uvicorn", "stt_worker.main:app", "--host", "0.0.0.0", "--port", "8000"]
