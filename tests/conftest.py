"""Test fixtures scoped to the ``tests`` suite.

The repo-root ``conftest.py`` holds the shared grain/category builders. This one
adds a single autouse fixture that resets the anonymous-compute envelope's
process-wide state before each test, so the burst-2 rate limiter and the
two-slot concurrency ceiling never leak tokens or permits from one case into the
next. It is a no-op when the Flask-dependent envelope module cannot be imported
(e.g. a solver-only run without the web dependencies installed)."""

import pytest


@pytest.fixture(autouse=True)
def _reset_compute_envelope():
    try:
        from brewgen.backend import envelope
    except Exception:
        yield
        return
    envelope.reset_state()
    yield
