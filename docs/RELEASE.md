# Releasing Huevat

Huevat 0.1.0 includes the supported palette, gradient, adapter, sampling,
export and figure-doctor interfaces. All eighteen named gradients are supported.
Saved recipe IDs, numerical profiles and audit measurements remain unchanged.
Support status is distinct from the scope of a numerical or human assessment.

Maintainer: **Clay Wood** — **clayewood@gmail.com**.

## First-time account setup

Create and verify accounts on [PyPI](https://pypi.org/account/register/)
and [TestPyPI](https://test.pypi.org/account/register/), and enable two-factor
authentication. The two services have separate accounts and project databases.

In each account's publishing settings, add a pending GitHub Trusted Publisher:

| Setting | TestPyPI | PyPI |
| --- | --- | --- |
| Project name | `huevat` | `huevat` |
| GitHub owner | `clay-wood` | `clay-wood` |
| Repository | `huevat` | `huevat` |
| Workflow filename | `release.yml` | `release.yml` |
| Environment | `testpypi` | `pypi` |

The first successful upload creates the project through its pending publisher.
No long-lived package-index token is required. Accounts, verification,
two-factor authentication and publisher authorization must be ready before
running the publication jobs.

## Release sequence

1. Set the version in `src/huevat/_version.py`. Distribution metadata imports
   that same version; do not maintain a second version in `pyproject.toml`.
2. Commit and push the release changes, and confirm the normal CI workflow
   succeeds on Ubuntu, Windows and macOS.
3. Open the **Release to TestPyPI then PyPI** workflow in GitHub Actions.
   Run it from the release commit on `main`, entering the package version.
4. The workflow runs the runtime/scientific suites, builds the wheel and source
   archive, checks their metadata, runs the packaged tests against an installed
   wheel, and tests every extra independently across all three operating
   systems. Minimum declared dependency versions are tested on Python 3.10.
5. The workflow uploads to TestPyPI, compares both index file hashes with the
   built artifacts, and installs the TestPyPI wheel in a clean environment.
6. Only after that verification passes does it upload the same artifacts to
   PyPI. A final job verifies the PyPI hashes and performs a clean installation.

The workflow runs only when dispatched. Ordinary pushes do not publish a
package. Both publication jobs use named GitHub environments and Trusted
Publishing. Build artifacts are retained for 90 days. Commit time is supplied
as `SOURCE_DATE_EPOCH` to make archive timestamps reproducible.

If a version already exists, publication may skip its existing filenames,
but verification still requires their hashes to match exactly. A different
archive under the same version is a failure; fix the release and increment
the version rather than replacing an index file.

## Local verification

```sh
uv sync --locked --all-extras
uv run --locked --all-extras pytest
uv run --locked --all-extras python tools/verify.py --research
uv build
uv run --locked twine check --strict dist/*
uv run --locked python tools/check_install.py --test-sdist
uv run --locked python tools/check_extras.py
```

For minimum-version tests, use Python 3.10:

```sh
uv run --locked --python 3.10 python tools/check_extras.py --minimum
```

After an upload, reproduce the index verification with:

```sh
uv run --locked python tools/check_index.py --repository testpypi --version 0.1.0
uv run --locked python tools/check_index.py --repository pypi --version 0.1.0
```

These commands require the exact uploaded archives in `dist/`.

## Installation

```sh
python -m pip install huevat
python -m pip install 'huevat[matplotlib]'
python -m pip install 'huevat[plotly]'
python -m pip install 'huevat[ultraplot]'
```

[PyPI Trusted Publishing](https://docs.pypi.org/publishing/publishing-to-pypi/)
and [pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
document the account-side setup.
