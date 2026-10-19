from __future__ import annotations

import json
import tempfile
import tarfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from agents_setup_cli.source import (
    DEFAULT_SKILLS_SOURCE,
    parse_github_release_spec,
    resolve_source,
    safe_extract_tar,
    safe_extract_zip,
)
from agents_setup_cli.skills import Skill, build_skills, bundle_skills, install_skill, installed_name, uninstall_skill
from agents_setup_cli.cli import confirm_selection, main
from agents_setup_cli.workflows import install_workflow, load_workflows


class PackageMetadataTests(unittest.TestCase):
    def test_exposes_only_agents_setup_binary(self) -> None:
        package_path = Path(__file__).resolve().parents[1] / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))

        self.assertEqual(package["bin"], {"agents-setup": "bin/agents-setup.js"})


class SourceTests(unittest.TestCase):
    def test_default_skills_source_uses_renamed_repository(self) -> None:
        self.assertEqual(DEFAULT_SKILLS_SOURCE, "github-release:iPFSoftwares/skills@latest")

    def test_parse_github_release_spec(self) -> None:
        self.assertEqual(
            parse_github_release_spec("github-release:iPFSoftwares/skills@latest"),
            ("iPFSoftwares/skills", "latest"),
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

    def test_installed_name_honors_exact_frontmatter_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "commit"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: commit\ninstall_name: commit\ndescription: Commit safely\n---\n",
                encoding="utf-8",
            )

            self.assertEqual(installed_name(skill, "ipf"), "commit")

    def test_invalid_exact_name_is_rejected_before_building_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "commit"
            skill.mkdir()
            skill_file = skill / "SKILL.md"
            for value in ("../personal", "commit/other", "bad_name", ""):
                skill_file.write_text(f"---\nname: commit\ninstall_name: {value}\n---\n", encoding="utf-8")
                with self.subTest(value=value), self.assertRaisesRegex(SystemExit, "Invalid install_name"):
                    installed_name(skill, "ipf")

    def test_build_skills_marks_exact_install_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "skills"
            skill = source / "shared" / "commit"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: commit\ninstall_name: commit\ndescription: Commit safely\n---\n",
                encoding="utf-8",
            )

            built = build_skills([skill], source, "ipf")

            self.assertEqual(built[0].destination_name, "commit")
            self.assertTrue(built[0].exact_install_name)

    def test_install_refuses_to_replace_unmanaged_exact_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source" / "commit"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: commit\ninstall_name: commit\ndescription: Canonical\n---\n",
                encoding="utf-8",
            )
            dest = root / "dest"
            existing = dest / "commit"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text(
                "---\nname: commit\ndescription: Personal\n---\n",
                encoding="utf-8",
            )
            skill = Skill(source, "commit", "shared", "commit", "Canonical", True)

            with self.assertRaisesRegex(SystemExit, "Refusing to replace unmanaged canonical skill"):
                install_skill(skill, dest, replace=True, dry_run=False)

            self.assertIn("unmanaged", uninstall_skill(skill, dest, dry_run=False).message)
            self.assertTrue((existing / "SKILL.md").exists())

    def test_canonical_install_marks_ownership_for_replace_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source" / "commit"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: commit\ninstall_name: commit\ndescription: Canonical\n---\n",
                encoding="utf-8",
            )
            dest = root / "dest"
            dest.mkdir()
            skill = Skill(source, "commit", "shared", "commit", "Canonical", True)

            self.assertTrue(install_skill(skill, dest, replace=True, dry_run=False).changed)
            marker = json.loads((dest / "commit" / ".ipf-skill-owner.json").read_text(encoding="utf-8"))
            self.assertEqual(marker, {"owner": "iPFSoftwares/skills", "name": "commit"})
            self.assertTrue(install_skill(skill, dest, replace=True, dry_run=False).changed)
            self.assertTrue(uninstall_skill(skill, dest, dry_run=False).changed)
            self.assertFalse((dest / "commit").exists())

    def test_canonical_uninstall_leaves_mismatched_marker_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "dest"
            target = dest / "commit"
            target.mkdir(parents=True)
            (target / ".ipf-skill-owner.json").write_text(
                '{"owner":"iPFSoftwares/skills","name":"other"}\n', encoding="utf-8"
            )
            skill = Skill(root / "source", "commit", "shared", "commit", "Canonical", True)

            self.assertFalse(uninstall_skill(skill, dest, dry_run=False).changed)
            target.rename(dest / "personal")
            target.symlink_to(dest / "personal", target_is_directory=True)
            self.assertFalse(uninstall_skill(skill, dest, dry_run=False).changed)
            self.assertTrue(target.is_symlink())

    def test_bundle_filters_shared_and_frontend(self) -> None:
        skills = [
            Skill(Path("a"), "ipf-shared", "shared", "shared", ""),
            Skill(Path("b"), "ipf-front", "frontend", "front", ""),
            Skill(Path("c"), "ipf-back", "backend", "back", ""),
        ]
        self.assertEqual([s.destination_name for s in bundle_skills(skills, "frontend")], ["ipf-shared", "ipf-front"])

    def test_bundle_filters_shared_and_devops(self) -> None:
        skills = [
            Skill(Path("a"), "ipf-shared", "shared", "shared", ""),
            Skill(Path("b"), "ipf-devops", "devops", "devops", ""),
            Skill(Path("c"), "ipf-back", "backend", "back", ""),
        ]
        self.assertEqual([s.destination_name for s in bundle_skills(skills, "devops")], ["ipf-shared", "ipf-devops"])


class CliTests(unittest.TestCase):
    def test_assume_yes_skips_prompt(self) -> None:
        skill = Skill(Path("source"), "ipf-test", "shared", "test", "")
        self.assertTrue(confirm_selection("install", [skill], dry_run=False, assume_yes=True))

    def test_canonical_cli_state_tracks_only_owned_install_and_removal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "skills" / "shared" / "commit"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: commit\ninstall_name: commit\ndescription: Canonical\n---\n",
                encoding="utf-8",
            )
            dest = root / "dest"
            dest.mkdir()
            state = root / "state.json"
            base_args = ["--source", str(root / "skills"), "--dest", str(dest), "--all"]

            with patch("agents_setup_cli.cli.default_state_file", return_value=state):
                self.assertEqual(main(["install", *base_args, "--no-claude-link"]), 0)
                self.assertEqual([item["name"] for item in json.loads(state.read_text())["installed_skills"]], ["commit"])

                marker = dest / "commit" / ".ipf-skill-owner.json"
                marker.unlink()
                self.assertEqual(main(["uninstall", *base_args]), 0)
                self.assertTrue((dest / "commit").exists())
                self.assertEqual([item["name"] for item in json.loads(state.read_text())["installed_skills"]], ["commit"])

                marker.write_text('{"owner":"iPFSoftwares/skills","name":"commit"}\n', encoding="utf-8")
                self.assertEqual(main(["uninstall", *base_args]), 0)
                self.assertFalse((dest / "commit").exists())
                self.assertEqual(json.loads(state.read_text())["installed_skills"], [])


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
