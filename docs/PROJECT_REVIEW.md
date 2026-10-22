# Huevat project review after the Clearer H3 revision

October 22, 2026. This review separates implemented changes, measured costs,
code observations and proposed features. Proposed interfaces do not exist yet.
Measurements describe this Windows/Python 3.12.14 host, not universal limits.

## Implemented outcome

`categorical()` now selects the user-approved **Clearer direction**, with
independently optimized prepared counts 2–12 on white and #121212. All 22 pass
the unchanged H1 float/u8 profiles and the new aesthetic envelope. Counts
4/6/8 exactly match the selected comparison swatches. The original construction
remains `style="max-separation"`; existing recipes retain their original colors.
Previously frozen numerical/design modules and versioned resources remain
unchanged. Public exports and the resource manifest add the new revision.

Local verification: 205 tests pass; original H1/H2/H3 evidence and the Clearer
and selection-study reports reproduce. Clean offline pip/uv installs pass
without optional packages. The revised wheel is approximately 1.33 MB with
zero base dependencies. The user selected the categorical direction;
expanded-count visual review and H4's reviewed-default gate remain separate.

## Measured costs

Reproduce with `tools/profile_project.py`. Raw measurements, package versions,
resource hashes and profile stacks are in
`research/project-review-v1/benchmarks.json`. Cold operations use three fresh
isolated processes. Traced memory is measured separately. Warm operations use
five timing repeats; generation uses two completed three-start runs per count.
Profiling is used for attribution, not compared directly with uninstrumented
wall timings.

| Operation | Host measurement | Interpretation |
| --- | --- | --- |
| Core import | About 71 ms | Not the principal plotting bottleneck |
| First Clearer 8-color lookup, after import | About 32 ms | Resource reading/parsing dominates |
| Warm Clearer 8-color lookup | About .48 ms | Cheap, but still rebuilds an immutable object/report |
| First Spectral lookup, after import | About 50 ms | Loads shared original H3 evidence |
| Warm Spectral lookup | About 5.6 ms | Re-freezes recipe/count evidence |
| Spectral report access | About 2.7 ms | Repeated nested report conversions |
| Spectral reversal | About 10.2 ms | Rebuilds cached records for an orientation change |
| Spectral 7-bin selection | About 11.7 ms | Proxy/report handling outweighs seven color evaluations |
| 4,096 sequential samples | About 14.5 ms | Sampling is already inexpensive for plotting-sized tables |
| First custom 4-color request, one start | About .79 s | Includes optional-library imports and search |
| Three-start generation, warm design stack, light background | 4 colors .55–.56 s; 8 colors 1.36–1.41 s; 12 colors 4.13–4.24 s | Count-dependent search cost; keep it outside ordinary plotting |

The separate import/lookup measurement peaks at about 14.3 MB of traced Python
allocations for Clearer 8, 27.4 MB for Spectral and 39.6 MB for all families.
These are tracemalloc allocations, not process RSS. The current categorical
resource is 3.34 MB JSON, original H3 evidence 6.83 MB and H2 evidence 3.53 MB.
They remain cached after loading. The 8-color JSON envelope is about 143 KB;
the Spectral envelope is about 161 KB.

For a normal plot, create one palette/gradient and reuse it. Repeated object
construction, report conversion and per-pixel Python sampling are distinct
workloads; the numerical color model itself is not the main measured lookup cost.

## Bottlenecks and proposed remedies

### Runtime data and full evidence are coupled

The cold Clearer profile spends about 29 ms of its approximately 32 ms call in
resource loading. Requesting one palette loads every count/background's full
normal/CVD pair matrices in both encodings. That is valuable research evidence
but unnecessary for a simple plotting lookup.

Proposed remedy: separate compact runtime recipes and concise hash-linked
summaries from full audit details. Load matrices explicitly, possibly per
family/count/background. Offer compact exports retaining the floating recipe
and evidence identity/hash. Preserve all full research reports and independent
audits; a compact summary must not become an unverified pass claim.

### Immutable views repeatedly copy already immutable evidence

Profiling ten Spectral report reads shows roughly 97,000 `_thaw` calls and
90,000 `_freeze` calls, with overlapping cumulative times. `HueGradient.report`
builds an H2 proxy, copies its report and freezes the result again. Reversal
also reconstructs cached discrete evidence. The categorical `report` attribute
is already cheap; this finding applies specifically to gradient wrappers.

Proposed remedy: share frozen records between source/reversed views, cache
prepared objects and cache orientation-specific reports. Transform only changed
arm labels and parameter positions. Keep `.to_dict()` as the explicit mutable
copy. Preserve immutability and historical evidence with regression tests.

### Finite-difference constraints dominate custom search

In a profiled completed 8-color, one-start search, approximately .485 s of
.543 s cumulative time lies under numerical derivative estimation. Constraints
run 523 times; `_pair_data` accounts for about .433 s of overlapping cumulative
time. Every call transforms colors under eight conditions and measures two
spaces. The Oklab helper also loops in Python. Perturbing each RGB variable
multiplies these costs as the count rises.

Proposed order: share duplicate evaluations at the same vector, vectorize/batch
optional design transforms against the frozen scalar implementation, then add
tested Jacobians for smooth interior constraints. Keep final CAM02, quantized
and complete-path audits independent. Clipping/active constraints require
careful derivative treatment.

[SciPy supports callable Jacobians](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html).
Its [SLSQP workers option](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)
was added in 1.16, while Huevat permits 1.10. Parallel workers need feature
detection or an explicit compatibility change. Current nested closures also
complicate process workers on Windows. Optional parallel starts should retain
deterministic seeds/ranking and honest deadline reporting. Profiling and
derivatives come before concurrency.

### One factory combines lookup with unpredictable search

Standard calls load prepared data; custom preferences, backgrounds, counts or
changed search settings trigger optional imports and optimization. Even changing
`max_seconds` can switch the operation. This is documented but surprising.

Proposed remedy: visibly separate prepared lookup/discovery from explicit
custom design in H4, with compatibility for existing calls. Custom design
should expose budgets, progress and cancellation. Normal plotting should have
predictable latency and dependency behavior.

### Versioning rigor also creates maintenance friction

Certificate code, recipe schemas and family audits are coupled, leading to
schema proxies. Whole-module source hashes make unrelated refactoring look
like changed scientific evidence.

Proposed remedy: separate geometry certification, version dispatch and
presentation. Keep immutable recipes, provenance and frozen regression fixtures,
while distinguishing implementation changes that reproduce the same mathematics
from changed numerical methods. New engines still must reproduce or explicitly
version the retained evidence.

## What would make Huevat easier to use

1. **One-line plotting adapters.** Provide optional Matplotlib colormaps/color
   cycles, Seaborn sequences and Plotly mappings, with examples for lines,
   images and signed fields. [Matplotlib supports ListedColormap and named
   registration](https://matplotlib.org/stable/users/explain/colors/colormap-manipulation.html).
   [Plotly supports label-to-color maps and category order](https://plotly.com/python/discrete-color/).
   Sample actual Huevat paths with stated approximation control; endpoint RGB
   interpolation must not silently replace the path.
2. **Readable summaries and notebook swatches.** Show style, background/context,
   closest pair, passing discrete counts and review status before full matrices.
   Separate numerical pass, chosen direction and H4 human approval.
3. **Discovery.** List styles, immutable identifiers, prepared counts and
   contexts. Expose all passing counts for a fixed gradient.
4. **Actionable failures.** Name the colliding labels/colors and viewing
   condition. Suggest nearby passing counts or marker/dash alternatives. The
   H2 light diverging path fails 8 bins but passes 9, so simply saying “reduce n”
   is incomplete.
5. **Stable labels.** Map named categories explicitly, preserve assignments
   across figures and save them with a versioned style. Joint count optimization
   can otherwise adjust colors when categories appear or disappear.
6. **Explicit data semantics.** Carry sequential/signed meaning, actual center,
   missing-data and under/over-range colors in adapters. A neutral at t=.5 does
   not put zero correctly in an asymmetric data range by itself.
7. **A short quick start.** Lead with a six-series plot, heatmap and signed
   field; link the research details. Retain browser-free offline plotting.

## Creative features worth considering

These are proposals, not completed features or universal accessibility claims.

| Idea | Concrete experience | Requirement to retain |
| --- | --- | --- |
| Persistent color identities | “Control stays blue in every notebook, even when treatments are absent.” Save a label registry and paired light/dark colors. | Preserve old assignments or explain why a new label cannot fit; no silent recoloring. |
| Figure doctor | Inspect an existing figure; show CVD/grayscale proofs, confusing series, missing-value ambiguity and repairs. | Audit actual alpha-composited colors, backgrounds and mark geometry. |
| Color + marker + dash design | Assign coordinated identities to dense experimental series instead of relying only on 16 different hues. | Report multichannel encoding; never relabel a failed color-only palette as passing. |
| Figure-aware assignment | Prioritize extra separation between crossing lines or neighboring map regions. | Keep all baseline pairwise floors; the comparison graph controls extra separation. |
| Palette negotiation | Show three passing aesthetic/separation tradeoffs on the user's actual plot, with an optional pinned color. | Preserve hard gates; distinguish locked colors from adjustable preferences. |
| Optimized bin positions | Find seven well-separated classes along a gradient and return explicit class boundaries. | Keep order and center semantics, disclose nonuniform spacing and audit that exact selection. |
| Publication proof sheet | Export the actual figure at column width with actual-size marks, CVD/grayscale previews, recipe IDs and methods caption. | Separate rendering proof, numeric pass and human approval. |
| Paired uncertainty styles | Give each series a line color, uncertainty-band fill and boundary style. | Audit the composited fill and preserve series identity. |

## Suggested order

First finish H4 with reviewed families/counts, accepted identifiers, plotting
adapters, concise summaries, passing-count discovery, compact exports and exact
migration notes. Include stable label mapping early; it solves a common
practical failure.

Then improve shared immutable objects/views, lazy audit loading, optional
vectorized transforms and derivatives. Scalar sampling can wait until large
images/animation justify attention. GPU/browser infrastructure does not address
the measured JSON and object-copying costs.

For a distinctive next feature, prioritize a figure doctor plus coordinated
color/marker/dash repair. That can help users who already have a favorite
published palette, extending Huevat beyond another collection of named colors.
