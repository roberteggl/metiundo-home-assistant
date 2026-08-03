# Release Management

Releases are created from Git tags. The tag is the release version and the
version in `custom_components/metiundo/manifest.json` must match it.

## Release Types

Use a normal SemVer tag for a stable release:

```text
v1.0.0
```

Use a prerelease suffix for beta releases:

```text
v0.1.0-beta.1
```

Any tag containing a prerelease suffix is published as a GitHub prerelease.

## Release Workflow

1. Update the `version` in `custom_components/metiundo/manifest.json`.
2. Run the local validation and tests.
3. Commit the version change to `main`.
4. Create an annotated tag whose version matches the manifest.
5. Push the tag to GitHub.

Example:

```bash
./script/version --check-tag v0.1.0-beta.1
git tag -a v0.1.0-beta.1 -m "Release v0.1.0-beta.1"
git push origin v0.1.0-beta.1
```

The `Release` workflow then:

- Checks out the tagged commit
- Verifies the tag matches `manifest.json`
- Generates release notes with `git-cliff` and `cliff.toml`
- Creates a GitHub Release with those notes
- Marks tags such as `v0.1.0-beta.1` as prereleases

The workflow does not run for ordinary pushes to `main`.

## Validation

Run the project checks before tagging:

```bash
script/check
script/test
```

The tag workflow performs the version check again so a tag cannot publish a
different version from the integration manifest.

## GitHub Setup

The release workflow needs the `contents: write` permission. This is declared
in `.github/workflows/release.yml` and must not be restricted by repository
settings.

For HACS distribution, the repository must be public and the release must be a
published GitHub Release, not only a Git tag.

## Files

| File                            | Purpose                              |
| ------------------------------- | ------------------------------------ |
| `.github/workflows/release.yml` | Tag-based GitHub release workflow    |
| `cliff.toml`                    | git-cliff release note configuration |
| `hacs.json`                     | HACS metadata and minimum versions   |
| `manifest.json`                 | Canonical integration version        |
| `script/version`                | Version display and tag validation   |
