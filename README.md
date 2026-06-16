# @jerrylusato/agents

Public no-clone CLI for setting up AI-agent project wiring and installing private IPF skills.

This package is intentionally public and source-light. It does **not** bundle private skills. Skill installation fetches skills from an authenticated source, or from a local source passed with `--source`.

## Quick Start

```bash
# Set up a project with .agents/skills and compatibility symlinks
npx @jerrylusato/agents init

# Install private skills after authenticating to GitHub
npx @jerrylusato/agents install

# Inspect project and global setup
npx @jerrylusato/agents doctor
```

## Private Skills Source

Default source:

```text
github-release:iPFSoftwares/ipf-skills@latest
```

The default requires:

```bash
gh auth login
```

The authenticated GitHub account must be able to access the private `iPFSoftwares/ipf-skills` repository and its release assets.

For local development, use a local skills checkout:

```bash
npx @jerrylusato/agents install --source /Users/jeremiah/Work/ipf-skills/skills --bundle shared --all
```

Supported source forms:

```text
/path/to/skills
github-release:OWNER/REPO@TAG
github-release:OWNER/REPO@latest
/path/to/ipf-skills-<version>.tar.gz
/path/to/ipf-skills-<version>.zip
```

## Commands

```bash
npx @jerrylusato/agents init [--root <project>] [--dry-run]
npx @jerrylusato/agents install [--source <source>] [--bundle <name>] [--all] [--dry-run]
npx @jerrylusato/agents update [--source <source>] [--bundle <name>] [--all] [--dry-run]
npx @jerrylusato/agents uninstall [--source <source>] [--all] [--dry-run]
npx @jerrylusato/agents doctor [--source <source>] [--root <project>]
```

## Security Model

- The public npm package does not include private skill content.
- Private skills are fetched only when the user runs an install/update/doctor command that needs skill metadata.
- GitHub release downloads use the local `gh` CLI, so repository access stays governed by GitHub permissions.
- Archives are extracted with path traversal checks before reading `SKILL.md` files.
- Existing real files and directories are not silently overwritten during project setup.
- Global installs only manage `ipf-*` skill directories and do not remove unrelated personal/vendor skills.

## Relationship to ipf-skills

`ipf-skills` remains the private canonical skill library and release-packaging source. This repo is only the public installer and project scaffold CLI.
