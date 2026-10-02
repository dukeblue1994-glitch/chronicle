# Releasing Chronicle

PyPI accepts a new version number and valid distributions. Uploads cannot replace files from an existing release. Chronicle additionally requires passing CI before publication.

## Prepare

1. Update `pyproject.toml`, `chronicle/__init__.py`, and the default application version in `chronicle/config.py` together.
2. Add a versioned section to `CHANGELOG.md` and document compatibility changes.
3. Run Ruff, Black, mypy, pytest, `python -m build`, and `twine check --strict dist/*`.
4. Merge the reviewed changes after CI passes.

## Publish through GitHub

Create a GitHub release with a new `vX.Y.Z` tag at the verified commit. `publish.yml` validates metadata, reruns CI, builds and tests the distributions, then uploads those exact artifacts. It uses the existing `PI_PY_TOKEN` secret when configured, or PyPI Trusted Publishing when no token is configured.

The existing PyPI project should trust:

- Owner: `dukeblue1994-glitch`
- Repository: `chronicle`
- Workflow: `publish.yml`
- Environment: `pypi`

Manage this under the existing project's publishing settings. Pending publishers are for projects that do not exist yet.

The manually dispatched **Publish to PyPI (Token fallback)** workflow also accepts an existing tag and uses the repository's existing `PI_PY_TOKEN` secret. It runs the same CI before uploading. Never put the token in source files or logs.

The two publishing workflows share a concurrency group. Do not dispatch both for the same version.

## Verify

Check the GitHub Actions publishing job and the exact version on [PyPI](https://pypi.org/project/chronicle-events/). Install from PyPI into a fresh environment, outside the source checkout, and confirm:

```bash
chronicle --version
chronicle demo --db demo.db
```

The GitHub release alone is not evidence that PyPI accepted the upload.
