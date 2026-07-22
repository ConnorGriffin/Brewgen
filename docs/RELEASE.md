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

### Awaiting the production image (#47)

The container build, scan, and publish steps are gated on the production
`Dockerfile`, which is delivered by issue #47. Until that Dockerfile exists the
container steps are a green no-op (the code gate still runs in full). The moment
the Dockerfile lands, the same pipeline builds, scans, and publishes with no
further change. If #47's image reports its running commit through a mechanism
other than the `GIT_COMMIT` build arg / OCI revision label described above, that
is a coordination point to reconcile with #47 — not something to invent here.

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
