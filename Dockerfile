ARG GIT_COMMIT=unknown

# ── Stage 1: Build the Vue SPA ────────────────────────────────────────────────
# outDir in vite.config.js is '../dist' relative to the frontend project root,
# so the build lands at /dist (one level above WORKDIR /build).
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY brewgen/frontend/package*.json ./
RUN npm ci
COPY brewgen/frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim-bookworm
ARG GIT_COMMIT
LABEL org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.source="https://github.com/ConnorGriffin/brewgen"

WORKDIR /app

# Install runtime dependencies from the manifest. PuLP bundles its own CBC
# binary; no system solver package is needed.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

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
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "brewgen.backend.views:app"]
