"""Guardrails for the GHCR release/rollback delivery boundary.

These assert the security-critical shape of the CI, release, and rollback
workflows through their public interface — the committed workflow files. They
exist to fail loudly if a future edit reverts the `main` trigger to `master`,
drops the publish guard, breaks the shared concurrency group that serializes the
mutable `release` tag, or weakens the blocking container scan.
"""

import datetime
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"

# A committed trivy suppression (`.trivyignore`, auto-loaded by the scan) must
# never silently or permanently hollow out the gate. Every advisory line carries
# an `exp:YYYY-MM-DD` expiry in the future and a rationale on the comment line
# directly above it. See docs/RELEASE.md, "Recording an unfixable finding".
_ADVISORY = re.compile(r"^(?P<id>(?:CVE-\d{4}-\d+|GHSA-[0-9a-z]+(?:-[0-9a-z]+)+))\b")
_EXPIRY = re.compile(r"\bexp:(\d{4}-\d{2}-\d{2})\b")


def _trivyignore_violations(text: str, today: datetime.date) -> list[str]:
    """Return one message per unguarded/stale suppression; empty == clean."""
    problems: list[str] = []
    rationale = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            rationale = None
            continue
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            rationale = body or None
            continue
        match = _ADVISORY.match(line)
        ident = match.group("id") if match else line.split()[0]
        expiry = _EXPIRY.search(line)
        if not expiry:
            problems.append(f"{ident}: missing exp:YYYY-MM-DD expiry")
        else:
            try:
                when = datetime.date.fromisoformat(expiry.group(1))
            except ValueError:
                problems.append(f"{ident}: unparseable expiry {expiry.group(1)!r}")
            else:
                if when < today:
                    problems.append(f"{ident}: expiry {when.isoformat()} already passed")
        if not rationale:
            problems.append(f"{ident}: missing rationale on the preceding comment line")
        rationale = None
    return problems


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


def test_js_audit_is_scoped_to_shipped_dependencies():
    """The JS audit must stay scoped to what the container ships.

    Auditing dev/test tooling flags advisories that never reach the image and
    reds out `main`, which skips the whole image build/scan/publish job. The
    shipped artifact is covered by the blocking trivy scan instead.
    """
    ci = _read("ci.yml")
    assert "npm audit --audit-level=high --omit=dev" in ci


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


def test_no_unguarded_or_expired_scan_suppressions():
    """Any committed scan suppression must be justified and still in date.

    The blocking scan only stays meaningful if a suppression cannot quietly
    linger. A silent (`.trivyignore.yaml` is not auto-guarded here) or
    metadata-poor suppression turns the suite red rather than hollowing out the
    gate. Passes today because no suppression is needed — the flagged advisory
    was fixed by refreshing the base image.
    """
    today = datetime.date.today()
    plain = REPO / ".trivyignore"
    if plain.exists():
        problems = _trivyignore_violations(plain.read_text(encoding="utf-8"), today)
        assert not problems, f".trivyignore: {problems}"
    # A YAML ignore file is not auto-guarded by the plain-format check above, so
    # disallow it outright: suppressions belong in the guarded `.trivyignore`.
    assert not (REPO / ".trivyignore.yaml").exists(), (
        "Use .trivyignore (rationale + exp: date) so suppressions stay guarded."
    )


def test_trivyignore_guard_rejects_silent_or_stale_suppressions():
    """The guard itself: a fixed date proves each failure mode is caught."""
    today = datetime.date(2026, 7, 28)
    good = "# unreachable: brewgen parses no untrusted HTML\nCVE-2026-15308 exp:2026-10-01\n"
    assert _trivyignore_violations(good, today) == []
    # No rationale above the advisory.
    assert _trivyignore_violations("CVE-2026-15308 exp:2026-10-01\n", today)
    # No expiry date.
    assert _trivyignore_violations("# reason\nCVE-2026-15308\n", today)
    # Expiry already in the past.
    assert _trivyignore_violations("# reason\nCVE-2026-15308 exp:2020-01-01\n", today)
