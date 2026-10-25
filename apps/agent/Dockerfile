# Multi-stage Dockerfile for Epoxa LiveKit Voice Agent Worker
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4.10 /uv /bin/uv

COPY pyproject.toml /build/
COPY packages/core /build/packages/core
COPY apps/agent /build/apps/agent

ENV UV_COMPILE_BYTECODE=1
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python /build/packages/core /build/apps/agent

# Final Stage
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

RUN groupadd -g 1001 epoxa && \
    useradd -u 1001 -g epoxa -m epoxa

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY packages/core /app/packages/core
COPY apps/agent /app/apps/agent

USER epoxa

# Long-lived LiveKit worker process
CMD ["python", "-m", "epoxa_agent.main", "start"]
