# Contributing

`agents-setup` is a small public CLI. Keep changes focused, easy to review, and
safe for machines that do not have the private `ipf-skills` repository cloned.

## Branch Flow

- Open feature and fix pull requests into `develop`.
- Keep `develop` deployable, but treat it as the soak/integration branch.
- Merge `develop` into `main` only when a release is ready.
- Publishing happens from `main`, not from feature branches or `develop`.

This keeps normal contribution work away from the public npm release path while
still making releases simple and auditable.

## Local Checks

Run these before opening a PR:

```bash
python -m unittest discover -s tests
node bin/agents-setup.js --help
npm pack --dry-run
```

For behavior that touches private skills, test with an explicit local source:

```bash
TMP_HOME=$(mktemp -d)
HOME="$TMP_HOME" node bin/agents-setup.js install \
  --source /Users/jeremiah/Work/ipf-skills/skills \
  --bundle shared \
  --all
```

Do not add private skill content to this repository or to npm package data.

## Release Checklist

1. Merge feature PRs into `develop`.
2. Let `develop` run for review/testing.
3. Bump `package.json` when releasing a new npm version.
4. Open a PR from `develop` to `main`.
5. Confirm CI passes.
6. Merge to `main`.
7. The `Publish` workflow publishes to npm using the `NPM_TOKEN` repository secret.

The publish workflow skips a version that already exists on npm. If a release
needs a code change, bump the version first; npm versions cannot be overwritten.

## Security Expectations

- Keep this package source-light: installer code, tests, and docs only.
- Do not commit npm tokens, GitHub tokens, private release assets, or private
  skills.
- Archive extraction logic must keep path traversal and unsafe-link tests.
- Any change to GitHub release downloading, archive extraction, file writes, or
  uninstall behavior needs tests.
