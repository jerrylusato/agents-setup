from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .skills import Skill


def read_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_invalid": True, "path": str(path)}


def write_state(
    path: Path,
    *,
    dest_dir: Path,
    installed: list[Skill],
    claude_bridge: str,
    dry_run: bool,
) -> None:
    if dry_run:
        return

    existing = read_state(path)
    existing_skills = {
        item.get("name"): item
        for item in existing.get("installed_skills", [])
        if isinstance(item, dict) and item.get("name")
    }
    for skill in installed:
        existing_skills[skill.destination_name] = {
            "name": skill.destination_name,
            "label": skill.label,
            "department": skill.department,
            "source": str(skill.source_dir),
        }

    payload = {
        "package": "@jerrylusato/agents-setup",
        "version": __version__,
        "updated_at": datetime.now(UTC).isoformat(),
        "destination": str(dest_dir.expanduser()),
        "claude_bridge": claude_bridge,
        "installed_skills": sorted(existing_skills.values(), key=lambda item: item["name"]),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def remove_state_entries(path: Path, removed: list[Skill], dry_run: bool) -> None:
    if dry_run or not path.exists():
        return

    existing = read_state(path)
    removed_names = {skill.destination_name for skill in removed}
    installed = [
        item
        for item in existing.get("installed_skills", [])
        if isinstance(item, dict) and item.get("name") not in removed_names
    ]
    existing["installed_skills"] = installed
    existing["updated_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
