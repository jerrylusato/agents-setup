from __future__ import annotations

import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path

from .paths import DEFAULT_PREFIX


BUNDLES: dict[str, set[str]] = {
    "shared": {"shared"},
    "frontend": {"shared", "frontend"},
    "backend": {"shared", "backend"},
    "mobile": {"shared", "mobile"},
    "data": {"shared", "emerging-tech/data-engineering"},
    "all": {"*"},
}


@dataclass(frozen=True)
class Skill:
    source_dir: Path
    destination_name: str
    department: str
    label: str
    description: str
    exact_install_name: bool = False

    def target(self, dest_dir: Path) -> Path:
        return dest_dir / self.destination_name


def find_skill_dirs(source: Path) -> list[Path]:
    return sorted(path.parent for path in source.rglob("SKILL.md"))


def read_frontmatter_scalar(skill_dir: Path, key: str) -> str:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return ""

    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return ""

    prefix = f"{key}:"
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip().strip('"\'')
    return ""


def installed_name(skill_dir: Path, prefix: str = DEFAULT_PREFIX) -> str:
    exact_name = read_frontmatter_scalar(skill_dir, "install_name")
    if exact_name:
        return exact_name
    source_name = skill_dir.name
    if prefix and not source_name.startswith(f"{prefix}-"):
        return f"{prefix}-{source_name}"
    return source_name


def relative_label(skill_dir: Path, source: Path) -> str:
    return "/".join(skill_dir.relative_to(source).parts)


def department_name(skill_dir: Path, source: Path) -> str:
    relative = skill_dir.relative_to(source)
    if len(relative.parts) > 2 and relative.parts[0] == "emerging-tech":
        return "/".join(relative.parts[:2])
    return relative.parts[0] if len(relative.parts) > 1 else "shared"


def display_label(skill_dir: Path, source: Path) -> str:
    relative = skill_dir.relative_to(source)
    if len(relative.parts) <= 1:
        return skill_dir.name
    return "/".join(relative.parts[1:])


def read_frontmatter_description(skill_dir: Path) -> str:
    skill_file = skill_dir / "SKILL.md"
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return ""

    description_lines: list[str] = []
    in_description = False
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("description:"):
            raw_value = line.removeprefix("description:").strip()
            if raw_value in {">", ">-", "|", "|-"}:
                in_description = True
                continue
            return raw_value.strip('"')
        if in_description:
            if line and not line.startswith((" ", "\t")):
                break
            description_lines.append(line.strip())

    return " ".join(part for part in description_lines if part)


def build_skills(skill_dirs: list[Path], source: Path, prefix: str = DEFAULT_PREFIX) -> list[Skill]:
    return [
        Skill(
            source_dir=skill_dir,
            destination_name=installed_name(skill_dir, prefix),
            department=department_name(skill_dir, source),
            label=display_label(skill_dir, source),
            description=read_frontmatter_description(skill_dir),
            exact_install_name=bool(read_frontmatter_scalar(skill_dir, "install_name")),
        )
        for skill_dir in skill_dirs
    ]


def load_skills(source: Path, prefix: str = DEFAULT_PREFIX) -> list[Skill]:
    if not source.exists():
        raise SystemExit(f"Source directory does not exist: {source}")

    skill_dirs = find_skill_dirs(source)
    if not skill_dirs:
        raise SystemExit(f"No SKILL.md files found under: {source}")

    ensure_unique_names(skill_dirs, prefix)
    return build_skills(skill_dirs, source, prefix)


def ensure_unique_names(skill_dirs: list[Path], prefix: str) -> None:
    by_name: dict[str, list[Path]] = {}
    for skill_dir in skill_dirs:
        by_name.setdefault(installed_name(skill_dir, prefix), []).append(skill_dir)

    duplicates = {name: paths for name, paths in by_name.items() if len(paths) > 1}
    if not duplicates:
        return

    lines = ["Skill names must be unique for the flat skills layout:"]
    for name, paths in sorted(duplicates.items()):
        joined = ", ".join(str(path) for path in paths)
        lines.append(f"- {name}: {joined}")
    raise SystemExit("\n".join(lines))


def installed_only_skills(skills: list[Skill], dest_dir: Path, prefix: str) -> list[Skill]:
    if not dest_dir.exists():
        return []

    known_names = {skill.destination_name for skill in skills}
    prefix_pattern = f"{prefix}-*" if prefix else "*"
    extras: list[Skill] = []
    for installed_dir in sorted(dest_dir.glob(prefix_pattern)):
        if not installed_dir.is_dir() or installed_dir.name in known_names:
            continue
        extras.append(
            Skill(
                source_dir=installed_dir,
                destination_name=installed_dir.name,
                department="installed-only",
                label=installed_dir.name,
                description=read_frontmatter_description(installed_dir),
            )
        )
    return extras


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def rewrite_installed_name(target: Path, name: str) -> None:
    skill_file = target / "SKILL.md"
    lines = skill_file.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("name: "):
            lines[index] = f"name: {name}\n"
            skill_file.write_text("".join(lines), encoding="utf-8")
            return
    raise RuntimeError(f"Missing frontmatter name in {skill_file}")


def install_skill(skill: Skill, dest_dir: Path, replace: bool, dry_run: bool) -> str:
    target = skill.target(dest_dir)
    if target.exists() or target.is_symlink():
        if not replace:
            return f"skip    {target.name} already exists"
        if skill.exact_install_name and read_frontmatter_scalar(target, "install_name") != skill.destination_name:
            raise SystemExit(
                f"Refusing to replace unmanaged canonical skill: {target}. "
                "Remove or rename it explicitly, then retry."
            )
        if not dry_run:
            remove_existing(target)

    if dry_run:
        prefix = "replace" if target.exists() or target.is_symlink() else "copy"
        return f"{prefix:<7} {skill.source_dir} -> {target}"

    shutil.copytree(skill.source_dir, target)
    rewrite_installed_name(target, skill.destination_name)
    return f"copied  {target.name}"


def uninstall_skill(skill: Skill, dest_dir: Path, dry_run: bool) -> str:
    target = skill.target(dest_dir)
    if dry_run:
        action = "remove" if target.exists() or target.is_symlink() else "missing"
        return f"{action:<7} {target}"

    if not target.exists() and not target.is_symlink():
        return f"missing {target.name}"

    remove_existing(target)
    return f"removed {target.name}"


def group_by_department(skills: list[Skill]) -> dict[str, list[Skill]]:
    groups: dict[str, list[Skill]] = {}
    for skill in skills:
        groups.setdefault(skill.department, []).append(skill)
    return groups


def department_title(department: str) -> str:
    return department.replace("-", " ").replace("/", " / ").title()


def bundle_skills(skills: list[Skill], bundle: str | None) -> list[Skill]:
    if not bundle:
        return skills
    if bundle not in BUNDLES:
        valid = ", ".join(sorted(BUNDLES))
        raise SystemExit(f"Unknown bundle {bundle!r}. Choose one of: {valid}")

    departments = BUNDLES[bundle]
    if "*" in departments:
        return skills

    return [skill for skill in skills if skill.department in departments]


def describe_skill(skill: Skill) -> str:
    base = f"{skill.destination_name} ({department_title(skill.department)} / {skill.label})"
    if skill.description:
        return f"{base}: {textwrap.shorten(skill.description, width=96, placeholder='...')}"
    return base
