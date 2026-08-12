FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/ai ./backend/ai

WORKDIR /app/backend/ai
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS final

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /app /app
ENV PATH="/app/backend/ai/.venv/bin:$PATH"

WORKDIR /app/backend/ai

USER appuser

EXPOSE 8000

CMD ["uvicorn", "ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
