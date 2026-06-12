"""Loaders for example/local candidate profiles.

``load_sample_profile()`` returns the synthetic fixture committed to the repo —
a fictional candidate used for tests and skill development. ``load_profile(path)``
loads any profile JSON from disk (e.g. a real, gitignored ``profiles/`` file).
"""

from __future__ import annotations

from pathlib import Path

from job_hunt_assistant.profile import CandidateProfile

# Repo root = three parents up from this file (src/job_hunt_assistant/samples.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PROFILE_PATH = _REPO_ROOT / "examples" / "sample_profile.json"


def load_profile(path: str | Path) -> CandidateProfile:
    """Load and validate a candidate profile from a JSON file."""
    return CandidateProfile.from_json(Path(path).read_text())


def load_sample_profile() -> CandidateProfile:
    """Load the synthetic sample profile bundled with the repo."""
    return load_profile(SAMPLE_PROFILE_PATH)
