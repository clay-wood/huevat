# Huevat technical status

Verification date: October 22, 2026.

## H0: independent numerical foundation

H0 is complete. Local and cross-platform numerical, packaging, provenance, and
clean-install checks pass. The independent private repository is
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
| Cross-platform checks | Verified | Windows/Linux, Python 3.10/3.12/3.14; numerical tests, provenance, build, and offline pip/uv installation checks pass |

## H1: reference study and provisional quality profiles

H1 is complete. Thresholds were committed before evaluation in `90e7b60`;
the implementation and baseline artifacts are in
`b67534618da9eb8ec38a98b51f9abc7041ca9943`.

| Task | Evidence |
| --- | --- |
| Frozen reference corpus | 13 attributed references; native tables, exact Okabe-Ito values, source versions/hashes and retained licenses |
| Versioned protocol and four profiles | `METHODS_H1.md`, `profiles-v1.json`; data marks / filled fields on light / dark backgrounds |
| Screening and independent audit | Normal vision; Machado protan/deutan 50/80/100, tritan 100; Oklab and CAM02-UCS, grayscale and display-clipping records |
| Matched baseline | 296 explicit cases, including float/u8 paths and discrete selections, both backgrounds, 12 negative-control cases |
| Offline gallery | `research/baseline-v1/index.html`; 48 publication-size 300-DPI PNGs, summary JSON, full gzip JSON report and methods report |
| Defect detection | Repeated colors, RGB-interpolation artifacts, lightness reversal, broad flats, narrow spikes and excessive class counts fail intended criteria |
| Visual review | Artifacts and layout checked; human perceptual review remains pending in `review.json` |

Local evidence (Windows, Python 3.12.14): 127 tests passed; frozen corpus
reproduced byte-for-byte; all 296 study cases reproduced within 1e-8;
retained artifact hashes passed; the final wheel built from the source
distribution and passed offline clean pip and uv installation checks. The
installed base package loaded references/profiles and intermediate-severity
simulation without research, plotting or browser packages.

All eight CI jobs passed at `b675346`: six core jobs on Windows/Linux with
Python 3.10/3.12/3.14, and two research jobs on Windows/Linux with Python 3.12.
The research jobs ran all 127 tests, reproduced the frozen corpus and all
296 numerical cases, and verified the retained artifact hashes:
[H1 validation run 39828793418](https://github.com/clay-wood/huevat/actions/runs/39828793418).
The code/source corpus is reproducible across these environments; rendered
PNG byte identity is not asserted across different graphics-tool versions.
The baseline resource wheel is approximately 68 KB; gallery assets remain
separate from the lightweight installed package.

The initial baseline retains all failures. In normal-vision floating-point
paths, Spectral fails the neutral-center and arm-balance goals; ColorCET fire
fails some local-speed/spike screens. The 8-bit ColorCET coolwarm study
adaptation fails the exact-center-extremum requirement. Discrete and CVD
conditions have additional context-specific failures recorded in the reports.
These are results under Huevat's provisional goals, not a universal ranking.
No thresholds were relaxed and no source palette was changed to pass them.

## H2: sequential/diverging construction and immutable sampling

Implemented and locally verified; remote CI verification is in progress.
The H1 reference study, evaluator and frozen thresholds remain unchanged.

| Task | Evidence |
| --- | --- |
| Construction | Optional deterministic multi-start SciPy SLSQP; monotone cubic lightness and smooth Cartesian neutral joins; controlled chroma-reduction fallback |
| Prepared operation | Four experimental sequential/diverging light/dark paths; lookup, `.at()`, reversal and cached discrete sampling use only the standard library |
| Continuous numerical checks | Complete-segment Bernstein gamut bounds, derivative-extrema lightness checks and C1 continuity checks |
| Perceptual screening | All four paths pass unchanged H1 float/u8 profiles and a 4,097-point CVD ordering audit |
| Exact discrete selections | Every count below each prepared curve's arc-length bound audited for both contexts; even/odd counts handled explicitly; seven bins pass on every prepared path |
| Failure semantics | Invalid input, measured selection failures, bounded count conflicts and search exhaustion have distinct outcomes and actionable reports |
| Recipes and reports | Immutable nested reports, data-only JSON/fingerprints, tamper/schema rejection and revalidation of unknown recipes |
| Review artifacts | `research/ordered-v1/index.html`, eight 300-DPI panels, source/artifact hashes, measured generation and core-operation benchmarks |

Local tests: **159 passed** on Windows/Python 3.12.14. The H2 check reproduced
every saved cubic recipe and repeated all continuous/grid/dense checks and
all 151 cached discrete selections. Custom searches reproduced with completed
starts; a forced deadline produced search exhaustion without claiming
infeasibility. A custom background was independently evaluated and serialized.
The dependency-blocking subprocess exercised prepared lookup, seven bins,
reversal and recipe reload without NumPy, SciPy, colorspacious or plotting.
Clean offline pip/uv installation checks also pass; the base wheel is
approximately 272 KB with zero base requirements. The independent H1 check
still reproduces all 296 original reference cases and their retained hashes.

The complete two-start prepared builds, including discrete audits, measured
approximately 1-4 seconds per design on this host. The regular custom budget
is eight starts / 20 seconds; cooperative deadline and reproducibility limits
are documented in `METHODS_H2.md`. Rejected bin counts are retained; for
example, the light diverging path's 8-bin selection fails while its separate
9-bin selection passes. No requested colors are silently removed.

H2 rendering/layout has been checked. Human perceptual review of these new
designs remains pending; `approved_default` stays false.

## Boundaries

H3-H4 remain unimplemented: categorical and multi-hue/Spectral construction,
accepted defaults and the complete export/migration layer are later work.
H1 reference sampling remains an explicit finite-grid study adaptation. H2
certifies numerical properties of complete cubic paths, while perceptual/CVD
screening remains finite-grid evidence. `design` contains optional generation
and audit dependencies; `research` contains optional rendering tools. Core
loading/sampling of references, prepared gradients and profiles remains
independent of these packages.

The source color files were untracked in sketchplot. Their hashes identify the
extraction; its base commit alone cannot reproduce that working-tree state.
Huevat neither modifies sketchplot nor adopts its generated tables as defaults.

The primary Machado supplement timed out during H0 verification; the
colorspacious 1.1.2 transcription supplies H1's frozen matrix tables. All
tabulated severities and coefficient interpolation are tested against that
independent implementation. CAM02-UCS uses fixed standard sRGB viewing
conditions on both backgrounds; it does not model dark adaptation. Human
discrimination and visual approval of defaults remain later work. H2 adds
cooperative optimizer deadlines, with measured limitations recorded explicitly.

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
# Optional H1 research environment and offline reproduction:
uv sync --locked --extra research
uv run --locked --extra research pytest
uv run --locked --extra research python tools/freeze_references.py --check
uv run --locked --extra research python tools/build_baseline.py --check
# H2 optional construction and prepared-evidence reproduction:
uv sync --locked --extra design --extra research
uv run --locked --extra design --extra research python tools/build_ordered.py --check
```

`tools/check_install.py` checks distribution contents and installs the wheel
into two temporary environments using pip and uv, with indexes/network disabled.
It exercises the installed core from outside the checkout and checks that
optional dependencies are absent. Its local record is
`artifacts/install-check.json` (ignored; regenerate instead of treating it as
portable source data).

Implementation commit: `bcefa27d5abbdf92030496f7b771224e97d53d16`.
Portable installation-check fixes: `c722879` and `87575e0`.
The full six-environment CI matrix passed at `87575e0` on October 22, 2026:
[validation run 39824232437](https://github.com/clay-wood/huevat/actions/runs/39824232437).
Each environment ran all 96 numerical/core tests, checked provenance, built
the wheel from the source distribution, and verified offline clean pip and uv
installations. The local Windows/Python 3.12.14 run independently passed the
same checks, including optional comparison with the original source hashes.

CI exposed an installation-check portability issue: copying uv's managed Linux
Python 3.10 executable into a standard-library-created virtual environment
lost the standard-library path. The check now uses uv to provision both empty
environments and development pip's `--python` option to install into the pip
target offline. Package installation is still tested separately with pip and
uv. This affects verification tooling only; pip remains a development
dependency. The complete rerun cited above passed.
