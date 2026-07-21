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


## #11: Prove the production artifact

Blocked by: #6, #8, #9, #10
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


## Deferred risk: source rights

The maintainer explicitly deferred investigating publication rights for recipe, BJCP, and maltster-derived data. This is recorded as unresolved, not cleared.
