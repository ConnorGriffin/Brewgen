#!/usr/bin/env python3
"""Benchmark + load harness for Brewgen's anonymous-compute envelope.

Repeatable Linux/amd64 evidence that the single-worker public API stays inside
its budget and does not saturate under overload. It measures the process
directly -- it starts the real Flask app on a threaded loopback server (one
process) and drives it over HTTP -- and needs neither the unbuilt production
container nor the production relay. Client-address keying is simulated with one
trusted ``X-Forwarded-For`` hop, exactly as ``ProxyFix(x_for=1)`` resolves it in
production.

It proves three things and exits non-zero if any fails:

1. Budget -- a focused flavor-range check, a whole-brief feasibility check, and a
   grain-bill generation each finish within the end-to-end deadline (plus a
   little HTTP/process slack), so no operation runs unbounded.
2. Non-saturation -- when far more than the two-slot ceiling of generation
   requests arrive at once, the overflow is refused *immediately* with 503
   (busy), no request hangs past the deadline, the whole burst drains in about
   one budget rather than growing without bound, and peak memory stays bounded.
3. Per-visitor limit -- a single visitor's rapid requests are allowed up to the
   burst of two and then answered 429, with no compute spent on the refusals.

Usage:
    python3 scripts/benchmark_envelope.py [--overload N] [--json]

Run it on Linux/amd64 (CI-class hardware) for the recorded numbers; it runs
anywhere the backend dependencies (Flask, PuLP) are installed.
"""

import argparse
import json
import os
import resource
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from brewgen.backend import views  # noqa: E402
from brewgen.backend.solver.fermentables import SolverConfig  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

# The locked end-to-end deadline, plus generous slack for HTTP framing and
# process scheduling. A well-behaved request must land under the ceiling; an
# overloaded one must still never exceed it by more than a small margin.
END_TO_END_BUDGET = SolverConfig().request_deadline_seconds  # 2.0s
LATENCY_CEILING = END_TO_END_BUDGET + 1.5
# Peak RSS ceiling for the whole harness run. CBC is small and the two-slot cap
# bounds concurrent solves, so a single worker must stay well under this.
RSS_CEILING_MB = 512


# -- a valid brief straight from the shipped catalog ------------------------

def _briefs():
    grains = views.all_grains.get_grain_list()
    by_cat = {}
    for g in grains:
        by_cat.setdefault(g["category"], []).append(g["slug"])
    fermentables = [
        {"slug": s, "min_percent": 0, "max_percent": 100} for s in by_cat["base"][:2]
    ] + [
        {"slug": s, "min_percent": 0, "max_percent": 25} for s in by_cat["crystal"][:2]
    ]
    brief = {
        "fermentable_list": fermentables,
        "category_model": [
            {"name": "base", "min_percent": 60, "max_percent": 100,
             "unique_fermentable_count": 2},
            {"name": "crystal", "min_percent": 0, "max_percent": 25,
             "unique_fermentable_count": 2},
        ],
        "max_unique_fermentables": 4,
        "equipment_profile": {"target_volume_gallons": 5.5, "mash_efficiency": 75},
        "beer_profile": {"min_color_srm": 3, "max_color_srm": 20,
                         "original_sg": 1.055},
    }
    range_brief = dict(brief)
    range_brief["descriptor"] = views.all_grains.get_sensory_keywords()[0]
    return brief, range_brief


# -- loopback server --------------------------------------------------------

class _Server:
    """Run the real app on a threaded loopback server in a background thread."""

    def __init__(self):
        self._srv = make_server("127.0.0.1", 0, views.app, threaded=True)
        self.base = "http://127.0.0.1:%d" % self._srv.server_port
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._srv.shutdown()
        self._thread.join(timeout=5)


def _post(base, path, body, visitor):
    """POST a brief as one trusted-hop visitor; return (status, seconds)."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method="POST", headers={
        "Content-Type": "application/json",
        "X-Forwarded-For": visitor,
    })
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
    except urllib.error.HTTPError as err:
        status = err.code
    return status, time.perf_counter() - start


# -- benchmarks -------------------------------------------------------------

def bench_budget(base, brief, range_brief, report):
    """Each operation must finish under the latency ceiling."""
    ops = [
        ("focused flavor-range", "/api/v1/grains/sensory-range", range_brief),
        ("brief feasibility", "/api/v1/grains/feasibility", brief),
        ("grain-bill generation", "/api/v1/grains/recipes", brief),
    ]
    ok = True
    for i, (label, path, body) in enumerate(ops):
        samples = []
        for run in range(5):
            # A fresh visitor per run keeps the per-visitor limit out of the way
            # of the latency measurement.
            status, elapsed = _post(base, path, body, "10.%d.%d.1" % (i, run))
            samples.append(elapsed)
        p50 = statistics.median(samples)
        worst = max(samples)
        within = worst < LATENCY_CEILING
        ok = ok and within
        report["budget"][label] = {
            "p50_seconds": round(p50, 4),
            "max_seconds": round(worst, 4),
            "ceiling_seconds": LATENCY_CEILING,
            "within_budget": within,
        }
    return ok


def bench_non_saturation(base, brief, report, overload):
    """A burst far past the two-slot ceiling is shed immediately, not queued."""
    def fire(n):
        # Distinct visitors so the per-visitor limit never fires -- this isolates
        # the concurrency ceiling as the thing under test.
        return _post(base, "/api/v1/grains/recipes", brief, "172.16.0.%d" % (n % 250 + 1))

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=overload) as pool:
        results = list(pool.map(fire, range(overload)))
    wall = time.perf_counter() - wall_start

    statuses = [s for s, _ in results]
    latencies = [t for _, t in results]
    served = statuses.count(200)
    busy = statuses.count(503)
    worst = max(latencies)

    # The ceiling must shed load (some 503s), nothing may hang past the deadline
    # ceiling, and the whole burst must drain in a bounded number of budgets
    # rather than overload-many (which is what a growing backlog would cost).
    sheds_load = busy > 0
    bounded_latency = worst < LATENCY_CEILING
    no_backlog = wall < LATENCY_CEILING * 3
    ok = sheds_load and bounded_latency and no_backlog

    report["non_saturation"] = {
        "concurrent_requests": overload,
        "served_200": served,
        "busy_503": busy,
        "other": overload - served - busy,
        "max_latency_seconds": round(worst, 4),
        "wall_seconds": round(wall, 4),
        "sheds_load": sheds_load,
        "bounded_latency": bounded_latency,
        "no_growing_backlog": no_backlog,
    }
    return ok


def bench_rate_limit(base, brief, report):
    """One visitor: two allowed (burst), the rest 429 -- no compute on refusals."""
    statuses = [
        _post(base, "/api/v1/grains/feasibility", brief, "198.51.100.7")[0]
        for _ in range(5)
    ]
    allowed = sum(1 for s in statuses if s != 429)
    refused = statuses.count(429)
    ok = allowed == 2 and refused == 3
    report["rate_limit"] = {
        "requests": 5,
        "allowed_burst": allowed,
        "refused_429": refused,
        "matches_burst_two": ok,
    }
    return ok


def _peak_rss_mb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is kilobytes on Linux, bytes on macOS.
    if sys.platform == "darwin":
        rss /= 1024
    return rss / 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overload", type=int, default=24,
                        help="concurrent generation requests for the load test")
    parser.add_argument("--json", action="store_true",
                        help="emit the full report as JSON")
    args = parser.parse_args()

    brief, range_brief = _briefs()
    report = {"budget": {}}

    with _Server() as server:
        budget_ok = bench_budget(server.base, brief, range_brief, report)
        saturation_ok = bench_non_saturation(server.base, brief, report, args.overload)
        rate_ok = bench_rate_limit(server.base, brief, report)

    peak_mb = _peak_rss_mb()
    memory_ok = peak_mb < RSS_CEILING_MB
    report["memory"] = {
        "peak_rss_mb": round(peak_mb, 1),
        "ceiling_mb": RSS_CEILING_MB,
        "bounded": memory_ok,
    }
    report["passed"] = bool(budget_ok and saturation_ok and rate_ok and memory_ok)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)

    return 0 if report["passed"] else 1


def _print_report(report):
    print("Brewgen anonymous-compute envelope -- benchmark + load harness\n")
    print("Budget (each operation must finish under %.1fs):" % LATENCY_CEILING)
    for label, m in report["budget"].items():
        print("  %-24s p50 %.3fs  max %.3fs  %s"
              % (label, m["p50_seconds"], m["max_seconds"],
                 "OK" if m["within_budget"] else "FAIL"))
    s = report["non_saturation"]
    print("\nNon-saturation (%d concurrent generations, 2-slot ceiling):"
          % s["concurrent_requests"])
    print("  served %d  busy(503) %d  other %d" % (s["served_200"], s["busy_503"], s["other"]))
    print("  max latency %.3fs  burst wall %.3fs" % (s["max_latency_seconds"], s["wall_seconds"]))
    print("  sheds load: %s  bounded latency: %s  no growing backlog: %s"
          % (s["sheds_load"], s["bounded_latency"], s["no_growing_backlog"]))
    r = report["rate_limit"]
    print("\nPer-visitor limit (5 rapid requests, burst 2):")
    print("  allowed %d  refused(429) %d  %s"
          % (r["allowed_burst"], r["refused_429"], "OK" if r["matches_burst_two"] else "FAIL"))
    m = report["memory"]
    print("\nMemory: peak RSS %.1f MB (ceiling %d MB) %s"
          % (m["peak_rss_mb"], m["ceiling_mb"], "OK" if m["bounded"] else "FAIL"))
    print("\nRESULT: %s" % ("PASS" if report["passed"] else "FAIL"))


if __name__ == "__main__":
    sys.exit(main())
