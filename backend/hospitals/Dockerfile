FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/hospitals ./backend/hospitals

WORKDIR /app/backend/hospitals
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS final

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /app /app
ENV PATH="/app/backend/hospitals/.venv/bin:$PATH"

WORKDIR /app/backend/hospitals

USER appuser

EXPOSE 8000

CMD ["uvicorn", "hospitals.main:app", "--host", "0.0.0.0", "--port", "8000"]
