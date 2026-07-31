"""Guardrail that AGENTS.md names every command the backend CI job runs.

Exists so AGENTS.md can't quietly drift back to understating the real gate
(the failure mode of issue #83): an agent that trusts a stale AGENTS.md and
only runs part of what CI runs can push work CI then fails.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _backend_job_run_commands(ci_yaml: str) -> list[str]:
    """Return each `run:` command inside the `backend:` job, in order."""
    job_start = re.search(r"^  backend:\n", ci_yaml, re.MULTILINE)
    next_job = re.search(r"^  \w[\w-]*:\n", ci_yaml[job_start.end() :], re.MULTILINE)
    job_text = ci_yaml[job_start.end() : job_start.end() + next_job.start()]
    return re.findall(r"- run: (.+)", job_text)


def test_agents_md_states_every_backend_ci_command():
    ci_yaml = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    backend_commands = _backend_job_run_commands(ci_yaml)
    assert backend_commands, "expected at least one `run:` step in the backend job"

    agents_md = re.sub(r"\s+", " ", (REPO / "AGENTS.md").read_text())

    # AGENTS.md documents the gate agents must run before pushing, not the CI
    # job's own bootstrapping (e.g. installing test dependencies).
    gate_commands = [c for c in backend_commands if not c.startswith("python3 -m pip install")]
    assert gate_commands, "expected at least one non-install command in the backend job"

    for command in gate_commands:
        normalized = re.sub(r"\s+", " ", command).strip()
        assert normalized in agents_md, (
            f"AGENTS.md does not state the backend CI command: {normalized!r}"
        )
