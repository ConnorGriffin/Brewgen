# The anonymous-compute envelope

This is the implementation note for decision-map #10 (`docs/decision-maps/public-launch.md`):
the shared gate every public compute request passes through before any solver
work runs. It applies to the three public POST endpoints only — the focused
flavor-range check, the whole-brief feasibility check, and grain-bill
generation. The read-only GET endpoints and the SPA catch-all stay outside it.

## What every compute request passes through, in order

1. **Media type** — must be `application/json`, else **415**.
2. **Size** — the body is capped at **64 KiB (65 536 bytes)**; a larger body is
   **413** and is rejected *before* it is read into memory or a solver is built.
3. **JSON** — must parse, else **400**.
4. **Versioned brief contract** — a single strict schema: unknown fields,
   unknown or duplicate catalog slugs/categories/descriptors, non-finite
   numbers, inverted ranges, and over-cardinality lists are all **422**. Lists
   are capped at the shipped catalog's cardinality.
5. **Per-visitor rate limit** — **six requests per minute with a burst of two**,
   keyed by a daily-rotated in-memory hash of the client address with a
   ten-minute idle expiry. The seventh-in-a-burst is **429**. The key material
   is never logged or persisted.
6. **Concurrency** — at most **two** solver operations run at once, with **no
   queue**; a third concurrent request is **503 busy** immediately.

Only then does the operation run under the solver's own shared **1.8 s solver /
2.0 s end-to-end budget**. `partial` results return honestly as **200**;
`deadline_exceeded` and a no-slot refusal are **503**; `infeasible` is **422**.

All failures use `application/problem+json` with a stable machine `outcome` tag
and **no echoed input**. Every request emits exactly one aggregate log line
carrying only `{timestamp, request_id, operation, outcome, status, duration}`,
retained for seven days — never the brief, the address, the hash, headers,
cookies, user agents, referrers, or query strings.

## Deployment requirements (#11/#12/#16)

The limits above are **per container** and correct only under the runtime shape
the public-launch map locks:

- **One worker process.** The two-slot ceiling and the in-memory rate-limit
  store live in a single process. Do not run multiple workers behind one
  container without moving to shared state (explicitly out of scope here) — two
  workers would double the effective concurrency and split the rate-limit store.
- **Exactly one trusted proxy hop.** The client address is resolved with
  `ProxyFix(x_for=1)`; the deploy must place the API behind the single relay and
  forward exactly one `X-Forwarded-For` hop. More hops (or none) would either
  collapse every visitor onto the relay's address or expose a spoofable chain.
- **No access-log leakage.** The structured aggregate log above is the only
  request record. The serving layer's default access log (which includes the
  request path) must be disabled or reduced so it cannot become a second,
  chattier record.

## Proving it stays inside budget and does not saturate

`scripts/benchmark_envelope.py` is a repeatable Linux/amd64 benchmark + load
harness. It starts the real app on a threaded loopback server (one process) and
drives it directly — no production container or relay required — to show that:

- each operation finishes within the end-to-end budget,
- a burst far past the two-slot ceiling is shed immediately with 503s, no
  request hangs past the deadline, the burst drains in a bounded time (no
  growing backlog), and peak memory stays bounded, and
- a single visitor's rapid requests are allowed up to the burst of two and then
  refused 429.

Run it with `python3 scripts/benchmark_envelope.py` (add `--json` for the raw
report). Client-address keying is exercised with a simulated single trusted hop.
