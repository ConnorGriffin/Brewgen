# AGENTS.md — Brewgen

A Flask and Vue application that generates homebrew recipes from desired flavor characteristics.

profile: reviewed

## Repo facts

- **Frontend install:** `cd brewgen/frontend && npm install` (Vue 3 + Vite; the legacy Vue 2 / vue-cli app was replaced for the public surface).
- **Test / CI gate:** `python3 -m compileall -q brewgen recipe_analyzer archive`.
- **Frontend tests:** `cd brewgen/frontend && npm test` (Vitest component tests). Real-browser guard: `npm run test:browser`.
- **Frontend dev server:** `cd brewgen/frontend && npm run dev`.
- **Backend dev server:** `FLASK_APP=brewgen.backend.views flask run` (the Python dependencies are not currently captured in a manifest).
- **Screenshots:** `node scripts/screenshots.mjs <config.json>` (canonical harness; `--single-process` Chromium + `file://` + `addInitScript` fetch stubs survive the agent sandbox).
- Source: `brewgen/backend/`, `brewgen/frontend/src/`, and `recipe_analyzer/`. The Python side has no automated test suite; files named `*_test.py` are exploratory scripts, not tests. The frontend has Vitest component tests under `brewgen/frontend/tests/`.
- **The live recipe scrapers have been retired.** The BeerSmith Recipes and Brewers Friend crawler scripts were removed; the per-style aggregate models they once produced are now a frozen legacy artifact (see `recipe_analyzer/PROVENANCE.md`). Do not reintroduce live crawlers of third-party recipe sites — they made thousands of requests and could trigger rate limits, blocks, or legal concern.
- **Never use `pytest` discovery as the test gate.** It imports the exploratory `*_test.py` scripts, which execute expensive solver work at module import time. Use the compile gate above until a real test suite exists.

