# Private Sources

The CLI keeps private skills and workflows out of the public npm package. It resolves private content at runtime from authenticated GitHub release assets or explicit local sources.

Basic `agents-setup init` is agent wiring only and does not create `docs/`. Workflow-owned docs are created only when a workflow is installed.

## Skills Release Flow

Skill releases are cut from `ipf-skills` `main` after PR merge.

1. In the private `ipf-skills` repo, build a release bundle:

   ```bash
   python tooling/package_skills_release.py --version <version>
   ```

2. Attach the generated `ipf-skills-<version>.tar.gz` asset to a private GitHub Release.
3. Publish or update `@jerrylusato/agents-setup` only when installer behavior changes.
4. Developers run:

   ```bash
   gh auth login
   npx @jerrylusato/agents-setup install
   ```

## Workflow Release Flow

Workflow releases are cut from `workflow-contract` `main` after PR merge.

1. In the private `workflow-contract` repo, build a workflow bundle:

   ```bash
   python scripts/package_workflow_release.py --version <version>
   ```

2. Attach `ipf-workflows-v<version>.tar.gz` to a private GitHub Release.
3. Developers run:

   ```bash
   gh auth login
   npx @jerrylusato/agents-setup init --workflow workflow-contract --yes
   ```

## Local Testing

Use `--source` to avoid touching GitHub during local CLI development:

```bash
npx @jerrylusato/agents-setup install --source /Users/jeremiah/Work/ipf-skills/skills --bundle shared --all
```

```bash
npx @jerrylusato/agents-setup workflow list --workflow-source /Users/jeremiah/Work/workflow-contract
```
