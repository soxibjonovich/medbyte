FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/feedback ./backend/feedback

WORKDIR /app/backend/feedback
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS final

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /app /app
ENV PATH="/app/backend/feedback/.venv/bin:$PATH"

WORKDIR /app/backend/feedback
RUN mkdir -p audio_uploads && chown appuser:appuser audio_uploads

USER appuser

EXPOSE 8000

CMD ["uvicorn", "feedback.main:app", "--host", "0.0.0.0", "--port", "8000"]
