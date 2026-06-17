# Contributing

`agents-setup` is a small public CLI. Keep changes focused, easy to review, and
safe for machines that do not have the private `ipf-skills` or
`workflow-contract` repositories cloned.

## Branch and Release Flow

This repository follows GitHub Flow:

- `main` is the only long-lived branch and should always be releasable.
- Create short-lived feature and fix branches from `main`.
- Open pull requests into `main`; do not use `develop` for normal work.
- CI runs on pull requests and pushes to `main`.
- Publishing happens from `main` after merge and only when `package.json` has a
  version that does not already exist on npm.

Keep changes focused and include tests for behavior that touches downloads,
archive extraction, file writes, workflow setup, or uninstall logic.

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

For behavior that touches private workflows, test with an explicit local source:

```bash
TMP_PROJECT=$(mktemp -d)
node bin/agents-setup.js init \
  --root "$TMP_PROJECT" \
  --workflow documentation-framework \
  --workflow-source /Users/jeremiah/Work/workflow-contract \
  --yes
```

Do not add private skill or workflow content to this repository or to npm package data.

## Release Checklist

1. Bump `package.json` in the feature PR when releasing a new npm version.
2. Confirm unit tests, launcher smoke tests, and `npm pack --dry-run` pass.
3. Merge the PR into `main`.
4. The `Publish` workflow publishes to npm using the `NPM_TOKEN` repository secret.

The publish workflow skips a version that already exists on npm. If a release
needs a code change, bump the version first; npm versions cannot be overwritten.

## Security Expectations

- Keep this package source-light: installer code, tests, and docs only.
- Do not commit npm tokens, GitHub tokens, private release assets, or private
  skills/workflows.
- Archive extraction logic must keep path traversal and unsafe-link tests.
- Any change to GitHub release downloading, archive extraction, file writes, or
  uninstall behavior needs tests.
