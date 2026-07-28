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

# ── Stage 2: Install Python dependencies ─────────────────────────────────────
# The dev variant supplies pip. Build the venv WITHOUT pip and install into it
# with the builder's own pip (--python), so the shipped venv holds only the
# hash-checked runtime closure. Keeping pip out of /app/venv closes a blind spot:
# pip-audit only sees the declared project dependencies, so a pip/setuptools/wheel
# advisory would escape that audit yet be flagged by the image scan. See #70.
# Digest pinned 2026-07-28 (== :latest-dev, ships python 3.14.6-r4); see docs/RELEASE.md.
FROM cgr.dev/chainguard/python:latest-dev@sha256:3be081f6cae8f1678609f6ae00b1dfebd6819c3ce75b7c574663af84afe99cc4 AS python-builder
WORKDIR /app
RUN python -m venv --without-pip /app/venv
COPY requirements.lock ./
RUN pip --python /app/venv/bin/python install --no-cache-dir --require-hashes -r requirements.lock

# ── Stage 3: Minimal Python runtime ───────────────────────────────────────────
# Wolfi supplies glibc for PuLP's bundled CBC binary without carrying a Debian
# userland, shell, package manager, or build tools into production.
# Digest pinned 2026-07-28 (== :latest, ships python 3.14.6-r4, which fixes
# CVE-2026-15308); see docs/RELEASE.md. The free tier serves only :latest, so
# refresh this pin when the scan flags an aged base rather than expecting an
# older digest to keep pulling.
FROM cgr.dev/chainguard/python:latest@sha256:b3d3fbb8b9fe48950bab73d49bffa7496ff6f8a46ba570b302fc366f1396011a AS runtime
ARG GIT_COMMIT
LABEL org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.source="https://github.com/ConnorGriffin/brewgen"

WORKDIR /app

# Copy only the exact, hash-checked runtime dependency closure.
COPY --from=python-builder /app/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

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

# Chainguard's runtime is non-root by default; keep it explicit here.
USER nonroot

EXPOSE 5000

# Cheap liveness probe: process-up only, no solver work.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/app/venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz').read()"]

# Single worker matches the locked single-trusted-hop assumption documented in
# the resource-bounds section of docs/RELEASE.md. Its request threads only carry
# a burst to the application's one-slot admission guard; they add no solver
# capacity.
ENV GUNICORN_CMD_ARGS="--workers 1 --worker-class gthread --threads 24 --bind 0.0.0.0:5000 --access-logfile - --error-logfile - --no-control-socket"
ENTRYPOINT ["/app/venv/bin/gunicorn"]
CMD ["brewgen.backend.views:app"]

# Exercise the built SPA and API through Gunicorn before the final stage can be
# produced. The existing image CI job therefore runs this public smoke test
# without duplicating container-build logic in the workflow.
FROM runtime AS smoke-test
COPY scripts/container_smoke.py /tmp/container_smoke.py
RUN ["/app/venv/bin/python", "/tmp/container_smoke.py", "--launch", "--port", "5000", "--sentinel", "/tmp/container-smoke/passed"]

FROM runtime AS production
RUN --mount=type=bind,from=smoke-test,source=/tmp/container-smoke,target=/tmp/container-smoke \
    ["/usr/bin/python", "-c", "from pathlib import Path; assert Path('/tmp/container-smoke/passed').is_file()"]
