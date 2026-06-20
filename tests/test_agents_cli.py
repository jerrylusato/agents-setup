from __future__ import annotations

import json
import tempfile
import tarfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from agents_setup_cli.source import parse_github_release_spec, resolve_source, safe_extract_tar, safe_extract_zip
from agents_setup_cli.skills import Skill, bundle_skills, installed_name
from agents_setup_cli.cli import confirm_selection
from agents_setup_cli.workflows import install_workflow, load_workflows


class PackageMetadataTests(unittest.TestCase):
    def test_exposes_only_agents_setup_binary(self) -> None:
        package_path = Path(__file__).resolve().parents[1] / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))

        self.assertEqual(package["bin"], {"agents-setup": "bin/agents-setup.js"})


class SourceTests(unittest.TestCase):
    def test_parse_github_release_spec(self) -> None:
        self.assertEqual(
            parse_github_release_spec("github-release:iPFSoftwares/ipf-skills@latest"),
            ("iPFSoftwares/ipf-skills", "latest"),
        )

    def test_resolve_local_skills_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills" / "shared" / "demo"
            skills.mkdir(parents=True)
            (skills / "SKILL.md").write_text("---\nname: demo\ndescription: Demo\n---\n", encoding="utf-8")
            resolved = resolve_source(str(Path(tmp) / "skills"))
            self.assertEqual(resolved.skills_dir, (Path(tmp) / "skills").resolve())

    def test_resolve_nested_release_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "ipf-skills-v1" / "skills" / "shared" / "demo"
            skills.mkdir(parents=True)
            (skills / "SKILL.md").write_text("---\nname: demo\ndescription: Demo\n---\n", encoding="utf-8")
            resolved = resolve_source(tmp)
            self.assertEqual(resolved.skills_dir, (Path(tmp) / "ipf-skills-v1" / "skills").resolve())

    def test_rejects_unsafe_tar_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "bad.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                payload = b"bad"
                info = tarfile.TarInfo("../evil")
                info.size = len(payload)
                archive.addfile(info, BytesIO(payload))

            with tarfile.open(archive_path, "r:gz") as archive:
                with self.assertRaises(SystemExit):
                    safe_extract_tar(archive, Path(tmp) / "out")

    def test_rejects_unsafe_zip_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../evil", "bad")

            with zipfile.ZipFile(archive_path) as archive:
                with self.assertRaises(SystemExit):
                    safe_extract_zip(archive, Path(tmp) / "out")


class SkillTests(unittest.TestCase):
    def test_installed_name_adds_prefix_once(self) -> None:
        self.assertEqual(installed_name(Path("demo"), "ipf"), "ipf-demo")
        self.assertEqual(installed_name(Path("ipf-demo"), "ipf"), "ipf-demo")

    def test_bundle_filters_shared_and_frontend(self) -> None:
        skills = [
            Skill(Path("a"), "ipf-shared", "shared", "shared", ""),
            Skill(Path("b"), "ipf-front", "frontend", "front", ""),
            Skill(Path("c"), "ipf-back", "backend", "back", ""),
        ]
        self.assertEqual([s.destination_name for s in bundle_skills(skills, "frontend")], ["ipf-shared", "ipf-front"])


class CliTests(unittest.TestCase):
    def test_assume_yes_skips_prompt(self) -> None:
        skill = Skill(Path("source"), "ipf-test", "shared", "test", "")
        self.assertTrue(confirm_selection("install", [skill], dry_run=False, assume_yes=True))


class WorkflowTests(unittest.TestCase):
    def test_load_single_repo_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "workflow.json").write_text(
                '{"name":"workflow-contract","title":"Docs","skill":"workflow-contract"}\n',
                encoding="utf-8",
            )
            skill = root / ".agents" / "skills" / "workflow-contract"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: workflow-contract\n---\n", encoding="utf-8")

            workflows = load_workflows(root)

            self.assertEqual(len(workflows), 1)
            self.assertEqual(workflows[0].name, "workflow-contract")
            self.assertEqual(workflows[0].skill_name, "workflow-contract")

    def test_install_workflow_copies_skill_and_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "workflow.json").write_text(
                '{"name":"workflow-contract","title":"Docs","skill":"workflow-contract"}\n',
                encoding="utf-8",
            )
            skill = source / ".agents" / "skills" / "workflow-contract"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: workflow-contract\n---\n", encoding="utf-8")
            (source / "scripts").mkdir()
            project = Path(tmp) / "project"
            project.mkdir()

            workflow = load_workflows(source)[0]
            messages = install_workflow(workflow, project, dry_run=False, run_init=False)

            self.assertTrue((project / ".agents" / "skills" / "workflow-contract" / "SKILL.md").is_file())
            self.assertTrue((project / ".agents" / "workflows" / "workflow-contract" / "workflow.json").is_file())
            self.assertTrue(any("installed skill" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
