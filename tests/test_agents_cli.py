from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents_cli.source import parse_github_release_spec, resolve_source
from agents_cli.skills import Skill, bundle_skills, installed_name
from agents_cli.cli import confirm_selection


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


if __name__ == "__main__":
    unittest.main()
