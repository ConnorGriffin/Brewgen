# Brewgen public launch

Destination: an anonymous, stateless, fermentables-only grain-bill generator at `brewgen.connorcg.com`, running on the existing public-apps platform. Current assets: [solver rebuild issue #19](https://github.com/ConnorGriffin/Brewgen/issues/19), the legacy UI as behavioral reference, and committed style-model JSON derived from a missing raw corpus.

## #1: What ships first?

Blocked by: none
Type: Grilling

### Question

What is the first public product boundary?

### Answer

Anonymous and stateless. It generates fermentable grain bills only: no accounts, persistence, uploads, hops, or yeast. Existing API contracts and UI are not compatibility constraints.

## #2: Where does it run?

Blocked by: none
Type: Grilling

### Question

What serving and delivery boundary should public launch use?

### Answer

The existing `public-apps` VM behind the Lightsail relay and Caddy. The home network remains outbound-only; GHCR plus Watchtower is the established delivery path.

## #3: What is a generated alternative?

Blocked by: none
Type: Grilling

### Question

What behavior must replace enumerate-all recipe generation?

### Answer

Return up to five deterministic, explicitly unranked grain bills. Percentages are whole numbers totaling 100. Every pair differs by at least 10 total percentage points (L1 distance). Exact decimal SRM must satisfy the requested bounds; sensory ranges preserve all grain-count limits and are therefore MILP solves.

## #4: What security bar blocks cutover?

Blocked by: none
Type: Grilling

### Question

What evidence is required before anonymous public traffic is accepted?

### Answer

Zero known critical/high vulnerabilities in shipped dependencies; every remaining medium/low alert triaged. CI enforces tests, dependency audit, code scanning, and container scanning. The application owns request-size limits, per-client rate limits, and hard solver deadlines rather than relying on the currently disabled relay limiter. All 174 current Dependabot alerts originate in the obsolete frontend manifests.

## #5: Rebuild the reference corpus

Blocked by: none
Type: Research

### Question

What deliberate recipe sources, canonical schema, deduplication rules, quality filters, and provenance records should replace the missing ignored BeerXML corpus and ad-hoc rewrite tables?

### Answer


## #6: Prove a reproducible corpus pipeline

Blocked by: #5
Type: Prototype

### Question

Can one versioned import pipeline normalize the chosen sources, surface unmatched ingredients and rejected recipes as metrics, and regenerate byte-stable style models from scratch without live scraping?

### Answer


## #7: Prove the solver contract

Blocked by: #3
Type: Prototype

### Question

Can the corrected PuLP MILP enforce the exact color algebra, whole-percent/category/cardinality/sensory constraints, five-way L1 diversity, determinism, and hard runtime bounds against synthetic fixtures and the current committed style models?

### Answer


## #8: Lock the public workflow

Blocked by: #7
Type: Prototype

### Question

What is the simplest public grain-bill workflow that makes constraints understandable and presents five unranked alternatives honestly?

### Answer

Use `/ui-mockups`; the current Vue UI is reference material only. The implementation target is Vue 3 + Vite.

## #9: Establish the security baseline

Blocked by: #4
Type: Research

### Question

After replacing the frontend toolchain and declaring the Python runtime, what shipped dependency risks remain, which scanners cover them, and what explicit exceptions—if any—meet the cutover bar?

### Answer


## #10: Define the anonymous-compute envelope

Blocked by: #7, #8
Type: Grilling

### Question

What request schemas, size limits, solver deadlines, rate limits, concurrency caps, logging policy, and failure responses keep anonymous optimization bounded without collecting user data?

### Answer

A single strict, versioned JSON grain-bill brief carries style/original gravity, equipment, allowed fermentables and optional whole-percent bounds, maximum fermentable count, sensory bounds, and exact SRM bounds; the server derives category/style-model constraints. Reject unknown fields, duplicate or unknown catalog values, non-finite numbers, inverted ranges, and non-JSON input. Cap the body at 64 KiB and lists at current catalog cardinality.

Every compute request has a shared 1.8-second solver budget and 2-second end-to-end deadline. Permit six compute requests per visitor per minute with burst two, keyed only by a daily-rotated in-memory hash of the trusted client address (10-minute idle expiry; never logged or persisted). Allow two active solver requests per container with no queue. Log only timestamp, random request ID, operation, outcome, status, and duration for seven days; never log bodies, constraints, addresses/hashes, headers, cookies, user agents, referrers, or query strings.

Return at most five unranked grain bills and preserve `complete`, `partial`, `infeasible`, and `deadline_exceeded` as distinct outcomes. Failures use `application/problem+json` with stable codes and no echoed input: malformed JSON 400, oversized 413, wrong media type 415, invalid/empty/infeasible brief 422, visitor limit 429, busy/deadline 503, and generic internal failure 500. Public cutover requires boundary, deadline, concurrency, rate-limit, privacy-log, failure-contract, and recovery tests plus a production-container benchmark. The locked evidence and exact field ranges are recorded in issue #29.

## #11: Prove the production artifact

Blocked by: #6, #8, #9, #10, #13, #14
Type: Prototype

### Question

Can one non-root container serve the built frontend and production Python API with a health check, bounded resources, reproducible builds, clean scans, and rollback-safe GHCR release tags?

### Answer


## #12: Cut over `brewgen.connorcg.com`

Blocked by: #11
Type: Prototype

### Question

Can the app repository publish the proven image and the homelab repository add the public-apps workload, least-privilege tailnet route, relay vhost, DNS record, monitoring, and tested rollback without exposing the residential IP?

### Answer


## #13: Define the public licensing boundary

Blocked by: #5
Type: Research

### Question

Which licenses and notices should cover Brewgen's source code, documentation, and retained legacy style models, given that the models' raw reference corpus is missing and their source rights are not cleared?

### Answer


## #14: Lock the project-support affordance

Blocked by: #8, #13
Type: Prototype

### Question

Where should a `Support this project` control appear in the locked public workflow, where should it lead, and how should it behave without competing with the grain-bill brief or implying paid access?

### Answer


## Deferred risk: source rights

The maintainer explicitly deferred investigating publication rights for recipe, BJCP, and maltster-derived data. This is recorded as unresolved, not cleared.
