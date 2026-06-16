from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workflow:
    name: str
    title: str
    description: str
    version: str
    skill_name: str
    workflow_dir: Path
    skill_dir: Path

    def workflow_target(self, root: Path) -> Path:
        return root / ".agents" / "workflows" / self.name

    def skill_target(self, root: Path) -> Path:
        return root / ".agents" / "skills" / self.skill_name


def load_workflows(source_root: Path) -> list[Workflow]:
    source_root = source_root.resolve()
    if (source_root / "workflows.json").is_file():
        return load_manifest_workflows(source_root)
    if (source_root / "workflow.json").is_file():
        return [load_single_repo_workflow(source_root)]
    raise SystemExit(f"No workflow manifest found in source: {source_root}")


def load_manifest_workflows(source_root: Path) -> list[Workflow]:
    manifest = json.loads((source_root / "workflows.json").read_text(encoding="utf-8"))
    workflows: list[Workflow] = []
    for item in manifest.get("workflows", []):
        name = item["name"]
        skill_name = item.get("skill", name)
        workflow_dir = source_root / item.get("workflow_path", f"workflows/{name}")
        skill_dir = source_root / item.get("skill_path", f"skills/{skill_name}")
        workflows.append(
            Workflow(
                name=name,
                title=item.get("title", name),
                description=item.get("description", ""),
                version=item.get("version", ""),
                skill_name=skill_name,
                workflow_dir=workflow_dir,
                skill_dir=skill_dir,
            )
        )
    return validate_workflows(workflows)


def load_single_repo_workflow(source_root: Path) -> Workflow:
    metadata = json.loads((source_root / "workflow.json").read_text(encoding="utf-8"))
    name = metadata["name"]
    skill_name = metadata.get("skill", name)
    return validate_workflows(
        [
            Workflow(
                name=name,
                title=metadata.get("title", name),
                description=metadata.get("description", ""),
                version=metadata.get("version", ""),
                skill_name=skill_name,
                workflow_dir=source_root,
                skill_dir=source_root / ".agents" / "skills" / skill_name,
            )
        ]
    )[0]


def validate_workflows(workflows: list[Workflow]) -> list[Workflow]:
    if not workflows:
        raise SystemExit("Workflow source has no workflows.")
    seen: set[str] = set()
    for workflow in workflows:
        if workflow.name in seen:
            raise SystemExit(f"Duplicate workflow name in source: {workflow.name}")
        seen.add(workflow.name)
        if not workflow.workflow_dir.is_dir():
            raise SystemExit(f"Missing workflow directory for {workflow.name}: {workflow.workflow_dir}")
        if not (workflow.workflow_dir / "workflow.json").is_file():
            raise SystemExit(f"Missing workflow.json for {workflow.name}: {workflow.workflow_dir}")
        if not workflow.skill_dir.is_dir():
            raise SystemExit(f"Missing workflow skill for {workflow.name}: {workflow.skill_dir}")
        if not (workflow.skill_dir / "SKILL.md").is_file():
            raise SystemExit(f"Missing SKILL.md for workflow {workflow.name}: {workflow.skill_dir}")
    return sorted(workflows, key=lambda workflow: workflow.name)


def describe_workflow(workflow: Workflow) -> str:
    version = f" v{workflow.version}" if workflow.version else ""
    return f"{workflow.name}{version} - {workflow.title}"


def select_workflow(workflows: list[Workflow], requested: str | None) -> Workflow:
    if requested and requested != "select":
        for workflow in workflows:
            if workflow.name == requested:
                return workflow
        names = ", ".join(workflow.name for workflow in workflows)
        raise SystemExit(f"Unknown workflow: {requested}. Available workflows: {names}")

    if len(workflows) == 1:
        return workflows[0]

    print("\nAvailable workflows")
    for index, workflow in enumerate(workflows, start=1):
        print(f"  {index}. {describe_workflow(workflow)}")
        if workflow.description:
            print(f"     {workflow.description}")

    while True:
        try:
            answer = input("\nChoose workflow number: ").strip()
        except EOFError as exc:
            raise SystemExit("No interactive input available. Pass the workflow name explicitly.") from exc
        if not answer:
            raise SystemExit("No workflow selected.")
        if answer.isdigit() and 1 <= int(answer) <= len(workflows):
            return workflows[int(answer) - 1]
        print(f"Pick a number from 1 to {len(workflows)}.")


def copy_managed_tree(source: Path, target: Path, dry_run: bool, label: str) -> str:
    if dry_run:
        action = "replace" if target.exists() or target.is_symlink() else "create"
        return f"would {action} {label}: {target}"
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=ignore_private_source)
    return f"installed {label}: {target}"


def ignore_private_source(_: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in {".git", ".agents", "__pycache__", "dist", ".DS_Store"} or name.endswith(".pyc")
    }


def install_workflow(
    workflow: Workflow,
    root: Path,
    dry_run: bool = False,
    run_init: bool = True,
) -> list[str]:
    root = root.expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    messages = [
        copy_managed_tree(workflow.skill_dir, workflow.skill_target(root), dry_run, f"skill {workflow.skill_name}"),
        copy_managed_tree(workflow.workflow_dir, workflow.workflow_target(root), dry_run, f"workflow {workflow.name}"),
    ]
    init_script = workflow.workflow_target(root) / "scripts" / "init_workflow_contract.py"
    if run_init and init_script.is_file():
        if dry_run:
            messages.append(f"would run workflow init: {init_script}")
        else:
            result = subprocess.run(
                [sys.executable, str(init_script)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
            if output:
                messages.append(output)
            if result.returncode != 0:
                raise SystemExit(f"Workflow init failed for {workflow.name}.")
    elif run_init:
        messages.append(f"no workflow init script found for {workflow.name}; copied files only")
    return messages
