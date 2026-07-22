# Brewgen frontend

The public brief-construction screen (issue #26 locked design), built on Vue 3 +
Vite. This replaces the retired Vue 2 / vue-cli app, which was reference-only.

## Commands

- `npm install` — install dependencies.
- `npm run dev` — Vite dev server (proxies `/api` to a local Flask backend on :5000).
- `npm run build` — production build into `../dist` (served by the Flask backend).
- `npm test` — component tests (Vitest + happy-dom): the focused-range contract,
  debounce/stale-response guard, five-flavor cap, and locked-voice error states.
- `npm run test:browser` — real-browser regression guard (headless Chromium)
  proving one flavor edit makes exactly one focused range request and never the
  retired all-descriptor sweep.

## Screens

`src/components/BriefEditor.vue` is the whole screen. It talks to only two solver
endpoints — one conditional range for a single flavor, and one whole-brief
feasibility check — and never the all-descriptor `/api/v1/grains/sensory-profiles`
path.
