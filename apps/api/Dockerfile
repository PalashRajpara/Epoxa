# Multi-stage Dockerfile for Epoxa FastAPI Backend Service
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4.10 /uv /bin/uv

COPY pyproject.toml /build/
COPY packages/core /build/packages/core
COPY apps/api /build/apps/api

ENV UV_COMPILE_BYTECODE=1
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python /build/packages/core /build/apps/api

# Final Stage
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

RUN groupadd -g 1001 epoxa && \
    useradd -u 1001 -g epoxa -m epoxa

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY packages/core /app/packages/core
COPY apps/api /app/apps/api

USER epoxa

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')" || exit 1

CMD ["uvicorn", "epoxa_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
