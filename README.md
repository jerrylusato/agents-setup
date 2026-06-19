# @jerrylusato/agents-setup

Public no-clone CLI for setting up coding AI-agent project wiring, private IPF skills, and private workflow packages.

This package is intentionally public and source-light. It does **not** bundle private skills or workflows. Private content is fetched from authenticated release assets, or from an explicit local source during development.

## Quick Start

```bash
# Basic agent wiring only. No docs/ scaffold.
npx @jerrylusato/agents-setup init

# Add the documentation workflow and its docs/ scaffold.
npx @jerrylusato/agents-setup init --workflow workflow-contract --yes

# Install private user-level skills after authenticating to GitHub.
npx @jerrylusato/agents-setup install

# Inspect project and global setup.
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

## Project Setup

Basic setup creates only agent wiring:

```text
AGENTS.md
CLAUDE.md -> AGENTS.md
.agents/skills/
.agents/workflows/
.claude/skills -> ../.agents/skills
.junie/skills -> ../.agents/skills
```

It does not create `docs/`. Docs are created by installed workflows, for example `workflow-contract`.

## Private Workflow Source

Default source:

```text
github-release:iPFSoftwares/workflow-contract@latest
```

Workflow setup installs the workflow and its skill entrypoint:

```text
.agents/skills/<workflow-skill>/
.agents/workflows/<workflow-name>/
```

A workflow may also create workflow-owned project files such as `docs/`.

Commands:

```bash
npx @jerrylusato/agents-setup workflow list
npx @jerrylusato/agents-setup workflow install workflow-contract --yes
npx @jerrylusato/agents-setup init --workflow workflow-contract --yes
```

For local development:

```bash
npx @jerrylusato/agents-setup workflow list \
  --workflow-source /Users/jeremiah/Work/workflow-contract
```

## Commands

```bash
npx @jerrylusato/agents-setup init [--root <project>] [--workflow [name]] [--dry-run]
npx @jerrylusato/agents-setup workflow list [--workflow-source <source>]
npx @jerrylusato/agents-setup workflow install [name] [--root <project>] [--yes] [--dry-run]
npx @jerrylusato/agents-setup install [--source <source>] [--bundle <name>] [--all] [--dry-run]
npx @jerrylusato/agents-setup update [--source <source>] [--bundle <name>] [--all] [--dry-run]
npx @jerrylusato/agents-setup uninstall [--source <source>] [--all] [--dry-run]
npx @jerrylusato/agents-setup doctor [--source <source>] [--root <project>]
```

## Security Model

- The public npm package does not include private skill content.
- The public npm package does not include private workflow content.
- Private content is fetched only when a command needs that source.
- GitHub release downloads use the local `gh` CLI, so repository access stays governed by GitHub permissions.
- Archives are extracted with path traversal checks before reading `SKILL.md` files.
- Existing real files and directories are not silently overwritten during project setup.
- Global installs only manage `ipf-*` skill directories and do not remove unrelated personal/vendor skills.
- Workflow installs replace only their managed `.agents/skills/<name>` and `.agents/workflows/<name>` targets.

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

For an end-to-end local workflow test:

```bash
TMP_PROJECT=$(mktemp -d)
node bin/agents-setup.js init \
  --root "$TMP_PROJECT" \
  --workflow workflow-contract \
  --workflow-source /Users/jeremiah/Work/workflow-contract \
  --yes
```

## Branch And Release Model

- `develop` is the integration branch. Open normal feature and fix PRs into `develop`.
- `main` is the release branch. Only merge `develop` into `main` when the package is ready to publish.
- CI runs on PRs and pushes to both `develop` and `main`.
- The npm publish workflow runs only on `main` and skips if the version already exists.
- Package versions are immutable on npm, so bump `package.json` before merging a release PR to `main`.

The repository expects an `NPM_TOKEN` GitHub secret with permission to publish
`@jerrylusato/agents-setup`.

## Relationship to Private Repos

`ipf-skills` remains the private canonical skill library. `workflow-contract` remains the private canonical workflow package. This repo is only the public installer and project scaffold CLI.
