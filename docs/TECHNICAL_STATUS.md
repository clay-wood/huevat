# Huevat technical status

Verification date: October 22, 2026.

## H0: independent numerical foundation

H0 is implemented. Local numerical, packaging, provenance, and clean-install
checks pass. The independent private repository is
[clay-wood/huevat](https://github.com/clay-wood/huevat).

| Task | Status | Evidence |
| --- | --- | --- |
| Independent Python package | Implemented | `src/huevat`, `pyproject.toml`; zero base dependencies |
| uv development workflow | Verified | Python 3.12.14, uv 0.12.20; locked sync and 96 numerical/core tests pass |
| Extracted numerical foundation | Verified | sRGB/Oklab/Oklch, gamut mapping, hex, contrast/distance, severity-100 simulation |
| Provenance and license retention | Verified | `PROVENANCE.md`, `extraction.json`, three retained-file fingerprints and original test-file hash |
| Clean pip and uv installations | Verified | Source distribution builds its wheel; offline clean pip and uv installs pass on Python 3.12.14 |
| Browser-free operation | Verified | Wheel has no base requirements; optional imports blocked in tests; clean installs have no browser/plotting/numerical packages |
| Private repository | Created | `clay-wood/huevat`, created private on October 22, 2026 |
| Cross-platform checks | Configured | Windows/Linux, Python 3.10/3.12/3.14 CI; remote results pending |

## Boundaries

H1-H4 remain unimplemented. H0 exposes no approved palette, constructor,
gradient object, optimization, or perceptual pass/fail profile. NumPy and SciPy
are declared only in the optional `design` extra. Core imports and clean base
installations must work without them or browser packages.

The source color files were untracked in sketchplot. Their hashes identify the
extraction; its base commit alone cannot reproduce that working-tree state.
Huevat neither modifies sketchplot nor adopts its generated tables as defaults.

Vision simulation currently uses only severity 100. The primary Machado
supplement timed out during verification; the published colorspacious
transcription supplied the matrix comparison. Intermediate severities,
CAM02-UCS, quantitative profiles, galleries, and visual review belong to H1+.

Gamut conversion and export tolerances are documented numerical conventions,
not perceptual acceptance thresholds. Simulated displays clip out-of-range
channels. Candidate gamut mapping instead reduces chroma at fixed L/h.

No PyPI publication is part of H0. The requested repository is private.

## Reproduction

```powershell
uv sync --locked
uv run --locked pytest
uv run --locked python tools/check_provenance.py
uv build
uv run --locked python tools/check_install.py
```

`tools/check_install.py` checks distribution contents and installs the wheel
into two temporary environments using pip and uv, with indexes/network disabled.
It exercises the installed core from outside the checkout and checks that
optional dependencies are absent. Its local record is
`artifacts/install-check.json` (ignored; regenerate instead of treating it as
portable source data).

The initial repository commit contains the implementation, plan, source hashes,
tests, and this record of local verification. Refer to `git log --reverse` for
that commit; the next status revision will cite it directly with remote CI
results.
