from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SKILLS_SOURCE = "github-release:iPFSoftwares/ipf-skills@latest"
ENV_SOURCE = "IPF_AGENTS_SKILLS_SOURCE"


@dataclass(frozen=True)
class ResolvedSource:
    skills_dir: Path
    cleanup_dirs: tuple[Path, ...] = ()
    description: str = ""


def default_source_spec() -> str:
    return os.environ.get(ENV_SOURCE, DEFAULT_SKILLS_SOURCE)


def resolve_source(spec: str) -> ResolvedSource:
    if spec.startswith("github-release:"):
        return resolve_github_release(spec)

    path = Path(spec).expanduser()
    if path.exists():
        return resolve_path(path)

    raise SystemExit(
        f"Skills source not found: {spec}\n"
        "Use --source /path/to/skills for local testing, or authenticate with gh "
        "for the default private GitHub release source."
    )


def resolve_path(path: Path) -> ResolvedSource:
    path = path.resolve()
    if path.is_dir():
        skills = find_skills_dir(path)
        return ResolvedSource(skills_dir=skills, description=str(path))
    if path.suffix == ".zip":
        return extract_zip(path)
    if path.name.endswith((".tar.gz", ".tgz")):
        return extract_tar(path)
    raise SystemExit(f"Unsupported skills source file: {path}")


def find_skills_dir(root: Path) -> Path:
    if (root / "SKILL.md").exists():
        return root.parent
    if (root / "skills").is_dir():
        return root / "skills"

    nested = [path for path in root.rglob("skills") if path.is_dir() and list(path.rglob("SKILL.md"))]
    if len(nested) == 1:
        return nested[0]

    if list(root.rglob("SKILL.md")):
        return root
    raise SystemExit(f"No SKILL.md files found in source: {root}")


def extract_zip(path: Path) -> ResolvedSource:
    cleanup = Path(tempfile.mkdtemp(prefix="agents-skills-"))
    with zipfile.ZipFile(path) as archive:
        safe_extract_zip(archive, cleanup)
    return ResolvedSource(skills_dir=find_skills_dir(cleanup), cleanup_dirs=(cleanup,), description=str(path))


def extract_tar(path: Path) -> ResolvedSource:
    cleanup = Path(tempfile.mkdtemp(prefix="agents-skills-"))
    with tarfile.open(path, "r:gz") as archive:
        safe_extract_tar(archive, cleanup)
    return ResolvedSource(skills_dir=find_skills_dir(cleanup), cleanup_dirs=(cleanup,), description=str(path))


def safe_extract_zip(archive: zipfile.ZipFile, dest: Path) -> None:
    dest = dest.resolve()
    for member in archive.infolist():
        target = (dest / member.filename).resolve()
        if dest != target and dest not in target.parents:
            raise SystemExit(f"Unsafe path in skills archive: {member.filename}")
        file_type = member.external_attr >> 16
        if file_type & 0o170000 == 0o120000:
            raise SystemExit(f"Unsafe link in skills archive: {member.filename}")
    archive.extractall(dest)


def safe_extract_tar(archive: tarfile.TarFile, dest: Path) -> None:
    dest = dest.resolve()
    for member in archive.getmembers():
        target = (dest / member.name).resolve()
        if dest != target and dest not in target.parents:
            raise SystemExit(f"Unsafe path in skills archive: {member.name}")
        if member.issym() or member.islnk():
            raise SystemExit(f"Unsafe link in skills archive: {member.name}")
    archive.extractall(dest)


def resolve_github_release(spec: str) -> ResolvedSource:
    repo, version = parse_github_release_spec(spec)
    ensure_gh_available()
    ensure_gh_auth()

    cleanup = Path(tempfile.mkdtemp(prefix="agents-skills-release-"))
    args = ["gh", "release", "download"]
    if version != "latest":
        args.append(version)
    args.extend(
        [
            "--repo",
            repo,
            "--pattern",
            "ipf-skills-*.tar.gz",
            "--dir",
            str(cleanup),
            "--clobber",
        ]
    )
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        shutil.rmtree(cleanup, ignore_errors=True)
        raise SystemExit(
            "Could not download private skills release.\n"
            f"Source: {spec}\n"
            "Make sure you have access and run `gh auth login` if needed.\n"
            f"gh output:\n{result.stderr.strip() or result.stdout.strip()}"
        )

    archives = sorted(cleanup.glob("ipf-skills-*.tar.gz"))
    if not archives:
        shutil.rmtree(cleanup, ignore_errors=True)
        raise SystemExit(f"No ipf-skills-*.tar.gz asset found in {repo} release {version}.")

    extracted = extract_tar(archives[0])
    return ResolvedSource(skills_dir=extracted.skills_dir, cleanup_dirs=(cleanup, *extracted.cleanup_dirs), description=spec)


def parse_github_release_spec(spec: str) -> tuple[str, str]:
    raw = spec.removeprefix("github-release:")
    if "@" in raw:
        repo, version = raw.rsplit("@", 1)
    else:
        repo, version = raw, "latest"
    if "/" not in repo:
        raise SystemExit(f"Invalid GitHub release source: {spec}")
    return repo, version or "latest"


def ensure_gh_available() -> None:
    if shutil.which("gh"):
        return
    raise SystemExit("The default private skills source requires the GitHub CLI. Install gh and run `gh auth login`.")


def ensure_gh_auth() -> None:
    result = subprocess.run(["gh", "auth", "status"], text=True, capture_output=True)
    if result.returncode == 0:
        return
    raise SystemExit(
        "GitHub CLI is not authenticated. Run `gh auth login` with an account that can access the private skills repo."
    )
