# H3: categorical and multi-hue construction

Version: `h3-families-v1`. Verification date: October 22, 2026.

H3 adds joint categorical optimization, multi-hue sequential paths and
Spectral-like diverging paths. The H1 `h1-screening-v1` profiles, reference
corpus, evaluator and H2 implementation/resources remain frozen. H3 reuses their
numerical conventions and gates. Passing prepared designs are supported in v0.1; release roles are recorded
separately from their original numerical evidence.

## Categorical construction

For exactly n colors, the variables are 3n encoded sRGB coordinates and one
auxiliary distance z. SLSQP maximizes z subject to every pair satisfying
`d_Oklab(normal)/2 >= z` and `d_Oklab(condition) >= z` for all seven Machado
conditions. This normalization retains H1's independently stricter normal
threshold. `z >= .041` supplies a small export margin over the CVD minimum .04;
it does not replace the final .08/.04 profile gates.

Hard search constraints include encoded RGB in [.002,.998], normal Oklab L in
[.22,.95], C in [.02,.26], 3:1 normal background contrast and CAM02-UCS distances
at least 8.3 normally and 4.15 under every simulated condition. A .005 luminance
margin on the contrast constraint reduces 8-bit boundary failures. The final
float and 8-bit audits use the original thresholds, without these margins.
Construction range checks allow 1e-7 arithmetic tolerance; their measurements
are attached to the floating design, not asserted for every rounded channel.

Each count generates a new random RGB candidate bank and uses farthest-point
selection under the weakest simulated relationship to seed joint searches.
Subsequent starts use the same seeded generator. No published reference is
relabeled and no generated larger palette is truncated. A supplied preference
can initialize one start, but does not become a hard constraint. A second
SLSQP phase reduces preference error while preserving z within 1e-6 of that
start's maximum. Candidate selection applies the same maximin tolerance before
preference error. The search is local and does not prove global optimality.

Each returned palette passes the H1 data-mark profile in floating point and
8-bit export: distinct colors, background contrast and full pairwise Oklab and
CAM02-UCS screens for all eight conditions. Reports retain distance matrices,
closest pairs, simulated clipping and grayscale audit matrices. Grayscale is
an audit, not an assertion that categories remain distinguishable in grayscale.
Preferred-to-produced categorical distances use the exported colors.

Prepared numerical tables cover independently optimized counts 2–12 on
white and #121212. Custom searches support 2–64 categories; the upper bound is
an implementation/resource limit, not an infeasibility theorem. Categorical
construction uses the data-mark context. For arbitrary backgrounds the search
chooses a darker branch if background luminance exceeds .2 and a lighter branch
otherwise. Mixed-contrast branches may be missed; failure is search exhaustion.

## Multi-hue ordered construction

The seven parameters comprise the H2 lightness endpoints and three chroma
controls, a base hue and a hue turn. Sequential lightness uses the monotone H2
spine. A linear phase rotates its Cartesian chromatic coordinates. Spectral
paths use the H2 shared-center lightness/chroma spine with opposed arms; the
rotation is quadratic in center-to-extreme radius. Both arms therefore follow
multi-hue routes. Zero chroma and zero first derivative at the neutral avoid
undefined-hue interpolation and preserve the shared C1 join.

The resulting paths are represented by cubic Hermite segments, splitting each
H2 interval once and matching the rotated values and derivatives at knots.
Hue/rotation products are approximated by these cubics; the delivered cubics
themselves receive every audit. No endpoint-only RGB approximation is substituted.

Deterministic multistart SLSQP constrains gamut, sampled CVD order, span,
background context and, for Spectral, opposite-arm separation/lightness balance.
It improves the weakest local sequential separation or opposite-arm separation
across all eight conditions, treating the normal metric separately at half
scale. A second phase preserves that relationship within 1e-6 while reducing
preference error. Passing candidates are selected by weakest relationship
(1e-6 tolerance), preference error and then cubic chromatic curvature. Seeds
and optima are both screened: an improved floating optimum can fail quantization.
Uniform chroma reductions of .95/.85/.7 are also screened; every reduction
preserves the chosen lightness and hue phase and is recorded in the resulting
construction parameters. This restricted spine family may adjust preferences
substantially or miss feasible routes outside its parameter bounds.

Final validation reuses H2's complete-segment gamut, monotone-L and C1
certificate, H1's 257-point float/8-bit normal/CVD/CAM02-UCS screens and H2's
4,097-point CVD order audit. The certificate operates on identical geometric
coefficients through an H2 schema proxy; no H2 evidence is reused for a new path.
Spectral receives diverging gates: an exact neutral-center extremum, arm spans,
matched lightness and center distances, and opposite-arm separation. Sequential
receives monotone span, local-contrast, flat/spike and spatial-feature gates.

An additional construction audit requires a hue excursion of at least 20
degrees per arm and no cumulative backward hue excursion greater than .1
degree, evaluated on the floating 257-point path where C >= .015. This is a
declared multi-hue construction rule, not a change to any H1 quality threshold
or a continuous hue certificate. Route reports omit the undefined neutral hue.
Preferred-to-produced ordered distances use the nearest floating path color
within the corresponding arm; reported parameter positions respect reversal.

Every discrete count is screened separately in float/8-bit and both contexts,
including its CAM02-UCS distances. Spectral uses the H2 actual-class arm checks,
excluding the center as an opposite-arm class. Even counts omit the center.
All counts below the conservative curve-length bound are cached, including
failures. Larger counts have an explicit fixed-path conflict bound. Neither
continuous approval nor approval of one count implies approval of another.

## Operation and reproducibility

The base package provides prepared lookup, immutable hex palettes and cubic
paths, sampling, reversal, reports and JSON round trips without NumPy, SciPy,
CAM02 tooling, Matplotlib or browser packages. New construction and unknown
recipe auditing require `huevat[design]`. Recognized prepared recipes use
checksum-verified package evidence. Unknown supplied evidence is ignored;
default import revalidates. `validate=False` reports an unvalidated status while
retaining structural checks and ordered numerical certification.

Invalid inputs raise ValueError before optional imports. Budget failure raises
SearchExhaustedError, records optimizer messages and any nearest failed gates,
and explicitly denies an infeasibility proof. A passing candidate already found
may be returned if a later start reaches the deadline. Deadlines are cooperative
between objective/constraint/audit calls; a single numerical audit can overrun.
Completed starts reproduce on the recorded numerical stack; deadline-truncated
runs do not promise identical selections. Cross-platform checks compare retained
measurements at 1e-8; they do not require identical optimizer iterates across
different BLAS/compiler versions or identical PNG rendering bytes.

`tools/build_families.py` creates source hashes, prepared recipes/reports,
generation timings by family/count, cold lookup/sampling/import measurements,
separate traced-memory measurements, 300-DPI PNGs and an offline HTML gallery.
Its `--check` mode reconstructs the ordered coefficients from saved parameters,
reaudits all categorical/path/bin reports and verifies resource/source/artifact
hashes. Independent tests repeat completed searches, exercise deadline and
defect failures and block all optional imports during prepared operation.
Clean pip/uv installs exercise all families outside the checkout. H1/H2 evidence
reproduction remains required in CI alongside H3.

The gallery shows every categorical count, matched .75/1.5-point lines and
3/5-point markers at counts 4/6/8, all CVD severities, full pair matrices at
those counts, grayscale, ramps, discrete legends and synthetic spatial/signed
fields. It links the attributed H1 reference comparisons and H2 gallery.
Rendering/layout inspection is separate from human perceptual review; all
`review.json` panels remain pending and no approved default is claimed.
