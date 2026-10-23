# Huevat technical status

Verification date: October 23, 2026. Historical sections retain their milestone records.

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

H2 is complete at implementation commit
`8fa85029432c0118e6a5ab30802f091b2b17a6dc`.
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

All eight CI jobs passed at the implementation commit: six core jobs on
Windows/Linux with Python 3.10/3.12/3.14 and two design/research jobs with
Python 3.12. The research jobs passed all 159 tests, reproduced the original
H1 corpus/baseline and reproduced all H2 cubic and discrete evidence:
[H2 validation run 39842172702](https://github.com/clay-wood/huevat/actions/runs/39842172702).
Core jobs independently checked browser-free offline wheel installation,
prepared sampling and recipe reloading without optional dependencies.

## H3: categorical and multi-hue/Spectral construction

H3 is complete at implementation commit
`c58c9c89bf69c7b48249c84b8b2be3e835b97a4d`. Its numerical gates pass on both
backgrounds; H1/H2 sources, profiles and prepared designs remain frozen.

| Task | Evidence |
| --- | --- |
| Count-specific categorical search | Joint 3n RGB coordinates plus auxiliary minimum-distance variable; deterministic multistart SLSQP with explicit contrast, range, Oklab and CAM02-UCS constraints |
| Prepared categories | 22 independently optimized palettes: every count 2–12, light and dark; full float/u8 pair matrices and grayscale audits |
| Multi-hue sequential | Smooth rotating cubic spine; ordered hue and lightness, H1 local-contrast/spatial-feature gates and dense CVD order audit |
| Spectral-like construction | Two multi-hue arms with one shared Cartesian neutral and C1 join; unchanged H1 center, arm-order, span, balance and separation criteria |
| Exact discrete counts | All counts below conservative path-length bounds audited in both contexts, including failures; no silent dropping of classes |
| Lightweight operation | All new prepared lookups, sampling, reversal and JSON reloads work with every optional import blocked |
| Reproduction and failures | Completed count/path searches repeat; custom backgrounds/preferences are audited; exhausted budgets never claim infeasibility |
| Complete gallery | `research/families-v1/index.html`; 18 300-DPI panels, all count legends, matched lines/marks, CVD, grayscale, distance matrices and spatial/signed fields; links to H1/H2 comparisons |

Local test suite: **190 passed** on Windows/Python 3.12.14. H1's 296 cases
and all H2 numerical/discrete evidence independently reproduce. H3's final
resource/source/artifact checks reproduce all 22 categorical reports and all
four ordered recipes, continuous/dense audits and cached bin selections.
Clean offline pip and uv installs pass outside the checkout with no optional
packages installed. The wheel is approximately 895 KB and has zero base
requirements. Full recipes, reports, source hashes and
per-count generation timings are retained in `families-v1.json` and the gallery
results. Human perceptual review remains pending; every approved-default flag
is false.

The custom H3 budget is four starts / 30 seconds. Prepared tables were built
with two completed starts and a 120-second safety budget, with actual measured
times retained per family/count. Deadlines are cooperative and may overrun by
one audit call. Search bounds restrict the route family and background contrast
branch; failed searches do not prove that a different parameterization is
impossible. H3 adds a declared 20-degree hue-route construction rule while
leaving every H1 profile threshold unchanged. See `METHODS_H3.md`.

On this host the two-start categorical searches measured approximately
.13–4.2 seconds by count/background; multi-hue sequential searches measured
4.5–4.7 seconds and Spectral searches 7.6–10.6 seconds. A separate clean process
measured approximately 76 ms core import, 75 ms for the three H3 cold lookups
together and 16 ms for 4,096 cubic samples. A separate traced-memory run peaked
at approximately 27.5 MB for import, categorical lookup and Spectral lookup.
These are host measurements, not performance guarantees. No optional numerical,
rendering or browser modules loaded during the core benchmark.

All eight CI jobs passed at the implementation commit: six core jobs on
Windows/Linux with Python 3.10/3.12/3.14 and two design/research jobs with
Python 3.12. The research jobs passed all 190 tests, reproduced the H1 corpus
and 296 baseline cases, reproduced all H2 evidence and reaudited every H3
categorical/path/discrete report and retained hash:
[H3 validation run 39862188952](https://github.com/clay-wood/huevat/actions/runs/39862188952).
Core jobs independently verified offline clean pip/uv installs and all-family
prepared sampling/recipe reloads without optional dependencies.

## H4a: adapters and optimized discrete sampling

Implemented October 23, 2026. All three adapters return native plotting objects:
Matplotlib colormaps/property cycles/normalizers, Plotly scales/color axes and
label maps, and UltraPlot continuous/discrete colormaps and native property
cycles. Registration is explicit. Asymmetric ranges, exact centers, masks,
under/over policies and explicit physical class boundaries are covered.

`optimized_discrete` returns immutable colors, normalized positions and a
count-specific float/u8 normal/CVD Oklab/CAM02-UCS report. Filled fields use
adjacent maximin dynamic programming; data marks use all-pair compatibility
search. Source paths/endpoints remain fixed, with mirrored diverging arms.
The light diverging eight-color optimized selection passes while its unchanged
uniform selection fails. Recipes revalidate on load. `known_counts` discovers
prepared passing uniform counts; `summarize` gives compact status information.

The base remains dependency-free, with deferred imports and separate
`matplotlib`, `plotly` and `ultraplot` extras. Native backend checks used
Matplotlib 3.11.2, Plotly 7.1.0 and UltraPlot 2.7.3 on Windows/Python 3.12.14.
All 243 local tests pass, including 38 new sampling/adapter tests. All H0
fingerprints and H1/H2/H3/Clearer evidence reproduced unchanged. Local offline
clean pip and uv base installations pass.

The native gallery and ten audited selections are in `research/adapters-v1`;
usage and limitations are in `METHODS_H4A.md`. Native PNGs were visually
checked; Plotly figures/serialization were tested. Browser interaction review
of local HTML was blocked by the browser tool's file-URL policy.

Approximation evidence covers dense finite grids and explicitly makes no new
H1 approval claim for rendered figures. Mutations invalidate that evidence.
Optimized selections use cooperative budgets; failure is finite-search
exhaustion, except for explicit fixed-path count bounds. Prepared optimized
caches and nearby-count suggestions remain follow-up work. The source and
artifact hashes can be verified with `tools/build_adapters.py --check`.

Implementation commit: `34ba2f2d022ebde66e544292ee612688c6f1291e`.
All eight cross-platform jobs passed:
[H4a validation run 39990104341](https://github.com/clay-wood/huevat/actions/runs/39990104341).
The six core jobs cover Windows/Linux with Python 3.10/3.12/3.14, including
distribution builds and clean offline installs. Both Python 3.12 research jobs
exercise all three native backends, reproduce the frozen milestones and
revalidate the ten optimized selections and H4a gallery hashes.

## H4b: named gradient candidates and application gallery

Implemented October 23, 2026. Twelve independent free-knot routes provide
eight sequential and four diverging choices, with 24 screened light/dark
variants. `gradient_names` filters by family/domain, `gradient_info` returns
immutable route/direction metadata, and `gradient(name, background=...)` loads
prepared paths without optional dependencies. Known recipe hashes reload from
shipped evidence; modified recipes receive the established independent audit.

All 24 variants pass the unchanged H1 float/u8 normal/CVD Oklab/CAM02-UCS
profiles, continuous numerical certificates and denser ordering audit. The
checker reproduces their exact construction from retained parameters, all 336
prepared context/count reports and three deliberately bad controls. The 24
construction records retain 3,956 rejected trials in a separate 202 KB gzip
archive, keeping trial history out of runtime lookup data. The base remains
dependency-free. Existing H0–H3 data and all H4a numerical sources are unchanged;
H4a's public-import fingerprint records the added lazy catalog exports.

Local verification: all 256 tests pass, including 13 new collection tests;
all earlier milestone evidence reproduces. Clean offline pip/uv installations
load all 24 variants without optional packages; the wheel is approximately
1.90 MB. The 35-panel gallery includes
normal/CVD/grayscale comparisons, seismic rasters and wiggles, weak structural
features, separate land/water mappings, explicitly separate hillshade review,
and linear/log atmospheric examples. Original physical units, sign conventions,
centers and missing/no-signal distinctions remain explicit. Synthetic wavelets
are exactly centered and symmetric. Hillshade derivative filling preserves
the displayed missing mask and does not replace source values.

The gallery is `research/collection-v1/index.html`; API, construction protocol,
pilot refinements and reproduction are in `METHODS_H4B.md`. All panels were
inspected in contact sheets, with representative panels checked at full size.
Appearance review is pending and no reviewed default is adopted. Browser
filter interaction remains untested under the local-file browser restriction.

## Boundaries

Roadmap update, October 23, 2026: the user accepted figure doctor with
coordinated encodings, figure-aware assignment and palette negotiation;
optimized discrete sampling; more general and application-specific gradients;
and required Matplotlib, Plotly and UltraPlot adapters. `NEXT_STEPS.md` defines
the expanded H4 slices and acceptance gates. H4a and the H4b candidate collection
are implemented; H4b appearance review is pending. Figure doctor (H4c) and final
adoption/release gates (H4d) remain planned. H0–H3 numerical implementation/data and the existing
uniform sampling API remain unchanged.

Categorical aesthetic revision: the user selected **Clearer** from the
appearance study. `categorical()` now uses `h3-categorical-v2`: satisfy the
original quality floors, then preserve the selected aesthetic targets. All 22
prepared counts 2–12 pass on both backgrounds, and counts 4/6/8 reproduce the
chosen study's hex colors exactly. Original H0–H3 sources/data are preserved;
`style="max-separation"` and old recipes retain their original colors. See
`METHODS_CATEGORICAL_V2.md` and `research/categorical-v2`. Expanded-count visual
review and H4 adoption remain separate from the user's selection of direction.

The Clearer revision passes **205 local tests** and all retained H1/H2/H3-v1,
selection-study and v2 evidence checks. Offline clean pip/uv installations pass
with zero base dependencies; the wheel is approximately 1.33 MB. The project
review and reproducible measurements are in `PROJECT_REVIEW.md` and
`research/project-review-v1/benchmarks.json`. They identify evidence loading,
immutable-report/view copying and finite-difference constraints as the main
measured costs; ordinary 4,096-point sampling takes about 14.5 ms on this host.

Revision implementation commit: `9e7d9d19dc03f264f734e64b51beec9e460ad48a`.
All eight cross-platform CI jobs passed: six core jobs on Windows/Linux with
Python 3.10/3.12/3.14 and two research jobs with Python 3.12. The research jobs
passed all 205 tests and reproduced H1, H2, original H3 and the revised Clearer
evidence. Core jobs verified clean offline pip/uv installs of both categorical
styles and all ordered families without optional dependencies:
[Clearer validation run 39871485468](https://github.com/clay-wood/huevat/actions/runs/39871485468).

H4 remains: reviewed and accepted defaults and the complete export/migration
layer are later work. All construction families are now represented.
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
# H3 optional construction and prepared-evidence reproduction:
uv run --locked --extra design --extra research python tools/build_families.py --check
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
