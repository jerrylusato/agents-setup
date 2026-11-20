# Machine skill resolution

`resolve` materializes exact skill packages for CI or an application's release.
It does not modify user skills, installation state, agent wiring, or credentials.

```bash
agents-setup resolve --manifest skills.request.json --dest build/resolved
```

The destination must not exist. The JSON request uses schema version 1:

```json
{
  "schema_version": 1,
  "source": {
    "repository": "iPFSoftwares/skills",
    "version": "v3.1.0",
    "archive_sha256": "<64-character SHA-256 from the approved release>"
  },
  "skills": ["backend/review/api-contract-review"]
}
```

Use an exact release version and approved checksum; mutable refs such as `latest`
and `main` are rejected. Downloads use the authenticated GitHub CLI. A local
`--archive path.tar.gz` can replace the download, but its checksum must still match.

Output contains `skills/<department>/<group>/<name>/` and `resolved.json` with the
source pin, selected metadata, dependencies, repository scopes, and content hashes.
All declared dependencies must be selected. Source names are preserved without
adding installation prefixes. Resolution never executes package code or scripts.
Archive bounds, safe extraction, metadata consistency, and the archive checksum
are checked before the destination is activated. Failures leave no partial output.

Consumers own application policy: department/group restrictions, repository scope,
required load order, and output/authorization boundaries. They should validate the
resolved metadata and pin this CLI's version in their build environment.
