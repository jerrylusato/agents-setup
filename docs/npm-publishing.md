# npm Publishing

The `Publish` GitHub Actions workflow publishes `@jerrylusato/agents-setup`
from `main`. It uses npm trusted publishing with GitHub OIDC and needs no npm
token in GitHub Secrets.

## Configure the npm package

In the npm settings for `@jerrylusato/agents-setup`, add a GitHub Actions
trusted publisher with these exact values:

| Field | Value |
| --- | --- |
| Organization or user | `jerrylusato` |
| Repository | `agents-setup` |
| Workflow filename | `publish.yml` |
| Environment | None |
| Allowed action | Direct `npm publish` |

The workflow file is `.github/workflows/publish.yml`. Its `id-token: write`
permission lets npm exchange the GitHub OIDC identity for a short-lived publish
credential. The workflow uses Node.js 24 and must run npm CLI 11.5.1 or newer.
Do not add `NODE_AUTH_TOKEN` to the publish step; it is unnecessary and makes
the authentication path harder to audit.

## Publish and verify

The workflow runs on pushes to `main` and can be started with
`workflow_dispatch`. It tests the package and skips publishing when the exact
version in `package.json` already exists on npm. Bump the version
before a later release; npm versions cannot be overwritten.

After the trust connection and workflow change are in place, run `Publish` from
`main` to retry an unpublished version. Check that the workflow's `Publish to
npm` step succeeds, then verify:

```bash
npm view @jerrylusato/agents-setup version
```

For a trust mismatch, confirm the npm package name, GitHub owner and repository,
workflow filename, allowed direct-publish action, and any environment name.
The npm package's `repository.url` in `package.json` must match the GitHub
repository. Never copy the old `NPM_TOKEN` into logs or the repository.
