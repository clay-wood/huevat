# Distribution audit — October 25, 2026

Huevat is already an installable Python library and a viable private release
candidate. A public distribution still needs release engineering and a human
review of the revised experimental collection. No upload or repository privacy
change is authorized by this audit.

## Initial repository size

Measured before installing optional dependencies or regenerating artifacts:

| Scope | Size |
| --- | ---: |
| Entire local checkout, including Git and local environment | about 141 MiB allocated |
| Git directory, including history | 86.5 MiB allocated |
| Git tracked working files | 30,106,098 bytes / 28.71 MiB, 215 files |
| Tracked research galleries/evidence | 16.91 MiB |
| Tracked `src` | 10.98 MiB |
| Original wheel | 1,603,774 bytes / 1.53 MiB compressed |
| Original source archive | 1,726,535 bytes / 1.65 MiB compressed |
| Original wheel contents | 11,611,531 bytes / 11.07 MiB unpacked |

The main source payload is prepared JSON reports: collection 4.30 MiB,
families 3.16 MiB, ordered designs 1.80 MiB and categorical designs 1.38 MiB.
The repository's largest individual gallery asset is the 4.65 MiB standalone
Plotly HTML. Git's object report was 70.01 MiB packed plus 1.84 MiB loose;
`.git` allocation also includes indexes and other bookkeeping.

Installing all plotting/design dependencies increases `.venv` substantially.
That environment is ignored and is not shipped in the package. Compare tracked
bytes and distribution sizes separately from a developer's full checkout.

## Verified starting point

- All 123 tests passed with the locked optional dependencies on macOS arm64,
  Python 3.12.14. Before installing extras: 96 passed, 27 skipped.
- Three extraction fingerprints and eight resource hashes verified.
- Runtime verification covered 32 gradient paths, 44 palettes, prepared
  uniform counts, reversal and recipe round trips.
- `uv build` produced a pure Python `py3-none-any` wheel by rebuilding from
  its source archive. Twine's strict checks passed for both archives.
- The wheel has no unconditional runtime dependencies and includes all nine
  data resources plus the MIT and third-party notices.
- Research galleries, environment/cache files and tooling are excluded from
  distributions. The source archive includes selected tests, examples and docs.

## Findings and release gates

1. **Gradient curation is unfinished.** The named routes are experimental,
   despite older plan wording saying the private release was complete. The
   reported pairs are near duplicates rather than identical tables. Initial
   mean Oklab distances were 0.025/0.019 for Aerosol–Rosewood and 0.018/0.017
   for Balance–Thermal (light/dark). Bathymetry–Mineral was 0.029 on light;
   their dark paths have opposite scalar directions and must also be compared
   after orientation alignment. Numeric screens do not assess catalog variety
   or substitute for the user's appearance review.
2. **Source-archive tests referenced excluded tooling.** Reproduced
   `ModuleNotFoundError: build_collection` in the gallery preview test when
   run from the extracted original sdist with optional dependencies available.
   The revised test explicitly skips that repository-only check when the
   builder is absent. Add distribution tests to CI so this cannot recur.
3. **Index-facing metadata and documentation need preparation.** `pyproject`
   lacks maintainer/contact, project URLs, keywords and classifiers. Those
   fields improve discovery/support rather than make an otherwise invalid
   package valid. README install commands assume a local checkout; its relative
   documentation/image links need accessible absolute targets for PyPI.
   Source archives omit the research images still referenced by the README.
4. **CI exercises the base and all extras together.** It does not test each
   extra as an independent user installation or the lower dependency bounds.
   The advertised Python range is 3.10+, while the configured matrix is
   3.10/3.12/3.14 on Ubuntu/Windows; macOS and other minor versions lack remote
   coverage. This audit's local run does not prove those remote jobs passed.
5. **Release publishing is absent.** There is no release workflow, TestPyPI
   rehearsal, artifact retention/upload, or index ownership evidence. The
   current name's availability was not established; do not infer availability
   from an unsuccessful web fetch. Agree on distribution audience before
   changing local-install guidance into public-index instructions.
6. **Package size is reasonable; evidence dominates runtime data.** Full
   frozen reports account for most of the uncompressed package. Compact
   prepared tables plus separately available evidence could improve size and
   first lookup memory, but this is an optimization rather than a build blocker.
   The 70 MiB Git pack is history, independent of the wheel; history rewriting
   is unnecessary for a working Python distribution.
7. **Maintenance polish remains.** Versions are repeated in package metadata,
   code, builders and smoke checks. Fixed pytest file lists and `.gitignore`
   allowlists make new tests/tools easy to miss. Contributor/release guidance,
   an explicit compatibility policy and measured cold lookup costs would help.
8. **An existing gallery manifest broke CI.** The checked-in figure-doctor
   manifest fingerprint for `tools/build_doctor.py` did not match that script,
   although neither file had local changes at the start of the audit. The
   standalone `build_doctor.py --check` failed. This pass regenerates the
   figure-doctor evidence and manifest from the current source.

## Current implementation and validation

This pass implements nine-bin default sampling, composable `_r`/`_d` named
suffixes, revised lookalike routes, six additional experimental choices,
retained old IDs, and updated continuous/nine-bin review galleries. There are
now eighteen named routes and 94 saved designs. All 76 prior designs retain
their exact recipe and orientation hashes.

The revised reported pairs have orientation-aligned mean Oklab distances of
0.061/0.059 (Aerosol–Rosewood), 0.080/0.066 (Balance–Thermal) and 0.066/0.064
(Bathymetry–Mineral), measured at 65 positions on light/dark backgrounds.
A separate `.045` regression guard checks these curation changes; it does not
change the frozen scientific profiles or certify human distinguishability.
Related hue routes elsewhere in the catalog still need appearance review.

Final local checks: 148 tests passed; all three extraction fingerprints,
eight resource hashes, 50 continuous paths, 44 categorical palettes, recipe
round trips and prepared counts passed. Independent normal/CVD float/8-bit
audits passed. The collection checker reproduced all 42 current/retained
free-knot paths and their count reports. The release checker verified all 94
IDs and eight continuous CSS exports; adapter checks reproduced ten optimized
selections and exports for all three backends. Clean offline pip and uv base
wheel installs passed, and strict Twine checks passed for both archives.
In a separate temporary environment, the built wheel and all extras passed
147 tests from the extracted source archive; one repository-only gallery test
was explicitly skipped. The installed module path was verified outside this
checkout. After regeneration, the figure-doctor checker also reproduced all
eight native cases, three tradeoffs, locked failures, guarded undo and hashes.

After this work, source-controlled files plus new deliverables total about
32.9 MiB. The complete local checkout is about 406 MiB, dominated by the
274 MiB optional-dependency environment and 86.5 MiB Git directory. The current
wheel is about 1.84 MiB compressed (14.29 MiB unpacked); the source archive is
about 2.01 MiB. Small changes to this report and regenerated evidence affect
exact byte counts. The environment, Git history and research galleries are
excluded from the wheel.

The release gates in [project_plan.md](../project_plan.md#6-distribution-audit-and-collection-revision--october-25-2026)
remain open; no public/private-index upload was performed.

## Packaging references

- [PyPA: project metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
- [Twine: distribution validation](https://twine.readthedocs.io/en/stable/#twine-check).
- [PyPA: release workflows and Trusted Publishing](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).

These references inform the release checklist; repository findings above come
from local files and executed checks.
