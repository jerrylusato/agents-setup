from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .paths import DEFAULT_PREFIX, default_skills_dest, default_state_file
from .source import ResolvedSource, default_source_spec, resolve_source
from .doctor import print_doctor
from .scaffold import print_scaffold_report, scaffold_project
from .skills import (
    BUNDLES,
    Skill,
    bundle_skills,
    department_title,
    describe_skill,
    group_by_department,
    install_skill,
    installed_only_skills,
    load_skills,
    uninstall_skill,
)
from .state import remove_state_entries, write_state


def ensure_claude_bridge(dest_dir: Path, dry_run: bool) -> str:
    shared = default_skills_dest().expanduser()
    if dest_dir.expanduser().resolve() != shared.resolve():
        return "skipped-custom-destination"

    claude_skills = Path.home() / ".claude" / "skills"
    if claude_skills.is_symlink():
        return "already-linked"
    if claude_skills.exists():
        print(
            f"Note: {claude_skills} is a real directory; left as-is. "
            f"Claude Code will not see {shared} until you merge them."
        )
        return "real-directory-left-untouched"
    if dry_run:
        print(f"would link {claude_skills} -> {shared}  (Claude Code)")
        return "would-create"
    claude_skills.parent.mkdir(parents=True, exist_ok=True)
    claude_skills.symlink_to(shared)
    print(f"Linked {claude_skills} -> {shared}  (Claude Code now shares the same skills)")
    return "created"


def prompt(message: str) -> str:
    try:
        return input(message).strip().lower()
    except EOFError as exc:
        raise SystemExit("No interactive input available. Re-run with --all for a bulk operation.") from exc


def ask_department(action: str, department: str, skills: list[Skill], dest_dir: Path) -> str:
    installed_count = sum(1 for skill in skills if skill.target(dest_dir).exists() or skill.target(dest_dir).is_symlink())
    print(f"\n== {department_title(department)} ==")
    print(f"{len(skills)} available, {installed_count} currently installed.")
    for index, skill in enumerate(skills, start=1):
        status = "installed" if skill.target(dest_dir).exists() or skill.target(dest_dir).is_symlink() else "not installed"
        print(f"  {index:>2}. {skill.label:<38} {skill.destination_name:<36} {status}")
        if skill.description:
            print(f"      {skill.description[:93]}{'...' if len(skill.description) > 93 else ''}")

    verb = "install" if action == "install" else "uninstall"
    while True:
        answer = prompt(f"Choose for {department_title(department)}: [a]ll, [s]elect one by one, [n]one, [q]uit: ")
        if answer in {"a", "all"}:
            return "all"
        if answer in {"s", "select"}:
            return "select"
        if answer in {"", "n", "none", "skip"}:
            return "none"
        if answer in {"q", "quit"}:
            raise SystemExit(f"Stopped before {verb} finished.")
        print("Pick a, s, n, or q.")


def ask_skill(action: str, skill: Skill, dest_dir: Path) -> bool:
    target = skill.target(dest_dir)
    installed = target.exists() or target.is_symlink()
    if action == "uninstall" and not installed:
        return False

    status = "installed" if installed else "not installed"
    while True:
        answer = prompt(f"  {action} {skill.destination_name} ({skill.label}, {status})? [y/N]: ")
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            return False
        print("Answer y or n.")


def select_skills(
    action: str,
    skills: list[Skill],
    dest_dir: Path,
    prefix: str,
    select_all: bool,
    bundle: str | None = None,
) -> list[Skill]:
    if action == "uninstall":
        skills = [*skills, *installed_only_skills(skills, dest_dir, prefix)]
        prompted_skills = [
            skill for skill in skills if skill.target(dest_dir).exists() or skill.target(dest_dir).is_symlink()
        ]
        if not prompted_skills:
            print(f"No installed IPF skills found in {dest_dir.expanduser()}.")
            return []
    else:
        prompted_skills = bundle_skills(skills, bundle)

    if select_all:
        return prompted_skills

    print("\nIPF Skills")
    if bundle:
        print(f"Bundle: {bundle}. Review the included skills before anything changes.")
    else:
        print("Pick a department, then decide exactly which skills should change.")
    print("Nothing is changed until the final confirmation.")

    selected: list[Skill] = []
    for department, department_skills in group_by_department(prompted_skills).items():
        choice = ask_department(action, department, department_skills, dest_dir)
        if choice == "all":
            selected.extend(department_skills)
        elif choice == "select":
            selected.extend(skill for skill in department_skills if ask_skill(action, skill, dest_dir))

    return selected


def confirm_selection(action: str, selected: list[Skill], dry_run: bool, assume_yes: bool = False) -> bool:
    if not selected:
        print("No skills selected.")
        return False

    print(f"\nReady to {action} {len(selected)} skill(s):")
    for skill in selected:
        print(f"  - {describe_skill(skill)}")

    if dry_run:
        print("\nDry run only. Planned changes:")
        return True
    if assume_yes:
        print(f"\nProceeding with {action} because --all was provided.")
        return True

    while True:
        answer = prompt(f"\nProceed with {action}? [y/N]: ")
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            print("No changes made.")
            return False
        print("Answer y or n.")


def add_common_skill_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", default=default_source_spec(), help="Skills source: local skills directory/archive, or github-release:OWNER/REPO@TAG.")
    parser.add_argument("--dest", type=Path, default=default_skills_dest(), help="User skills directory.")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="Prefix installed skill names.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files.")


def cleanup_source(resolved: ResolvedSource) -> None:
    for cleanup_dir in resolved.cleanup_dirs:
        shutil.rmtree(cleanup_dir, ignore_errors=True)


def load_for_args(args: argparse.Namespace) -> tuple[list[Skill], Path, str, ResolvedSource]:
    resolved = resolve_source(args.source)
    source = resolved.skills_dir
    prefix = args.prefix.strip("-")
    return load_skills(source, prefix), source, prefix, resolved


def install_command(args: argparse.Namespace) -> int:
    skills, _, prefix, resolved = load_for_args(args)
    try:
        dest = args.dest.expanduser()
        selected = select_skills("install", skills, dest, prefix, args.all, args.bundle)
        if not confirm_selection("install", selected, args.dry_run, args.all):
            return 0

        if not args.dry_run:
            dest.mkdir(parents=True, exist_ok=True)

        for skill in selected:
            print(install_skill(skill, dest, not args.no_replace, args.dry_run))

        claude_bridge = "skipped"
        if not args.no_claude_link:
            claude_bridge = ensure_claude_bridge(dest, args.dry_run)

        write_state(default_state_file(), dest_dir=dest, installed=selected, claude_bridge=claude_bridge, dry_run=args.dry_run)
        print(f"\nSkills directory: {dest.expanduser()}")
        print("Restart your agent (Codex, Claude Code, Cursor, Gemini CLI, Copilot, Windsurf, ...) to pick up skill changes.")
        return 0
    finally:
        cleanup_source(resolved)


def uninstall_command(args: argparse.Namespace) -> int:
    skills, _, prefix, resolved = load_for_args(args)
    try:
        dest = args.dest.expanduser()
        selected = select_skills("uninstall", skills, dest, prefix, args.all)
        if not confirm_selection("uninstall", selected, args.dry_run, args.all):
            return 0
        for skill in selected:
            print(uninstall_skill(skill, dest, args.dry_run))
        remove_state_entries(default_state_file(), selected, args.dry_run)
        print(f"\nSkills directory: {dest.expanduser()}")
        return 0
    finally:
        cleanup_source(resolved)


def update_command(args: argparse.Namespace) -> int:
    skills, _, prefix, resolved = load_for_args(args)
    try:
        dest = args.dest.expanduser()
        installed = [
            skill for skill in skills if skill.target(dest).exists() or skill.target(dest).is_symlink()
        ]
        if args.all:
            selected = skills
        elif args.bundle:
            selected = [skill for skill in bundle_skills(skills, args.bundle) if skill in installed]
        else:
            selected = installed

        if not selected:
            print(f"No installed IPF skills found in {dest}. Use install to add skills first.")
            return 0
        if not confirm_selection("update", selected, args.dry_run, args.all):
            return 0
        if not args.dry_run:
            dest.mkdir(parents=True, exist_ok=True)
        for skill in selected:
            print(install_skill(skill, dest, True, args.dry_run))
        claude_bridge = "skipped" if args.no_claude_link else ensure_claude_bridge(dest, args.dry_run)
        write_state(default_state_file(), dest_dir=dest, installed=selected, claude_bridge=claude_bridge, dry_run=args.dry_run)
        return 0
    finally:
        cleanup_source(resolved)


def init_command(args: argparse.Namespace) -> int:
    report = scaffold_project(args.root, args.dry_run)
    print_scaffold_report(report)
    return 0


def doctor_command(args: argparse.Namespace) -> int:
    skills, _, prefix, resolved = load_for_args(args)
    try:
        print_doctor(args.root, skills, prefix, args.dest)
        return 0
    finally:
        cleanup_source(resolved)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agents-setup",
        description="Set up projects for AI agents and install IPF skills without cloning ipf-skills.",
    )
    subcommands = parser.add_subparsers(dest="command")

    init = subcommands.add_parser("init", help="Scaffold project-level agent skill discovery.")
    init.add_argument("--root", type=Path, default=Path("."), help="Project root to scaffold.")
    init.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files.")
    init.set_defaults(func=init_command)

    install = subcommands.add_parser("install", help="Install IPF skills globally.")
    add_common_skill_args(install)
    install.add_argument("--all", action="store_true", help="Install every discovered skill without prompts.")
    install.add_argument("--bundle", choices=sorted(BUNDLES), help="Install a recommended bundle.")
    install.add_argument("--no-replace", action="store_true", help="Skip skills that already exist.")
    install.add_argument("--no-claude-link", action="store_true", help="Skip ~/.claude/skills bridge.")
    install.set_defaults(func=install_command)

    update = subcommands.add_parser("update", help="Refresh installed IPF skills.")
    add_common_skill_args(update)
    update.add_argument("--all", action="store_true", help="Install/update every discovered skill.")
    update.add_argument("--bundle", choices=sorted(BUNDLES), help="Update installed skills from a bundle.")
    update.add_argument("--no-claude-link", action="store_true", help="Skip ~/.claude/skills bridge.")
    update.set_defaults(func=update_command)

    uninstall = subcommands.add_parser("uninstall", help="Remove IPF-installed global skills.")
    add_common_skill_args(uninstall)
    uninstall.add_argument("--all", action="store_true", help="Uninstall every detected IPF skill without prompts.")
    uninstall.set_defaults(func=uninstall_command)

    doctor = subcommands.add_parser("doctor", help="Inspect project and global agent setup.")
    add_common_skill_args(doctor)
    doctor.add_argument("--root", type=Path, default=Path("."), help="Project root to inspect.")
    doctor.set_defaults(func=doctor_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
