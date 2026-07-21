# AGENTS.md — Brewgen

A Flask and Vue application that generates homebrew recipes from desired flavor characteristics.

profile: reviewed

## Repo facts

- **Frontend install:** `cd brewgen/frontend && npm install`.
- **Test / CI gate:** `python3 -m compileall -q brewgen recipe_analyzer archive`.
- **Frontend dev server:** `cd brewgen/frontend && npm run serve`.
- **Backend dev server:** `FLASK_APP=brewgen.backend.views flask run` (the Python dependencies are not currently captured in a manifest).
- Source: `brewgen/backend/`, `brewgen/frontend/src/`, and `recipe_analyzer/`. There is no automated test suite; files named `*_test.py` are exploratory scripts, not tests.
- **Never run the live recipe scrapers.** `recipe_analyzer/beersmith_scrape/scrape.py` and `recipe_analyzer/brewersfriend_scrape/scrape.py` crawl third-party recipe sites across thousands of requests and can trigger rate limits or blocks.
- **Never use `pytest` discovery as the test gate.** It imports the exploratory `*_test.py` scripts, which execute expensive solver work at module import time. Use the compile gate above until a real test suite exists.

