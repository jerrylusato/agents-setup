from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


AGENTS_STUB = """# Project agent guide

<!-- One source of truth for every AI coding agent. AGENTS.md is read by Codex,
     Cursor, Gemini CLI, Copilot and others; CLAUDE.md is a symlink to this file. -->

## What this project is

(One or two lines: what it does, the stack, anything an agent must know first.)

## Conventions

- (Commit format, branch rules, how to run tests, etc.)

## Skills

Reusable skills live in `.agents/skills/` and are shared across all agents.
"""


@dataclass
class ScaffoldReport:
    root: Path
    created: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    dry_run: bool = False


def ensure_dir(path: Path, label: str, report: ScaffoldReport) -> None:
    if path.is_dir():
        return
    if not report.dry_run:
        path.mkdir(parents=True, exist_ok=True)
    report.created.append(label)


def ensure_link(link: Path, target: str, label: str, report: ScaffoldReport) -> None:
    if link.is_symlink():
        current = link.readlink().as_posix()
        if current == target:
            report.kept.append(f"{label} already linked")
            return
        if not report.dry_run:
            link.unlink()
            link.symlink_to(target)
        report.fixed.append(f"{label} -> {target} (was -> {current})")
        return

    if link.exists():
        report.kept.append(f"{label} real file/dir exists; left untouched")
        return

    if not report.dry_run:
        link.symlink_to(target)
    report.created.append(f"{label} -> {target}")


def scaffold_project(root: Path, dry_run: bool = False) -> ScaffoldReport:
    root = root.expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    report = ScaffoldReport(root=root, dry_run=dry_run)

    ensure_dir(root / ".agents" / "skills", ".agents/skills (canonical skills store)", report)

    ensure_dir(root / ".claude", ".claude", report)
    ensure_link(root / ".claude" / "skills", "../.agents/skills", ".claude/skills (Claude Code)", report)

    ensure_dir(root / ".junie", ".junie", report)
    ensure_link(root / ".junie" / "skills", "../.agents/skills", ".junie/skills (JetBrains Junie)", report)

    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    if not agents.exists() and not claude.exists():
        if not dry_run:
            agents.write_text(AGENTS_STUB, encoding="utf-8")
        report.created.append("AGENTS.md (stub - please fill it in)")
        ensure_link(claude, "AGENTS.md", "CLAUDE.md (Claude Code instructions)", report)
    elif agents.exists() and not claude.exists():
        ensure_link(claude, "AGENTS.md", "CLAUDE.md (Claude Code instructions)", report)
    elif claude.is_symlink():
        ensure_link(claude, "AGENTS.md", "CLAUDE.md (Claude Code instructions)", report)
    else:
        report.kept.append("AGENTS.md / CLAUDE.md real instruction file(s) exist; merge by hand if needed")

    return report


def print_scaffold_report(report: ScaffoldReport) -> None:
    print(f"Scaffolding agent skills in: {report.root}")
    if report.dry_run:
        print("(dry run - no changes will be written)")
    print()
    for item in report.created:
        print(f"  created  {item}")
    for item in report.fixed:
        print(f"  fixed    {item}")
    for item in report.kept:
        print(f"  kept     {item}")
    print()
    print(f"Done: {len(report.created)} created, {len(report.fixed)} fixed, {len(report.kept)} left as-is.")
    skills_dir = report.root / ".agents" / "skills"
    if skills_dir.exists() and not any(skills_dir.iterdir()):
        print()
        print("Next: add skill folders to .agents/skills/<skill-name>/SKILL.md")
        print("      or run `agents-setup install` for user-level IPF skills.")
