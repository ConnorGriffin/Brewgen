# AGENTS.md — Brewgen

A Flask and Vue application that generates homebrew recipes from desired flavor characteristics.

profile: reviewed

## Repo facts

- **Frontend install:** `cd brewgen/frontend && npm install` (Vue 3 + Vite; the legacy Vue 2 / vue-cli app was replaced for the public surface).
- **Test / CI gate:** `python3 -m compileall -q brewgen recipe_analyzer archive` and `python3 -m pytest tests -q`.
- **Frontend tests:** `cd brewgen/frontend && npm test` (Vitest component tests). Real-browser guard: `npm run test:browser`.
- **Frontend dev server:** `cd brewgen/frontend && npm run dev`.
- **Backend dev server:** `FLASK_APP=brewgen.backend.views flask run` (Python dependencies are pinned in `pyproject.toml`, with a hash-pinned compile in `requirements.lock`).
- **Style default briefs:** `python3 scripts/build_style_defaults.py` recomputes the committed, generation-proved default brief every style opens on (and the two American Pale Ale browser fixtures anchored on it). Run it after adding a style or changing a style's grain, category, or sensory model; `tests/test_style_defaults.py` fails while its output is stale.
- **Screenshots:** `node scripts/screenshots.mjs <config.json>` (canonical harness; `--single-process` Chromium + `file://` + `addInitScript` fetch stubs survive the agent sandbox).
- Source: `brewgen/backend/`, `brewgen/frontend/src/`, and `recipe_analyzer/`. The Python side's test suite lives under `tests/` (shared fixtures in root `conftest.py`); the frontend has Vitest component tests under `brewgen/frontend/tests/`.
- **The live recipe scrapers have been retired.** The BeerSmith Recipes and Brewers Friend crawler scripts were removed; the per-style aggregate models they once produced are now a frozen legacy artifact (see `recipe_analyzer/PROVENANCE.md`). Do not reintroduce live crawlers of third-party recipe sites — they made thousands of requests and could trigger rate limits, blocks, or legal concern.
- **Never point `pytest` at the repo root or `archive/` explicitly** (e.g. `pytest .`, `pytest archive`). `archive/modulo_test.py` is an exploratory script that imports the removed OR-Tools dependency, so collecting it is now an import error. A bare `pytest` from the repo root is safe — `testpaths` in `pyproject.toml` already scopes collection to `tests/`.

