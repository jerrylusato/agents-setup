from __future__ import annotations

from pathlib import Path


DEFAULT_PREFIX = "ipf"
STATE_FILE_NAME = ".ipf-skills.json"


def default_agents_home() -> Path:
    return Path.home() / ".agents"


def default_skills_dest() -> Path:
    return default_agents_home() / "skills"


def default_state_file() -> Path:
    return default_agents_home() / STATE_FILE_NAME
