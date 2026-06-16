from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .source import (
    ensure_gh_auth,
    ensure_gh_available,
    parse_github_release_spec,
    safe_extract_tar,
    safe_extract_zip,
)


DEFAULT_WORKFLOWS_SOURCE = "github-release:iPFSoftwares/workflow-contract@latest"
ENV_WORKFLOWS_SOURCE = "IPF_AGENTS_WORKFLOWS_SOURCE"


@dataclass(frozen=True)
class ResolvedWorkflowSource:
    root_dir: Path
    cleanup_dirs: tuple[Path, ...] = ()
    description: str = ""


def default_workflow_source_spec() -> str:
    return os.environ.get(ENV_WORKFLOWS_SOURCE, DEFAULT_WORKFLOWS_SOURCE)


def resolve_workflow_source(spec: str) -> ResolvedWorkflowSource:
    if spec.startswith("github-release:"):
        return resolve_github_release(spec)

    path = Path(spec).expanduser()
    if path.exists():
        return resolve_path(path)

    raise SystemExit(
        f"Workflow source not found: {spec}\n"
        "Use --workflow-source /path/to/workflow-contract for local testing, "
        "or authenticate with gh for the default private GitHub release source."
    )


def resolve_path(path: Path) -> ResolvedWorkflowSource:
    path = path.resolve()
    if path.is_dir():
        return ResolvedWorkflowSource(root_dir=find_workflows_root(path), description=str(path))
    if path.suffix == ".zip":
        return extract_zip(path)
    if path.name.endswith((".tar.gz", ".tgz")):
        return extract_tar(path)
    raise SystemExit(f"Unsupported workflow source file: {path}")


def find_workflows_root(root: Path) -> Path:
    if (root / "workflows.json").is_file() or (root / "workflow.json").is_file():
        return root

    manifests = [path.parent for path in root.rglob("workflows.json")]
    manifests.extend(path.parent for path in root.rglob("workflow.json"))
    unique = sorted(set(manifests))
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        raise SystemExit(f"Multiple workflow manifests found in source: {root}")
    raise SystemExit(f"No workflow manifest found in source: {root}")


def extract_zip(path: Path) -> ResolvedWorkflowSource:
    cleanup = Path(tempfile.mkdtemp(prefix="agents-workflows-"))
    with zipfile.ZipFile(path) as archive:
        safe_extract_zip(archive, cleanup)
    return ResolvedWorkflowSource(root_dir=find_workflows_root(cleanup), cleanup_dirs=(cleanup,), description=str(path))


def extract_tar(path: Path) -> ResolvedWorkflowSource:
    cleanup = Path(tempfile.mkdtemp(prefix="agents-workflows-"))
    with tarfile.open(path, "r:gz") as archive:
        safe_extract_tar(archive, cleanup)
    return ResolvedWorkflowSource(root_dir=find_workflows_root(cleanup), cleanup_dirs=(cleanup,), description=str(path))


def resolve_github_release(spec: str) -> ResolvedWorkflowSource:
    repo, version = parse_github_release_spec(spec)
    ensure_gh_available()
    ensure_gh_auth()

    cleanup = Path(tempfile.mkdtemp(prefix="agents-workflows-release-"))
    args = ["gh", "release", "download"]
    if version != "latest":
        args.append(version)
    args.extend(
        [
            "--repo",
            repo,
            "--pattern",
            "ipf-workflows-*.tar.gz",
            "--dir",
            str(cleanup),
            "--clobber",
        ]
    )
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        shutil.rmtree(cleanup, ignore_errors=True)
        raise SystemExit(
            "Could not download private workflow release.\n"
            f"Source: {spec}\n"
            "Make sure you have access and run `gh auth login` if needed.\n"
            f"gh output:\n{result.stderr.strip() or result.stdout.strip()}"
        )

    archives = sorted(cleanup.glob("ipf-workflows-*.tar.gz"))
    if not archives:
        shutil.rmtree(cleanup, ignore_errors=True)
        raise SystemExit(f"No ipf-workflows-*.tar.gz asset found in {repo} release {version}.")

    extracted = extract_tar(archives[0])
    return ResolvedWorkflowSource(
        root_dir=extracted.root_dir,
        cleanup_dirs=(cleanup, *extracted.cleanup_dirs),
        description=spec,
    )
