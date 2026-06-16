from __future__ import annotations

from pathlib import Path

from .paths import default_state_file
from .skills import Skill, installed_only_skills
from .state import read_state


def _status(path: Path) -> str:
    if path.is_symlink():
        target = path.readlink()
        if path.exists():
            return f"symlink -> {target}"
        return f"broken symlink -> {target}"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "missing"


def _check_link(path: Path, expected: str) -> str:
    if path.is_symlink():
        target = path.readlink().as_posix()
        if target == expected and path.exists():
            return f"ok: {path} -> {target}"
        if target == expected:
            return f"broken: {path} -> {target}"
        return f"check: {path} -> {target}; expected {expected}"
    if path.exists():
        return f"manual: {path} is a real {_status(path)}; left untouched by setup"
    return f"missing: {path}; run init to create it"


def print_doctor(root: Path, skills: list[Skill], prefix: str, global_dest: Path) -> None:
    root = root.expanduser().resolve()
    global_dest = global_dest.expanduser()
    state_file = default_state_file()

    print(f"Project: {root}")
    print(f"- .agents/skills: {_status(root / '.agents' / 'skills')}")
    print(f"- .agents/workflows: {_status(root / '.agents' / 'workflows')}")
    print(f"- {_check_link(root / '.claude' / 'skills', '../.agents/skills')}")
    print(f"- {_check_link(root / '.junie' / 'skills', '../.agents/skills')}")

    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    print(f"- AGENTS.md: {_status(agents)}")
    if claude.is_symlink():
        target = claude.readlink().as_posix()
        marker = "ok" if target == "AGENTS.md" else "check"
        print(f"- CLAUDE.md: {marker}: symlink -> {target}")
    else:
        print(f"- CLAUDE.md: {_status(claude)}")

    print()
    print(f"Global skills: {global_dest.expanduser()}")
    print(f"- skills directory: {_status(global_dest.expanduser())}")
    print(f"- {_check_link(Path.home() / '.claude' / 'skills', str(global_dest.expanduser()))}")

    installed = [
        skill
        for skill in skills
        if skill.target(global_dest).exists() or skill.target(global_dest).is_symlink()
    ]
    stale = installed_only_skills(skills, global_dest, prefix)
    print(f"- known IPF skills installed: {len(installed)}")
    print(f"- installed-only/stale IPF skills: {len(stale)}")
    for skill in stale[:10]:
        print(f"  - {skill.destination_name}")
    if len(stale) > 10:
        print(f"  ... {len(stale) - 10} more")

    state = read_state(state_file)
    if state:
        if state.get("_invalid"):
            print(f"- state file: invalid JSON at {state_file}")
        else:
            print(f"- state file: {state_file} ({len(state.get('installed_skills', []))} recorded skills)")
    else:
        print(f"- state file: missing ({state_file})")

    print()
    print("Notes:")
    print("- Junie symlink support should be verified in the installed IDE version.")
    print("- Antigravity's .agent/.agents path support is still ambiguous; verify locally before relying on it.")
