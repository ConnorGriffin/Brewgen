"""Integration coverage for the anonymous-compute envelope, exercised through
the public HTTP surface of the three compute endpoints.

Proves, in one place: the media-type/size/JSON gates, the versioned brief
contract, the per-visitor rate limit (burst then refill, keyed per trusted
hop), the one-slot no-queue concurrency ceiling, the deadline->503 mapping, the
stable problem+json failure contract with no echoed input, and the
aggregate-only privacy log. The size cap carries a regression guard: an
oversized body must be rejected before the solver is ever built."""

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from brewgen.backend import views, envelope
from brewgen.backend import brief as brief_module
from brewgen.backend.solver.fermentables import SolverConfig

COMPUTE_ENDPOINTS = [
    "/api/v1/grains/sensory-range",
    "/api/v1/grains/feasibility",
    "/api/v1/grains/recipes",
]


@pytest.fixture
def client():
    return views.app.test_client()


def _brief(endpoint=None):
    """A valid brief for any compute endpoint (adds a descriptor for the focused
    range endpoint, whose contract requires one)."""
    style = views.all_styles.get_style_by_slug("american-pale-ale")
    usage = style.get_grain_usage()
    brief = {
        "version": 1,
        "style": {"slug": style.slug, "original_gravity": 1.055},
        "equipment": {
            "batch_volume_gallons": 5.5,
            "mash_efficiency_percent": 75,
        },
        "fermentables": {
            "allowed_slugs": [item["slug"] for item in usage],
            "bounds": [
                {
                    "slug": item["slug"],
                    "minimum_percent": int(item["min_percent"]),
                    "maximum_percent": int(item["max_percent"]),
                }
                for item in usage
            ],
            "maximum_count": min(style.unique_fermentable_count, 7),
        },
        "sensory": [],
        "color_srm": {"minimum": 3, "maximum": 20},
    }
    if endpoint and endpoint.endswith("sensory-range"):
        brief["descriptor"] = views.all_grains.get_sensory_keywords()[0]
    return brief


def _post_raw(client, endpoint, raw, content_type="application/json"):
    return client.post(endpoint, data=raw, content_type=content_type)


# -- size / media-type / JSON gates ----------------------------------------

def test_oversized_body_is_413_before_the_solver_is_built(client, monkeypatch):
    # Regression guard: a 65_537-byte body must be rejected before any solver
    # work. The body is *valid, padded JSON* that would reach the solver if the
    # cap regressed behind solver work, so a spy that raises when built proves
    # the cap fires first.
    def spy(_data):
        raise AssertionError("solver must not be built for an oversized body")
    monkeypatch.setattr(views, "_build_fermentable_solver", spy)

    body = json.dumps(_brief("/api/v1/grains/recipes"))
    body += " " * (65_537 - len(body))
    assert len(body) == 65_537
    resp = _post_raw(client, "/api/v1/grains/recipes", body)

    assert resp.status_code == 413
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "oversized"


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_wrong_media_type_is_415(client, endpoint):
    resp = _post_raw(client, endpoint, "descriptor=malty", content_type="text/plain")
    assert resp.status_code == 415
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "wrong_media_type"


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_non_json_body_is_400(client, endpoint):
    resp = _post_raw(client, endpoint, "{not valid json")
    assert resp.status_code == 400
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "malformed_json"


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_empty_body_is_400(client, endpoint):
    resp = _post_raw(client, endpoint, "")
    assert resp.status_code == 400
    assert resp.get_json()["outcome"] == "malformed_json"


# -- versioned brief contract ----------------------------------------------

@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_version_one_choice_brief_is_accepted(client, endpoint):
    resp = client.post(endpoint, json=_brief(endpoint))
    assert resp.status_code == 200
    assert resp.get_json()["status"] in {"feasible", "complete", "partial"}


def _mutations():
    slugs = views.all_grains.get_grain_slugs()
    keywords = views.all_grains.get_sensory_keywords()

    def unknown_field(b):
        b["surprise"] = True

    def unknown_slug(b):
        b["fermentables"]["allowed_slugs"][0] = "definitely-not-a-real-grain"

    def duplicate_slug(b):
        b["fermentables"]["allowed_slugs"][1] = \
            b["fermentables"]["allowed_slugs"][0]

    def non_finite(b):
        b["style"]["original_gravity"] = float("inf")

    def inverted_range(b):
        b["fermentables"]["bounds"][0]["minimum_percent"] = 90
        b["fermentables"]["bounds"][0]["maximum_percent"] = 10

    def over_cardinality(b):
        b["sensory"] = [
            {"name": keywords[0], "minimum": 0, "maximum": 1}
            for _ in range(49)
        ]

    def boolean_number(b):
        b["equipment"]["mash_efficiency_percent"] = True

    def unknown_nested_field(b):
        b["color_srm"]["surprise"] = 1

    def bound_for_absent_slug(b):
        absent = next(
            slug for slug in slugs
            if slug not in set(b["fermentables"]["allowed_slugs"]))
        b["fermentables"]["bounds"][0]["slug"] = absent

    def count_over_allowed(b):
        first = b["fermentables"]["allowed_slugs"][0]
        b["fermentables"]["allowed_slugs"] = [first]
        b["fermentables"]["bounds"] = []
        b["fermentables"]["maximum_count"] = 2

    return [unknown_field, unknown_slug, duplicate_slug, non_finite,
            inverted_range, over_cardinality, boolean_number,
            unknown_nested_field, bound_for_absent_slug, count_over_allowed]


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
@pytest.mark.parametrize("mutate", _mutations(), ids=lambda f: f.__name__)
def test_invalid_brief_is_422_problem_json(client, endpoint, mutate):
    brief = _brief(endpoint)
    mutate(brief)
    # json.dumps serializes non-finite numbers as Infinity/NaN, which the server
    # parses and the contract then rejects for non-finiteness.
    resp = _post_raw(client, endpoint, json.dumps(brief))
    assert resp.status_code == 422
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "invalid"


def test_unknown_brief_version_is_rejected(client):
    brief = _brief("/api/v1/grains/recipes")
    brief["version"] = 2
    resp = _post_raw(client, "/api/v1/grains/recipes", json.dumps(brief))
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "invalid"


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_version_is_required_and_legacy_model_fields_are_rejected(
        client, endpoint):
    missing = _brief(endpoint)
    del missing["version"]
    resp = client.post(endpoint, json=missing)
    assert resp.status_code == 422
    assert {error["path"] for error in resp.get_json()["errors"]} >= {"version"}

    for field in [
        "fermentable_list",
        "category_model",
        "sensory_model",
        "max_unique_fermentables",
        "equipment_profile",
        "beer_profile",
    ]:
        brief = _brief(endpoint)
        brief[field] = []
        resp = client.post(endpoint, json=brief)
        assert resp.status_code == 422
        assert field in {error["path"] for error in resp.get_json()["errors"]}


def _invalid_path_cases():
    return [
        ("style unknown", lambda b: b["style"].update(extra=1), "style.extra"),
        ("style slug unknown",
         lambda b: b["style"].update(slug="not-a-real-style"),
         "style.slug"),
        ("equipment unknown", lambda b: b["equipment"].update(extra=1),
         "equipment.extra"),
        ("fermentables unknown", lambda b: b["fermentables"].update(extra=1),
         "fermentables.extra"),
        ("bound unknown", lambda b: b["fermentables"]["bounds"][0].update(extra=1),
         "fermentables.bounds[0].extra"),
        ("bound duplicate", _duplicate_bound, "fermentables.bounds[1].slug"),
        ("sensory unknown", _add_unknown_sensory_field, "sensory[0].extra"),
        ("color unknown", lambda b: b["color_srm"].update(extra=1),
         "color_srm.extra"),
        ("version boolean", lambda b: b.update(version=True), "version"),
        ("gravity low", lambda b: b["style"].update(original_gravity=.999),
         "style.original_gravity"),
        ("gravity high", lambda b: b["style"].update(original_gravity=1.201),
         "style.original_gravity"),
        ("volume low", lambda b: b["equipment"].update(batch_volume_gallons=.24),
         "equipment.batch_volume_gallons"),
        ("volume high", lambda b: b["equipment"].update(batch_volume_gallons=101),
         "equipment.batch_volume_gallons"),
        ("efficiency low",
         lambda b: b["equipment"].update(mash_efficiency_percent=.9),
         "equipment.mash_efficiency_percent"),
        ("efficiency high",
         lambda b: b["equipment"].update(mash_efficiency_percent=101),
         "equipment.mash_efficiency_percent"),
        ("percent float", _set_float_percent,
         "fermentables.bounds[0].minimum_percent"),
        ("percent high", _set_high_percent,
         "fermentables.bounds[0].maximum_percent"),
        ("count float", lambda b: b["fermentables"].update(maximum_count=2.0),
         "fermentables.maximum_count"),
        ("count low", lambda b: b["fermentables"].update(maximum_count=0),
         "fermentables.maximum_count"),
        ("count high", lambda b: b["fermentables"].update(maximum_count=8),
         "fermentables.maximum_count"),
        ("sensory duplicate", _duplicate_sensory, "sensory[1].name"),
        ("sensory unknown name", _unknown_sensory, "sensory[0].name"),
        ("sensory high", _high_sensory, "sensory[0].maximum"),
        ("sensory inverted", _inverted_sensory, "sensory[0].minimum"),
        ("srm low", lambda b: b.update(color_srm={"minimum": -1, "maximum": 20}),
         "color_srm.minimum"),
        ("srm high", lambda b: b.update(color_srm={"minimum": 0, "maximum": 256}),
         "color_srm.maximum"),
        ("srm inverted",
         lambda b: b.update(color_srm={"minimum": 20, "maximum": 5}),
         "color_srm.minimum"),
    ]


def _sensory_item():
    return {
        "name": views.all_grains.get_sensory_keywords()[0],
        "minimum": 0,
        "maximum": 1,
    }


def _add_unknown_sensory_field(brief):
    brief["sensory"] = [_sensory_item()]
    brief["sensory"][0]["extra"] = 1


def _set_float_percent(brief):
    brief["fermentables"]["bounds"][0]["minimum_percent"] = 1.5


def _set_high_percent(brief):
    brief["fermentables"]["bounds"][0]["maximum_percent"] = 101


def _duplicate_bound(brief):
    brief["fermentables"]["bounds"][1] = deepcopy(
        brief["fermentables"]["bounds"][0])


def _duplicate_sensory(brief):
    brief["sensory"] = [_sensory_item(), deepcopy(_sensory_item())]


def _unknown_sensory(brief):
    brief["sensory"] = [_sensory_item()]
    brief["sensory"][0]["name"] = "not-a-real-sensory-name"


def _high_sensory(brief):
    brief["sensory"] = [_sensory_item()]
    brief["sensory"][0]["maximum"] = 5.1


def _inverted_sensory(brief):
    brief["sensory"] = [_sensory_item()]
    brief["sensory"][0].update(minimum=4, maximum=1)


@pytest.mark.parametrize(
    "_label,mutate,path", _invalid_path_cases(),
    ids=[case[0] for case in _invalid_path_cases()])
def test_invalid_choice_fields_report_only_their_paths(
        client, _label, mutate, path):
    brief = _brief("/api/v1/grains/recipes")
    mutate(brief)
    resp = client.post("/api/v1/grains/recipes", json=brief)
    assert resp.status_code == 422
    assert path in {error["path"] for error in resp.get_json()["errors"]}


def test_exact_numeric_and_cardinality_boundaries_are_accepted(client):
    brief = _brief("/api/v1/grains/feasibility")
    brief["style"]["original_gravity"] = 1.200
    brief["equipment"] = {
        "batch_volume_gallons": 100,
        "mash_efficiency_percent": 100,
    }
    brief["fermentables"] = {
        "allowed_slugs": views.all_grains.get_grain_slugs(),
        "bounds": [{
            "slug": views.all_grains.get_grain_slugs()[0],
            "minimum_percent": 0,
            "maximum_percent": 100,
        }],
        "maximum_count": 7,
    }
    brief["sensory"] = [
        {"name": name, "minimum": 0, "maximum": 5}
        for name in views.all_grains.get_sensory_keywords()
    ]
    brief["color_srm"] = {"minimum": 0, "maximum": 255}

    resp = client.post("/api/v1/grains/feasibility", json=brief)
    assert resp.get_json().get("outcome") != "invalid"

    brief["style"]["original_gravity"] = 1.000
    brief["equipment"] = {
        "batch_volume_gallons": .25,
        "mash_efficiency_percent": 1,
    }
    resp = client.post("/api/v1/grains/feasibility", json=brief)
    assert resp.get_json().get("outcome") != "invalid"


def test_non_finite_choice_numbers_report_paths(client):
    brief = _brief("/api/v1/grains/recipes")
    brief["style"]["original_gravity"] = float("nan")
    brief["equipment"]["batch_volume_gallons"] = float("inf")
    resp = _post_raw(
        client, "/api/v1/grains/recipes", json.dumps(brief))
    assert resp.status_code == 422
    paths = {error["path"] for error in resp.get_json()["errors"]}
    assert paths >= {
        "style.original_gravity",
        "equipment.batch_volume_gallons",
    }


def test_style_category_constraints_are_derived_server_side(client):
    brief = _brief("/api/v1/grains/feasibility")
    crystal = next(
        grain for grain in views.all_grains.get_grain_list()
        if grain["category"] == "crystal")
    brief["fermentables"] = {
        "allowed_slugs": [crystal["slug"]],
        "bounds": [],
        "maximum_count": 1,
    }
    brief["color_srm"] = {"minimum": 0, "maximum": 255}

    resp = client.post("/api/v1/grains/feasibility", json=brief)
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "infeasible"


# -- per-visitor rate limit -------------------------------------------------

def _frozen_limiter(monkeypatch, now=1000.0):
    limiter = envelope.RateLimiter(clock=lambda: now)
    monkeypatch.setattr(envelope, "RATE_LIMITER", limiter)
    return limiter


def test_rate_limit_allows_a_burst_of_two_then_429(client, monkeypatch):
    _frozen_limiter(monkeypatch)  # frozen clock: no refill mid-burst
    body = _brief("/api/v1/grains/feasibility")
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    third = client.post("/api/v1/grains/feasibility", json=body)
    assert third.status_code == 429
    assert third.mimetype == "application/problem+json"
    assert third.get_json()["outcome"] == "rate_limited"


def test_rate_limit_refills_at_six_per_minute(client, monkeypatch):
    clock = {"now": 0.0}
    monkeypatch.setattr(envelope, "RATE_LIMITER",
                        envelope.RateLimiter(clock=lambda: clock["now"]))
    body = _brief("/api/v1/grains/feasibility")
    # Spend the burst of two, then throttle.
    client.post("/api/v1/grains/feasibility", json=body)
    client.post("/api/v1/grains/feasibility", json=body)
    assert client.post("/api/v1/grains/feasibility", json=body).status_code == 429
    # One token refills after ten seconds (six per minute).
    clock["now"] = 10.0
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code == 429


def test_rate_limited_carries_exact_retry_after(client, monkeypatch):
    # Right after the burst the frozen bucket sits at zero tokens, so one refills
    # in exactly (1 - 0) / 0.1 = 10 s. The refusal must state that, both as the
    # RFC 7231 header and as the body field the frontend renders.
    _frozen_limiter(monkeypatch)
    body = _brief("/api/v1/grains/feasibility")
    client.post("/api/v1/grains/feasibility", json=body)
    client.post("/api/v1/grains/feasibility", json=body)
    third = client.post("/api/v1/grains/feasibility", json=body)
    assert third.status_code == 429
    assert third.headers["Retry-After"] == "10"
    assert third.get_json()["retry_after"] == 10


def test_busy_shed_does_not_charge_the_visitor(client, monkeypatch):
    # Regression guard for the charge bug: a request shed as busy never reaches
    # solver work, so it must leave the visitor's allowance untouched. Against
    # the old gate (charge, then refuse) the second post below would already be
    # 429; with the busy refund the full burst of two survives the shed.
    _frozen_limiter(monkeypatch)
    body = _brief("/api/v1/grains/feasibility")

    assert envelope.SLOTS.acquire(blocking=False) is True
    try:
        busy = client.post("/api/v1/grains/feasibility", json=body)
        assert busy.status_code == 503
        assert busy.get_json()["outcome"] == "busy"
        assert busy.headers["Retry-After"] == "1"
        assert busy.get_json()["retry_after"] == 1
    finally:
        envelope.SLOTS.release()

    # The visitor still has both burst tokens: two allowed, then 429.
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code == 429


def test_allow_retry_timing_is_exact_under_an_injected_clock():
    # The limiter's retry seconds come from the same clock reading as the
    # decision, so they are exact without any wall-clock waiting.
    now = {"t": 0.0}
    limiter = envelope.RateLimiter(clock=lambda: now["t"])
    addr = "203.0.113.5"
    assert limiter.allow(addr) == (True, 0.0)
    assert limiter.allow(addr) == (True, 0.0)
    allowed, retry = limiter.allow(addr)
    assert allowed is False
    assert retry == 10.0                       # empty bucket -> a full ten seconds
    now["t"] = 5.0                             # half a token has refilled
    allowed, retry = limiter.allow(addr)
    assert allowed is False
    assert retry == pytest.approx(5.0)


def test_busy_refund_restores_the_bucket_at_a_frozen_clock():
    # refund credits exactly one token back (capped at capacity) at the same
    # clock instant, so the busy path can undo its own charge.
    now = {"t": 0.0}
    limiter = envelope.RateLimiter(clock=lambda: now["t"])
    addr = "203.0.113.6"
    assert limiter.allow(addr)[0] is True
    assert limiter.allow(addr)[0] is True
    assert limiter.allow(addr)[0] is False     # burst spent
    limiter.refund(addr)
    assert limiter.allow(addr)[0] is True       # the refunded token is spendable
    assert limiter.allow(addr)[0] is False


def test_rate_limit_is_keyed_per_visitor_via_one_trusted_hop(client, monkeypatch):
    _frozen_limiter(monkeypatch)
    body = _brief("/api/v1/grains/feasibility")

    def post(ip):
        return client.post("/api/v1/grains/feasibility", json=body,
                           headers={"X-Forwarded-For": ip})

    # One visitor spends its burst and is throttled...
    post("203.0.113.1")
    post("203.0.113.1")
    assert post("203.0.113.1").status_code == 429
    # ...while a different forwarded hop is unaffected: the key is the client,
    # not the relay (ProxyFix resolves exactly one hop).
    assert post("203.0.113.9").status_code != 429


# -- one-slot, no-queue concurrency ----------------------------------------

def test_occupied_solver_slot_is_busy_503(client):
    # One solve in flight means the next request is immediately busy, no queue.
    assert envelope.SLOTS.acquire(blocking=False) is True
    try:
        resp = client.post("/api/v1/grains/recipes", json=_brief())
        assert resp.status_code == 503
        assert resp.mimetype == "application/problem+json"
        assert resp.get_json()["outcome"] == "busy"
    finally:
        envelope.SLOTS.release()


def test_burst_admits_one_distinct_solve_and_sheds_the_rest(monkeypatch):
    """Distinct concurrent briefs reach the guard: one runs, the rest are busy."""
    entered = threading.Event()
    release = threading.Event()
    lock = threading.Lock()
    concurrency = {"active": 0, "peak": 0}
    build_solver = views._build_fermentable_solver

    def holding_build(data):
        with lock:
            concurrency["active"] += 1
            concurrency["peak"] = max(
                concurrency["peak"], concurrency["active"])
        entered.set()
        try:
            release.wait(10)
            return build_solver(data)
        finally:
            with lock:
                concurrency["active"] -= 1

    monkeypatch.setattr(views, "_build_fermentable_solver", holding_build)
    results = []

    def post(index):
        brief = _brief("/api/v1/grains/recipes")
        brief["equipment"]["batch_volume_gallons"] += index / 100
        resp = views.app.test_client().post(
            "/api/v1/grains/recipes", json=brief,
            headers={"X-Forwarded-For": "198.51.100.%d" % (index + 1)})
        results.append((resp.status_code, resp.mimetype, resp.get_json()))

    holder = threading.Thread(target=post, args=(0,))
    holder.start()
    assert entered.wait(5), "the first request never reached the solver"

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(post, range(1, 9)))

    assert concurrency["peak"] == 1, "more than one solve ran at once"
    assert len(results) == 8, "busy answers waited for the held solve"
    assert all(status == 503 for status, _, _ in results)
    assert all(mimetype == "application/problem+json"
               for _, mimetype, _ in results)
    assert all(body["outcome"] == "busy" for _, _, body in results)

    release.set()
    holder.join(10)
    assert not holder.is_alive()
    assert results[-1][0] == 200


# -- deadline -> 503 --------------------------------------------------------

@pytest.mark.parametrize("endpoint", [
    "/api/v1/grains/feasibility", "/api/v1/grains/recipes"])
def test_deadline_maps_to_503(client, monkeypatch, endpoint):
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    resp = client.post(endpoint, json=_brief(endpoint))
    assert resp.status_code == 503
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "deadline"


# -- problem+json contract: no echo, stable shape --------------------------

def test_problem_json_never_echoes_input(client):
    marker = "zzz-marker-not-a-real-slug"
    brief = _brief("/api/v1/grains/recipes")
    brief["fermentables"]["allowed_slugs"][0] = marker
    resp = _post_raw(client, "/api/v1/grains/recipes", json.dumps(brief))
    assert resp.status_code == 422
    text = resp.get_data(as_text=True)
    assert marker not in text
    assert set(resp.get_json()) == {
        "type", "title", "status", "outcome", "errors"}
    assert {"path": "fermentables.allowed_slugs[0]"} \
        in resp.get_json()["errors"]


def test_rejection_body_stays_small_for_a_maximally_invalid_brief(client):
    """A full-size body of nothing but bad fields is still rejected with a
    small failure body -- the rejection runs before the rate limiter, so it
    must not become an amplifier."""
    brief = _brief("/api/v1/grains/recipes")
    brief["fermentables"]["bounds"] = [0]
    while len(json.dumps(brief).encode("utf-8")) <= envelope.MAX_BODY_BYTES:
        brief["fermentables"]["bounds"] += [0] * 500
    brief["fermentables"]["bounds"] = brief["fermentables"]["bounds"][:-500]
    raw = json.dumps(brief)
    assert len(raw.encode("utf-8")) > envelope.MAX_BODY_BYTES / 2

    resp = _post_raw(client, "/api/v1/grains/recipes", raw)
    assert resp.status_code == 422
    assert len(resp.get_json()["errors"]) <= brief_module.MAX_REPORTED_ERRORS
    assert len(resp.get_data()) < 8_192


# -- privacy log ------------------------------------------------------------

def test_log_carries_only_aggregate_fields(client, caplog):
    marker_ip = "203.0.113.77"
    marker_slug = _brief()["fermentables"]["allowed_slugs"][0]
    with caplog.at_level(logging.INFO, logger="brewgen.compute"):
        client.post("/api/v1/grains/recipes", json=_brief(),
                    headers={"X-Forwarded-For": marker_ip})

    records = [r for r in caplog.records if r.name == "brewgen.compute"]
    assert len(records) == 1, "exactly one aggregate line per compute request"
    payload = json.loads(records[0].getMessage())
    assert set(payload) == {"timestamp", "request_id", "operation",
                            "outcome", "status", "duration"}
    assert payload["operation"] == "recipes"
    # The address, its hash, and brief content never reach the log.
    assert marker_ip not in records[0].getMessage()
    assert marker_slug not in records[0].getMessage()


# -- single-flight coalescing + short-lived result cache -------------------

def _counting_solver_spy(monkeypatch, gate=None):
    """Replace the solver builder with a spy that counts executions and,
    optionally, blocks the leader on ``gate`` so followers reliably attach while
    it is still in flight. Returns the shared call counter (a list)."""
    real_build = views._build_fermentable_solver
    calls = []
    lock = threading.Lock()

    def spy(data):
        with lock:
            calls.append(1)
        if gate is not None:
            gate.wait(timeout=5)
        return real_build(data)

    monkeypatch.setattr(views, "_build_fermentable_solver", spy)
    return calls


def _post_from(client_endpoint, brief, ip):
    resp = views.app.test_client().post(
        client_endpoint, json=brief, headers={"X-Forwarded-For": ip})
    return resp


def test_concurrent_identical_briefs_run_the_solver_once(monkeypatch):
    # N byte-identical valid briefs racing one endpoint must cause exactly one
    # solver execution; every caller gets the same 200 body, and no follower is
    # turned away busy even though N exceeds the one-slot ceiling. Distinct
    # forwarded hops keep the per-visitor rate limit out of the way -- the
    # canonical key is the brief, not the address.
    gate = threading.Event()
    calls = _counting_solver_spy(monkeypatch, gate=gate)
    endpoint = "/api/v1/grains/feasibility"
    brief = _brief(endpoint)

    results = {}

    def worker(i):
        results[i] = _post_from(endpoint, brief, "203.0.113.%d" % (i + 1))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    # Let the leader reach the solver and the followers reach their wait.
    deadline = time.monotonic() + 5
    while not calls and time.monotonic() < deadline:
        time.sleep(0.01)
    time.sleep(0.1)
    gate.set()
    for t in threads:
        t.join(timeout=5)

    assert len(calls) == 1, "identical concurrent briefs must share one execution"
    bodies = {r.get_data() for r in results.values()}
    statuses = {r.status_code for r in results.values()}
    assert statuses == {200}, "no follower is turned away while one leader runs"
    assert len(bodies) == 1, "every caller receives the byte-identical body"


def test_identical_brief_replays_from_cache_then_recomputes_after_ttl(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(envelope, "COALESCER",
                        envelope.ComputeCoalescer(clock=lambda: clock["now"]))
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/feasibility"
    brief = _brief(endpoint)

    first = _post_from(endpoint, brief, "203.0.113.1")
    assert first.status_code == 200
    assert len(calls) == 1
    # A repeat inside the TTL replays the cached answer -- no new solver work.
    cached = _post_from(endpoint, brief, "203.0.113.2")
    assert cached.status_code == 200
    assert cached.get_data() == first.get_data()
    assert len(calls) == 1
    # Past the TTL the cache entry is gone and the brief recomputes.
    clock["now"] += envelope.RESULT_CACHE_TTL_SECONDS + 1
    _post_from(endpoint, brief, "203.0.113.3")
    assert len(calls) == 2


def test_different_canonical_keys_never_share_a_result(monkeypatch):
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/feasibility"
    a = _brief(endpoint)
    b = _brief(endpoint)
    b["fermentables"]["bounds"][0]["maximum_percent"] = 90

    _post_from(endpoint, a, "203.0.113.1")
    _post_from(endpoint, b, "203.0.113.2")
    assert len(calls) == 2, "briefs with different keys must not false-share"


def test_sensory_range_key_ignores_the_queried_descriptors_own_bound(monkeypatch):
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/sensory-range"
    keywords = views.all_grains.get_sensory_keywords()
    target, other = keywords[0], keywords[1]

    def brief(target_bound, other_bound):
        b = _brief(endpoint)
        b["descriptor"] = target
        b["sensory"] = [
            {
                "name": target,
                "minimum": target_bound[0],
                "maximum": target_bound[1],
            },
            {
                "name": other,
                "minimum": other_bound[0],
                "maximum": other_bound[1],
            },
        ]
        return b

    # Differ only in the queried descriptor's own bound -> one execution.
    _post_from(endpoint, brief((0, 5), (0, 5)), "203.0.113.1")
    _post_from(endpoint, brief((1, 4), (0, 5)), "203.0.113.2")
    assert len(calls) == 1, "the queried descriptor's own bound is not part of the key"

    # Differ in a *different* descriptor's bound -> a second execution.
    _post_from(endpoint, brief((0, 5), (0, 4)), "203.0.113.3")
    assert len(calls) == 2, "another descriptor's bound does change the key"


def test_deadline_outcome_is_not_cached(monkeypatch):
    # A transient 503 must never be replayed: an immediately repeated identical
    # brief re-enters the solver rather than being handed the cached timeout.
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/feasibility"
    brief = _brief(endpoint)

    first = _post_from(endpoint, brief, "203.0.113.1")
    second = _post_from(endpoint, brief, "203.0.113.2")
    assert first.status_code == 503
    assert second.status_code == 503
    assert len(calls) == 2, "a deadline is not cached; the repeat recomputes"
