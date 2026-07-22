# syntax=docker/dockerfile:1@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89

ARG GIT_COMMIT=unknown

# ── Stage 1: Build the Vue SPA ────────────────────────────────────────────────
# outDir in vite.config.js is '../dist' relative to the frontend project root,
# so the build lands at /dist (one level above WORKDIR /build).
FROM node:20-slim@sha256:3d0f05455dea2c82e2f76e7e2543964c30f6b7d673fc1a83286736d44fe4c41c AS frontend-builder
WORKDIR /build
COPY brewgen/frontend/package*.json ./
RUN npm ci
COPY brewgen/frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim-bookworm@sha256:28255a3ace7eb4c48bc1b57b90af29e1bc82b4fd6c60614a8e3dce61b87ff941 AS runtime
ARG GIT_COMMIT
LABEL org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.source="https://github.com/ConnorGriffin/brewgen"

WORKDIR /app

# Install the exact, hash-checked runtime dependency closure. PuLP bundles its
# own CBC binary; no system solver package is needed.
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

# Suppress .pyc writes so a --read-only rootfs never trips on cache dirs.
ENV PYTHONDONTWRITEBYTECODE=1
# Make the brewgen source importable as a namespace package from /app.
ENV PYTHONPATH=/app

# Copy Python source (no frontend, no build artifacts).
COPY brewgen/backend/ ./brewgen/backend/

# Copy the built SPA from the builder stage.
# Flask expects static_folder='../dist/static' and template_folder='../dist'
# relative to brewgen/backend/, so the dist tree lives at brewgen/dist/.
COPY --from=frontend-builder /dist/ ./brewgen/dist/

# Non-root service account.
RUN useradd --system --no-create-home --uid 1000 brewgen
USER brewgen

EXPOSE 5000

# Cheap liveness probe: process-up only, no solver work.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz').read()"

# Single worker matches the locked single-trusted-hop assumption documented in
# the resource-bounds section of docs/RELEASE.md.
ENV GUNICORN_CMD_ARGS="--workers 1 --bind 0.0.0.0:5000 --access-logfile - --error-logfile - --no-control-socket"
CMD ["gunicorn", "brewgen.backend.views:app"]

# Exercise the built SPA and API through Gunicorn before the final stage can be
# produced. The existing image CI job therefore runs this public smoke test
# without duplicating container-build logic in the workflow.
FROM runtime AS smoke-test
COPY scripts/container_smoke.py /tmp/container_smoke.py
RUN set -eu; \
    gunicorn brewgen.backend.views:app & \
    server_pid=$!; \
    trap 'kill "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true' 0; \
    python /tmp/container_smoke.py --port 5000; \
    mkdir /tmp/container-smoke; \
    touch /tmp/container-smoke/passed

FROM runtime AS production
RUN --mount=type=bind,from=smoke-test,source=/tmp/container-smoke,target=/tmp/container-smoke \
    test -f /tmp/container-smoke/passed
