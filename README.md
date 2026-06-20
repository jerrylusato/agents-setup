# agents-setup

npm package: `@jerrylusato/agents-setup`

Public CLI for setting up AI-agent project wiring, installing private IPF skills, and installing private workflow packages without cloning private repositories.

The npm package does not include private skill or workflow content. Private content is downloaded at runtime from authenticated GitHub release assets, or read from an explicit local source.

## Requirements

- Node.js `>=18`
- GitHub CLI (`gh`) authenticated with an account that can access the private source repositories:

  ```bash
  gh auth login
  ```

## Quick start

```bash
# Scaffold agent wiring only. This does not create docs/.
npx @jerrylusato/agents-setup init

# Scaffold agent wiring and install the default workflow.
npx @jerrylusato/agents-setup init --workflow workflow-contract --yes

# Install private user-level IPF skills.
npx @jerrylusato/agents-setup install

# Inspect project and global setup.
npx @jerrylusato/agents-setup doctor
```

Installed binary names:

```bash
agents-setup
coding-ai-agents-setup
ipf-agents-setup
```

## What `init` creates

Basic setup creates only shared agent wiring:

```text
AGENTS.md
CLAUDE.md -> AGENTS.md
.agents/skills/
.agents/workflows/
.claude/skills -> ../.agents/skills
.junie/skills -> ../.agents/skills
```

It does not create `docs/`. Workflow-owned files, including `docs/`, are created only when a workflow is installed.

## Default private sources

Skills:

```text
github-release:iPFSoftwares/ipf-skills@latest
```

Workflows:

```text
github-release:iPFSoftwares/workflow-contract@latest
```

The authenticated `gh` account must have access to those repositories and their release assets.

## Commands

```bash
npx @jerrylusato/agents-setup init [--root <project>] [--dry-run] [--workflow [name]] [--workflow-source <source>] [--yes] [--no-workflow-init]

npx @jerrylusato/agents-setup workflow list [--workflow-source <source>]
npx @jerrylusato/agents-setup workflow install [name] [--root <project>] [--dry-run] [--workflow-source <source>] [--yes] [--no-workflow-init]

npx @jerrylusato/agents-setup install [--source <source>] [--dest <dir>] [--prefix <prefix>] [--bundle <name>] [--all] [--dry-run] [--no-replace] [--no-claude-link]
npx @jerrylusato/agents-setup update [--source <source>] [--dest <dir>] [--prefix <prefix>] [--bundle <name>] [--all] [--dry-run] [--no-claude-link]
npx @jerrylusato/agents-setup uninstall [--source <source>] [--dest <dir>] [--prefix <prefix>] [--all] [--dry-run]

npx @jerrylusato/agents-setup doctor [--root <project>] [--source <source>] [--dest <dir>] [--prefix <prefix>]
```

Use `--help` on any command for the exact option list.

## Source formats

Skills source formats:

```text
/path/to/skills
/path/to/ipf-skills-<version>.tar.gz
/path/to/ipf-skills-<version>.zip
github-release:OWNER/REPO@TAG
github-release:OWNER/REPO@latest
```

Workflow source formats:

```text
/path/to/workflow-repo
/path/to/ipf-workflows-<version>.tar.gz
/path/to/ipf-workflows-<version>.zip
github-release:OWNER/REPO@TAG
github-release:OWNER/REPO@latest
```

Local examples:

```bash
npx @jerrylusato/agents-setup install \
  --source /Users/jeremiah/Work/ipf-skills/skills \
  --bundle shared \
  --all

npx @jerrylusato/agents-setup init \
  --workflow workflow-contract \
  --workflow-source /Users/jeremiah/Work/workflow-contract \
  --yes
```

## Safety rules

- Existing real files and directories are left untouched during project setup.
- Workflow installs replace only their managed `.agents/skills/<workflow-skill>` and `.agents/workflows/<workflow-name>` targets.
- Skill installs manage only the selected destination and `ipf-*` skill names by default.
- Archive extraction rejects path traversal and link entries.
- GitHub release downloads use the local `gh` authentication state.

## Development

```bash
python -m unittest discover -s tests
node bin/agents-setup.js --help
npm pack --dry-run
```

## Release

This repository uses GitHub Flow.

- `main` is the only long-lived branch.
- CI runs on pull requests and pushes to `main`.
- Publishing runs on pushes to `main`.
- The publish workflow skips when the current `package.json` version already exists on npm.
- Bump `package.json` before merging a release PR.

Required GitHub secret:

```text
NPM_TOKEN
```

`NPM_TOKEN` must be able to publish `@jerrylusato/agents-setup`.

## Related private repositories

- `iPFSoftwares/ipf-skills`: canonical private skill source.
- `iPFSoftwares/workflow-contract`: canonical private workflow source.
