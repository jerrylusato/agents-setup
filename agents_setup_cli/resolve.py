"""Resolve checksum-pinned skill packages without changing user installation state."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from .source import ensure_gh_auth, ensure_gh_available, safe_extract_tar

ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*")
REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+")
VERSION = re.compile(r"v?[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.-]+)?")
SHA256 = re.compile(r"[0-9a-f]{64}")


def read_json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(data, dict):
        raise ValueError("Manifest must be an object")
    return data


def validate_request(request: dict) -> None:
    if set(request) != {"schema_version", "source", "skills"} or request["schema_version"] != 1:
        raise ValueError("Expected resolve manifest schema_version 1 with source and skills")
    source = request["source"]
    if not isinstance(source, dict) or set(source) != {"repository", "version", "archive_sha256"}:
        raise ValueError("Source requires repository, version, and archive_sha256")
    for key, pattern in (("repository", REPOSITORY), ("version", VERSION), ("archive_sha256", SHA256)):
        if not isinstance(source[key], str) or not pattern.fullmatch(source[key]):
            raise ValueError(f"Invalid pinned source {key}")
    selected = request["skills"]
    if (not isinstance(selected, list) or not selected
            or not all(isinstance(value, str) and ID.fullmatch(value) for value in selected)
            or len(selected) != len(set(selected))):
        raise ValueError("Skills must be a nonempty, unique list of canonical department/group/name IDs")


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def tree_hash(directory: Path) -> str:
    result = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Skill links are forbidden")
        if path.is_file():
            result.update(path.relative_to(directory).as_posix().encode() + b"\0")
            result.update(path.read_bytes())
    return result.hexdigest()


def download(source: dict, directory: Path) -> Path:
    ensure_gh_available()
    ensure_gh_auth()
    filename = f"ipf-skills-{source['version']}.tar.gz"
    result = subprocess.run(
        ["gh", "release", "download", source["version"], "--repo", source["repository"],
         "--pattern", filename, "--dir", str(directory)],
        capture_output=True, timeout=180,
    )
    if result.returncode:
        raise RuntimeError(f"Skill release download failed (gh exit {result.returncode})")
    return directory / filename


def extract(archive: Path, destination: Path) -> Path:
    if archive.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Compressed skill archive exceeds 64 MiB")
    destination.mkdir()
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if (len(members) > 20_000 or sum(item.size for item in members) > 256 * 1024 * 1024
                or any(not (item.isfile() or item.isdir()) for item in members)):
            raise ValueError("Skill archive exceeds bounds or contains special files")
        names = [item.name for item in members]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate skill archive member")
        safe_extract_tar(bundle, destination)
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1 or not (roots[0] / "catalog.json").is_file():
        raise ValueError("Expected one release root with catalog.json")
    return roots[0]


def select_catalog(root: Path, selected: list[str]) -> list[dict]:
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        raise ValueError("Release catalog must be a list")
    available = {}
    for entry in catalog:
        if not isinstance(entry, dict):
            raise ValueError("Invalid catalog entry")
        identifier = "/".join(str(entry.get(field, "")) for field in ("department", "group", "name"))
        if not ID.fullmatch(identifier) or entry.get("path") != f"skills/{identifier}/SKILL.md":
            raise ValueError("Catalog metadata does not match canonical path")
        if identifier in available:
            raise ValueError("Duplicate catalog ID")
        available[identifier] = entry
    result = []
    for identifier in selected:
        if identifier not in available:
            raise ValueError(f"Missing selected skill: {identifier}")
        entry = available[identifier]
        directory = root / "skills" / identifier
        text = (directory / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---", 2)
        if len(front) != 3 or front[0]:
            raise ValueError("Missing selected skill frontmatter")
        for field in ("name", "department", "group"):
            match = re.search(rf"^{field}: ([^\n]+)$", front[1], re.MULTILINE)
            if not match or match[1].strip().strip("\"'") != entry[field]:
                raise ValueError("Selected skill metadata differs from release catalog")
        dependencies = entry.get("dependencies", [])
        if (not isinstance(dependencies, list)
                or not all(isinstance(value, str) and value in selected for value in dependencies)):
            raise ValueError(f"Unselected skill dependency: {identifier}")
        repositories = entry.get("repositories", [])
        if not isinstance(repositories, list) or not all(isinstance(value, str) and REPOSITORY.fullmatch(value) for value in repositories):
            raise ValueError("Invalid skill repository scope")
        result.append({"id": identifier, "name": entry["name"], "department": entry["department"],
                       "group": entry["group"], "dependencies": dependencies, "repositories": repositories,
                       "sha256": tree_hash(directory)})
    return result


def resolve(manifest: Path, destination: Path, archive: Path | None = None) -> dict:
    request = read_json(manifest)
    validate_request(request)
    destination = destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("Resolve destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".resolve-", dir=destination.parent) as temporary:
        temporary = Path(temporary)
        archive = archive.resolve() if archive is not None else download(request["source"], temporary)
        if file_hash(archive) != request["source"]["archive_sha256"]:
            raise ValueError("Skill release checksum mismatch")
        root = extract(archive, temporary / "extracted")
        if root.name != f"ipf-skills-{request['source']['version']}":
            raise ValueError("Archive root does not match pinned release version")
        entries = select_catalog(root, request["skills"])
        output = temporary / "output"
        output.mkdir()
        for entry in entries:
            target = output / "skills" / entry["id"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(root / "skills" / entry["id"], target)
        result = {"schema_version": 1, "source": request["source"], "skills": entries}
        (output / "resolved.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(output, destination)
    return result


def resolve_command(args) -> int:
    result = resolve(args.manifest, args.dest, args.archive)
    print(f"Resolved {len(result['skills'])} skills into {args.dest}")
    return 0
