# Releasing Brewgen

Brewgen ships through the same pull-based boundary as the other public apps:
CI builds and proves an image, publishes it to GHCR, and the serving host pulls
it. Nothing is pushed into the home network. This document covers image
identity, normal publication, rollback, and how to confirm which image a running
container is serving.

## Image identity

Images live at `ghcr.io/connorgriffin/brewgen` under two kinds of tag:

- **`:<full-commit-sha>` — immutable.** One tag per released commit. It always
  points at the exact image built and scanned from that source commit and is
  never moved. This is the source of truth for "what is this artifact".
- **`:release` — mutable.** The single tag the serving host follows. It is an
  alias that points at whichever commit image is currently live. Normal
  publication and rollback both work by moving `:release` onto an immutable
  commit tag.

Every image carries its source commit in the `org.opencontainers.image.revision`
label and receives it as the `GIT_COMMIT` build argument, so the artifact can
report the commit it was built from independently of its tag.

## Normal publication (`.github/workflows/ci.yml`)

CI runs on every push to `main` and on every pull request. The gate must pass
before anything is published:

1. Backend suite (`pytest tests`) on Python 3.11 and 3.14.
2. Frontend suite and production build (`npm test` + `npm run build`).
3. Dependency audit — Python (`pip-audit`) and JavaScript (`npm audit`).
4. Code scanning — CodeQL for Python and JavaScript/TypeScript.
5. Container scan — the exact `linux/amd64` image is built and scanned; any
   **critical or high** finding fails the job and blocks publication.

Only a green push to `main` on `ConnorGriffin/brewgen` publishes. The image
built and scanned in that run is pushed under its immutable commit tag, and
`:release` is moved onto the same image. Pull requests and forks run the entire
gate — including the container scan — but the login and push steps are skipped,
so they perform zero registry writes.

## Running the image locally

The image needs no secrets and no persistent volumes. The only writable path
required at runtime is `/tmp`, which the CBC solver uses for temporary `.lp` and
`.sol` files.

```sh
docker run --rm \
  --read-only \
  --tmpfs /tmp \
  --user nonroot \
  --cpus 1 \
  --memory 512m \
  --pids-limit 64 \
  --log-driver local --log-opt max-size=10m --log-opt max-file=3 \
  -p 5000:5000 \
  ghcr.io/connorgriffin/brewgen:release
```

Resource bounds:

- **Workers:** 1 gunicorn worker. Matches the single-trusted-hop assumption and
  keeps the CBC solver's temp-file footprint bounded.
- **CPU:** `--cpus 1` — one virtual CPU. The solver is CPU-bound; this is the
  expected ceiling for normal requests.
- **Memory:** `--memory 512m` — covers the solver's ILP working set plus the
  JSON data files loaded at startup.
- **Processes:** `--pids-limit 64` — one gunicorn master + one worker, with
  headroom for CBC child processes.
- **Logs:** written to stdout/stderr (gunicorn `--access-logfile -`);
  capped at 10 MB × 3 files via the `local` log driver so the host disk is
  never exhausted by access logs.
- **Read-only rootfs:** `/tmp` is the only writable mount. Python `.pyc` cache
  writes are suppressed by `PYTHONDONTWRITEBYTECODE=1` in the image.

To build locally from source:

```sh
docker build --platform linux/amd64 \
  --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
  -t brewgen:local .
```

To build the Linux image and exercise the SPA, API, source label, same-origin
boundary, health check, and grain-bill generation under the documented runtime
limits:

```sh
python3 scripts/container_smoke.py
```

## Rollback (`.github/workflows/rollback.yml`)

To move `release` back to an earlier commit, run the **Rollback release tag**
workflow (`workflow_dispatch`) and supply the full 40-character commit SHA.

The workflow:

1. Rejects any input that is not a full SHA reachable from `main`.
2. Retests that exact commit (backend + frontend) and rebuilds its image.
3. Rescans the image and blocks on any critical/high finding.
4. Republishes that commit's immutable image and moves `:release` onto it.

Forward release and rollback share a single concurrency group
(`brewgen-release-tag`), so the two can never move `:release` at the same time;
one waits for the other to finish.

## Verifying which image a container is serving

- **By tag on the host:** inspect the digest `:release` resolves to and compare
  it to the commit tag you expect:

  ```
  docker image inspect --format '{{index .RepoDigests 0}}' ghcr.io/connorgriffin/brewgen:release
  ```

- **By source commit:** read the revision label baked into the running image:

  ```
  docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' <container>
  ```

  That value is the source commit the artifact was built from, regardless of
  which mutable tag was used to pull it.
