"""Build and exercise the production container under its runtime constraints."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from typing import Any


IMAGE = "brewgen:container-smoke"
CBC_STATE_PATH = "/tmp/brewgen-cbc-state.json"

_CBC_WATCHER = f"""
import json
import os
import signal
import time
from pathlib import Path

state = Path({CBC_STATE_PATH!r})
state.unlink(missing_ok=True)
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    pids = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            if Path("/proc", entry, "comm").read_text().strip() == "cbc":
                pids.append(int(entry))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    if pids:
        try:
            os.kill(pids[0], signal.SIGSTOP)
        except ProcessLookupError:
            continue
        state.write_text(json.dumps({{
            "held_pid": pids[0],
            "samples": [len(pids)],
        }}))
        break
    time.sleep(0.001)
"""

_READ_CBC_STATE = f"""
from pathlib import Path
state = Path({CBC_STATE_PATH!r})
print(state.read_text() if state.exists() else "")
"""

_LIST_CBC_PIDS = """
import json
import os
from pathlib import Path

pids = []
for entry in os.listdir("/proc"):
    if not entry.isdigit():
        continue
    try:
        if Path("/proc", entry, "comm").read_text().strip() == "cbc":
            pids.append(int(entry))
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
print(json.dumps(pids))
"""


def docker(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["docker", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if result.stdout else ""


def container_python(container_id: str, program: str,
                     capture: bool = False, detach: bool = False) -> str:
    exec_args = ["exec"]
    if detach:
        exec_args.append("--detach")
    return docker(
        *exec_args, container_id, "/app/venv/bin/python", "-c", program,
        capture=capture)


def request(port: int, path: str, payload: object | None = None,
            origin: str | None = None,
            visitor: str | None = None,
            timeout: float = 5) -> tuple[int, object | bytes, Any]:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    if origin:
        headers["Origin"] = origin
    if visitor:
        headers["X-Forwarded-For"] = visitor
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read()
        content_type = response.headers.get_content_type()
        parsed = (json.loads(body) if content_type in {
            "application/json", "application/problem+json"} else body)
        status = response.status if hasattr(response, "status") else response.code
        return status, parsed, response.headers


def wait_until_ready(port: int) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            status, _, _ = request(port, "/healthz")
            if status == 200:
                return
        except (ConnectionError, TimeoutError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError("container did not become healthy within 30 seconds")


def generation_brief(style: dict[str, object]) -> dict[str, object]:
    usage = style["grain_usage"]
    assert isinstance(usage, list)
    allowed = [str(grain["slug"]) for grain in usage]
    return {
        "version": 1,
        "style": {
            "slug": style["slug"],
            "original_gravity": 1.055,
        },
        "equipment": {
            "batch_volume_gallons": 5.5,
            "mash_efficiency_percent": 75,
        },
        "fermentables": {
            "allowed_slugs": allowed,
            "bounds": [{
                "slug": grain["slug"],
                "minimum_percent": int(grain["min_percent"]),
                "maximum_percent": int(grain["max_percent"]),
            } for grain in usage],
            "maximum_count": min(
                int(style["unique_fermentable_count"]), len(allowed), 7),
        },
        "sensory": [],
        "color_srm": {"minimum": 3, "maximum": 20},
    }


def smoke_http(port: int) -> None:
    wait_until_ready(port)

    status, health, _ = request(port, "/healthz")
    assert status == 200 and health == {"status": "ok"}

    status, index, _ = request(port, "/")
    assert status == 200 and isinstance(index, bytes) and b'id="app"' in index

    status, grains, headers = request(
        port, "/api/v1/grains", origin="https://example.invalid")
    assert status == 200 and isinstance(grains, list) and grains
    assert headers.get("Access-Control-Allow-Origin") is None

    status, style, _ = request(
        port, "/api/v1/styles/american-pale-ale")
    assert status == 200 and isinstance(style, dict)

    status, result, _ = request(
        port, "/api/v1/grains/recipes", generation_brief(style), timeout=15)
    assert status == 200 and isinstance(result, dict)
    assert result.get("status") in {"complete", "partial"}
    assert result.get("alternatives")


def smoke_concurrent_admission(port: int, container_id: str) -> None:
    """Measure real CBC work while a constrained container sheds a 24-request burst."""
    status, style, _ = request(
        port, "/api/v1/styles/american-pale-ale")
    assert status == 200 and isinstance(style, dict)
    brief = generation_brief(style)
    # Avoid the answer smoke_http just cached.
    brief["style"]["original_gravity"] = 1.056

    admitted: list[tuple[int, object | bytes, Any]] = []

    def run_admitted() -> None:
        admitted.append(request(
            port, "/api/v1/grains/recipes", brief,
            visitor="198.51.100.1", timeout=15))

    # This watcher runs inside the production container, observes a real CBC
    # child, and stops it before it can exit. No application test hook is used.
    container_python(container_id, _CBC_WATCHER, detach=True)
    thread = threading.Thread(target=run_admitted)
    thread.start()

    deadline = time.monotonic() + 5
    state = None
    while time.monotonic() < deadline:
        raw_state = container_python(
            container_id, _READ_CBC_STATE, capture=True)
        if raw_state:
            state = json.loads(raw_state)
            break
        time.sleep(0.01)
    assert state is not None, "admitted request never started CBC"
    held_pid = int(state["held_pid"])
    assert state["samples"] == [1], f"CBC concurrency: {state}"
    assert thread.is_alive(), "CBC finished before the overload burst"

    def overflow(index: int) -> tuple[int, object | bytes, Any, float]:
        started = time.monotonic()
        overflow_brief = json.loads(json.dumps(brief))
        # Distinct valid briefs must reach the slot independently; byte-identical
        # requests correctly coalesce onto the admitted solve.
        overflow_brief["equipment"]["batch_volume_gallons"] += (index + 1) / 100
        try:
            status, body, headers = request(
                port, "/api/v1/grains/recipes", overflow_brief,
                visitor=f"198.51.100.{index + 2}", timeout=2)
        except (TimeoutError, urllib.error.URLError):
            return 0, None, None, time.monotonic() - started
        return status, body, headers, time.monotonic() - started

    try:
        with ThreadPoolExecutor(max_workers=23) as pool:
            overflow_results = list(pool.map(overflow, range(23)))

        active_pids = json.loads(container_python(
            container_id, _LIST_CBC_PIDS, capture=True))
        state["samples"].append(len(active_pids))
        assert state["samples"] == [1, 1], f"CBC concurrency: {state}"
        assert active_pids == [held_pid], (
            f"unexpected active CBC processes: {active_pids}")
        assert all(status == 503 for status, _, _, _ in overflow_results), (
            "overflow requests did not reach the no-queue guard promptly")
        assert all(headers.get_content_type() == "application/problem+json"
                   for _, _, headers, _ in overflow_results)
        assert all(body["status"] == 503 and body["outcome"] == "busy"
                   for _, body, _, _ in overflow_results)
        assert all(headers.get("Retry-After") == "1"
                   for _, _, headers, _ in overflow_results)
        assert max(elapsed for _, _, _, elapsed in overflow_results) < 1
        assert thread.is_alive(), "busy responses waited for the admitted solve"
    finally:
        container_python(
            container_id,
            f"import os, signal; os.kill({held_pid}, signal.SIGCONT)")
        thread.join(timeout=15)

    assert not thread.is_alive()
    assert admitted and admitted[0][0] == 200


def launch_and_smoke(port: int, sentinel: Path | None) -> None:
    server = subprocess.Popen(
        ["gunicorn", "brewgen.backend.views:app"],
        stdout=subprocess.DEVNULL,
    )
    try:
        smoke_http(port)
        if sentinel is not None:
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.touch()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


def smoke_container(image: str) -> None:
    """Exercise the exact production image under its published resource limits."""
    container_name = f"brewgen-smoke-{os.getpid()}"
    container_id = ""
    try:
        container_id = docker(
            "run", "--detach", "--rm", "--name", container_name,
            "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
            "--user", "nonroot", "--cpus", "1", "--memory", "512m",
            "--pids-limit", "64", "--log-driver", "local",
            "--log-opt", "max-size=10m", "--log-opt", "max-file=3",
            "--publish", "127.0.0.1::5000", image, capture=True)
        port_output = docker("port", container_id, "5000/tcp", capture=True)
        port = int(port_output.splitlines()[0].rsplit(":", 1)[1])
        smoke_http(port)
        smoke_concurrent_admission(port, container_id)
    finally:
        if container_id:
            subprocess.run(
                ["docker", "stop", "--time", "5", container_id],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", type=int,
        help="exercise an already-running container instead of building one")
    parser.add_argument(
        "--launch", action="store_true",
        help="launch Gunicorn before exercising the service")
    parser.add_argument(
        "--sentinel", type=Path,
        help="write this file after a successful launched-service smoke test")
    parser.add_argument(
        "--image",
        help="exercise an already-built production image under its resource limits")
    args = parser.parse_args()
    if args.port is not None:
        if args.image is not None:
            parser.error("--port and --image are mutually exclusive")
        if args.launch:
            launch_and_smoke(args.port, args.sentinel)
        else:
            if args.sentinel is not None:
                parser.error("--sentinel requires --launch")
            smoke_http(args.port)
        print("Production HTTP smoke test passed.")
        return

    if shutil.which("docker") is None:
        raise SystemExit("docker is required to run the container smoke test")

    if args.image is not None:
        if args.launch or args.sentinel is not None:
            parser.error("--launch/--sentinel require --port")
        smoke_container(args.image)
        print("Production container smoke test passed.")
        return

    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, text=True,
        stdout=subprocess.PIPE).stdout.strip()
    docker(
        "build", "--platform", "linux/amd64", "--build-arg",
        f"GIT_COMMIT={revision}", "--tag", IMAGE, ".")

    image_revision = docker(
        "inspect", "--format",
        '{{ index .Config.Labels "org.opencontainers.image.revision" }}',
        IMAGE, capture=True)
    if image_revision != revision:
        raise AssertionError(
            f"image revision {image_revision!r} did not match {revision!r}")

    smoke_container(IMAGE)

    print("Production container smoke test passed.")


if __name__ == "__main__":
    main()
