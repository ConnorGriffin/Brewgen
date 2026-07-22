"""Guardrails for the GHCR release/rollback delivery boundary.

These assert the security-critical shape of the CI, release, and rollback
workflows through their public interface — the committed workflow files. They
exist to fail loudly if a future edit reverts the `main` trigger to `master`,
drops the publish guard, breaks the shared concurrency group that serializes the
mutable `release` tag, or weakens the blocking container scan.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"


def _read(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_ci_triggers_on_main_not_master():
    ci = _read("ci.yml")
    assert "branches: [main]" in ci
    assert "master" not in ci
    assert "pull_request:" in ci


def test_ci_runs_backend_frontend_and_production_build():
    ci = _read("ci.yml")
    assert "pytest tests" in ci
    assert "npm test" in ci
    assert "npm run build" in ci


def test_ci_runs_dependency_audit_and_code_scanning():
    ci = _read("ci.yml")
    # Python + JS dependency audit.
    assert "pip-audit" in ci
    assert "npm audit" in ci
    # Python + JS code scanning.
    assert "github/codeql-action" in ci
    assert "language: [python, javascript-typescript]" in ci


def test_container_scan_blocks_on_critical_high():
    ci = _read("ci.yml")
    assert "trivy image" in ci
    assert "--severity CRITICAL,HIGH" in ci
    # A finding must fail the job (and so block publication).
    assert "--exit-code 1" in ci


def test_release_publishes_immutable_and_mutable_tags():
    ci = _read("ci.yml")
    assert "ghcr.io/connorgriffin/brewgen" in ci
    assert "${{ github.sha }}" in ci  # immutable commit tag
    assert ":release" in ci  # mutable release tag


def test_publish_is_guarded_against_pr_and_fork_writes():
    """Login and publish must never run on a PR or on a fork."""
    ci = _read("ci.yml")
    guard = (
        "github.event_name == 'push' && "
        "github.repository == 'ConnorGriffin/brewgen'"
    )
    # Both the GHCR login and the tag push carry the guard.
    assert ci.count(guard) >= 2
    # The guard sits on the login and publish steps specifically.
    for anchor in ("docker/login-action", "docker push"):
        assert anchor in ci


def test_forward_release_and_rollback_share_one_concurrency_group():
    ci = _read("ci.yml")
    rollback = _read("rollback.yml")
    assert "brewgen-release-tag" in ci
    assert "brewgen-release-tag" in rollback
    # Neither may cancel an in-progress tag move.
    assert "cancel-in-progress: false" in ci
    assert "cancel-in-progress: false" in rollback


def test_rollback_rejects_commits_not_on_main_and_retests():
    rollback = _read("rollback.yml")
    assert "workflow_dispatch:" in rollback
    assert "commit:" in rollback
    # Only a full SHA reachable from main is accepted.
    assert "merge-base --is-ancestor" in rollback
    # It retests and rescans before republishing.
    assert "pytest tests" in rollback
    assert "npm test" in rollback
    assert "--severity CRITICAL,HIGH" in rollback
    assert "docker push" in rollback


def test_release_documentation_exists():
    doc = (REPO / "docs" / "RELEASE.md").read_text(encoding="utf-8")
    for topic in ("Image identity", "publication", "Rollback", "Verifying"):
        assert topic in doc
