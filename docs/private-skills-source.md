# Private Skills Source

The CLI keeps private skills out of the public npm package. It installs skills by resolving a source at runtime.

## Recommended Release Flow

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

## Local Testing

Use `--source` to avoid touching GitHub during local CLI development:

```bash
npx @jerrylusato/agents-setup install --source /Users/jeremiah/Work/ipf-skills/skills --bundle shared --all
```
