"""Build and exercise the production container under its runtime constraints."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any


IMAGE = "brewgen:container-smoke"


def docker(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["docker", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if result.stdout else ""


def request(port: int, path: str, payload: object | None = None,
            origin: str | None = None,
            timeout: float = 5) -> tuple[int, object | bytes, Any]:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get_content_type()
        parsed = json.loads(body) if content_type == "application/json" else body
        return response.status, parsed, response.headers


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


def generation_brief(grains: list[dict[str, object]]) -> dict[str, object]:
    by_category: dict[str, list[str]] = {}
    for grain in grains:
        by_category.setdefault(str(grain["category"]), []).append(str(grain["slug"]))

    fermentables = [
        {"slug": slug, "min_percent": 0, "max_percent": 100}
        for slug in by_category["base"][:2]
    ] + [
        {"slug": slug, "min_percent": 0, "max_percent": 25}
        for slug in by_category["crystal"][:2]
    ]
    return {
        "fermentable_list": fermentables,
        "category_model": [
            {"name": "base", "min_percent": 60, "max_percent": 100,
             "unique_fermentable_count": 2},
            {"name": "crystal", "min_percent": 0, "max_percent": 25,
             "unique_fermentable_count": 2},
        ],
        "max_unique_fermentables": 4,
        "equipment_profile": {"target_volume_gallons": 5.5,
                              "mash_efficiency": 75},
        "beer_profile": {"min_color_srm": 3, "max_color_srm": 20,
                         "original_sg": 1.055},
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

    status, result, _ = request(
        port, "/api/v1/grains/recipes", generation_brief(grains), timeout=15)
    assert status == 200 and isinstance(result, dict)
    assert result.get("status") in {"complete", "partial"}
    assert result.get("alternatives")


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
    args = parser.parse_args()
    if args.port is not None:
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

    container_name = f"brewgen-smoke-{os.getpid()}"
    container_id = ""
    try:
        container_id = docker(
            "run", "--detach", "--rm", "--name", container_name,
            "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
            "--user", "nonroot", "--cpus", "1", "--memory", "512m",
            "--pids-limit", "64", "--log-driver", "local",
            "--log-opt", "max-size=10m", "--log-opt", "max-file=3",
            "--publish", "127.0.0.1::5000", IMAGE, capture=True)
        port_output = docker("port", container_id, "5000/tcp", capture=True)
        port = int(port_output.splitlines()[0].rsplit(":", 1)[1])
        smoke_http(port)
    finally:
        if container_id:
            subprocess.run(
                ["docker", "stop", "--time", "5", container_id],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Production container smoke test passed.")


if __name__ == "__main__":
    main()
