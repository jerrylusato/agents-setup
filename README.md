# @jerrylusato/agents-setup

Public no-clone CLI for setting up coding AI-agent project wiring and installing private IPF skills.

This package is intentionally public and source-light. It does **not** bundle private skills. Skill installation fetches skills from an authenticated source, or from a local source passed with `--source`.

## Quick Start

```bash
# Set up a project with .agents/skills and compatibility symlinks
npx @jerrylusato/agents-setup init

# Install private skills after authenticating to GitHub
npx @jerrylusato/agents-setup install

# Inspect project and global setup
npx @jerrylusato/agents-setup doctor
```

The installed binary is also named `agents-setup`:

```bash
agents-setup --help
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
npx @jerrylusato/agents-setup install --source /Users/jeremiah/Work/ipf-skills/skills --bundle shared --all
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
npx @jerrylusato/agents-setup init [--root <project>] [--dry-run]
npx @jerrylusato/agents-setup install [--source <source>] [--bundle <name>] [--all] [--dry-run]
npx @jerrylusato/agents-setup update [--source <source>] [--bundle <name>] [--all] [--dry-run]
npx @jerrylusato/agents-setup uninstall [--source <source>] [--all] [--dry-run]
npx @jerrylusato/agents-setup doctor [--source <source>] [--root <project>]
```

## Security Model

- The public npm package does not include private skill content.
- Private skills are fetched only when the user runs an install/update/doctor command that needs skill metadata.
- GitHub release downloads use the local `gh` CLI, so repository access stays governed by GitHub permissions.
- Archives are extracted with path traversal checks before reading `SKILL.md` files.
- Existing real files and directories are not silently overwritten during project setup.
- Global installs only manage `ipf-*` skill directories and do not remove unrelated personal/vendor skills.

## Development

```bash
python -m unittest discover -s tests
node bin/agents-setup.js --help
npm pack --dry-run
```

For an end-to-end local install test against a private `ipf-skills` checkout:

```bash
TMP_HOME=$(mktemp -d)
HOME="$TMP_HOME" node bin/agents-setup.js install \
  --source /Users/jeremiah/Work/ipf-skills/skills \
  --bundle shared \
  --all
```

## Branch And Release Model

- `develop` is the integration branch. Open normal feature and fix PRs into `develop`.
- `main` is the release branch. Only merge `develop` into `main` when the package is ready to publish.
- CI runs on PRs and pushes to both `develop` and `main`.
- The npm publish workflow runs only on `main` and skips if the version already exists.
- Package versions are immutable on npm, so bump `package.json` before merging a release PR to `main`.

The repository expects an `NPM_TOKEN` GitHub secret with permission to publish
`@jerrylusato/agents-setup`.

## Relationship to ipf-skills

`ipf-skills` remains the private canonical skill library and release-packaging source. This repo is only the public installer and project scaffold CLI.
