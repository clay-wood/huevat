# H2 ordered construction and validation

Implemented October 22, 2026. H2 adds single-hue sequential and two-arm
diverging construction. The H1 reference corpus, evaluator, methods artifacts
and **h1-screening-v1 thresholds remain unchanged**. The four prepared paths
are experimental numerically screened designs; accepted, visually reviewed
default identifiers remain H4 work.

## User interface and dependency boundary

```python
import huevat as hv

seq = hv.sequential(color="#0072b2", background="dark")
div = hv.diverging(colors=("#0072b2", "#d55e00"), background="light")
rgb = seq.at(0.35)
bins = div.discrete(7)       # Immutable hex-color sequence with its own report
reverse = div.reversed()
report = div.report          # Immutable nested mapping; report.to_dict() copies it
recipe_json = div.to_json()
restored = hv.load_recipe(recipe_json)
```

Prepared lookup, sampling, reversal, cached count screening and JSON loading
of a recognized prepared recipe use the standard library only. They never run
optimization. The shipped blue and blue/orange preferences select these
prepared designs on the stated light/dark backgrounds.

Install `huevat[design]` for custom preferences or backgrounds. It contains
NumPy, SciPy and colorspacious for constrained construction and independent
CAM02-UCS audits. Research rendering remains a separate optional extra.

```python
custom = hv.sequential(color="#0066aa", background="#171d26",
                       seed=4402, starts=2, max_seconds=60)
```

Backgrounds accept `light`, `dark`, six-digit hex, or finite encoded-sRGB
triples. They are measured separately; custom backgrounds have no visual
review claim. `context="filled-fields"` is the constructor default.
`data-marks` applies 3:1 background contrast to the continuous path, while
`gradient.discrete(n, context="data-marks")` separately screens those exported
marks. Some color/context requests exhaust the bounded search.

## Cubic representation

A data-only recipe contains knots on [0,1] and three power-basis cubic
polynomials per interval, in Oklab. Coefficients are in ascending powers of
normalized interval coordinate u. The core evaluates those same polynomials
with Horner's rule and converts to encoded sRGB without optimization.

Sequential designs use a monotone PCHIP lightness profile (currently linear
control lightness is sufficient) and three nonnegative chroma controls on one
constant hue axis. Diverging designs use a shared neutral at t=.5, matched
lightness profiles on two arms and opposite Cartesian chromatic directions.
Both lightness and chromatic derivatives vanish at the center. This avoids
small CVD lightness reversals that appeared between the H1 grid points when
only the lightness derivative vanished. Radius controls shape chroma away
from the neutral without interpolating an undefined neutral hue.

The light-background diverging path has a light neutral; the dark-background
path has a dark neutral. Sequential direction runs from near-background
lightness toward the opposite lightness extreme. Reversal is a view of the
same continuous path, with corresponding report and bin-order metadata.

Supplied colors are preferences. In the H2 diverging model they can move toward
opposite chromatic directions to retain arm balance. Reports show each
supplied value, nearest produced value, parameter and Oklab displacement.
Displacement is measured on the floating design; the produced hex is its
corresponding 8-bit display value.
No supplied palette is overwritten or relabeled as a published reference.

## Search priorities and practical budgets

Generation uses a fixed seed and bounded deterministic starts. SciPy SLSQP
first optimizes the weakest modeled relationship subject to sampled gamut,
span, parameter bounds and applicable background-contrast constraints. A
second constrained pass improves preference fit while retaining the first
pass's relationship within numerical tolerance. Fully passing candidates are
selected lexicographically: constraints/screens, weakest relationship,
preference displacement, then unnecessary chromatic curvature. No weighted
average can hide an individual failing screen.

Initial seeds came from bounded deterministic numerical prototypes. A global
constant-lightness/hue chroma reduction can rescue an out-of-gamut candidate;
the complete altered path must then pass every certificate and screen.
Pointwise RGB channel clipping does not repair candidates.

The prepared build uses two starts and a 60-second allowance per design; the
constructor's advanced custom-search defaults are eight starts and 20 seconds.
Measured complete builds, including all cached discrete audits, are recorded
in `research/ordered-v1/results.json`. Objective/constraint calls and candidate
boundaries check a cooperative deadline. One in-progress numerical audit may
finish after that boundary; this is not a hard process-kill timeout.

Completed starts and a fixed seed reproduce the search on the recorded
dependency versions. A wall-time cutoff can stop at different starts on
different hosts, so reports record completed optimizations, candidate counts,
elapsed time and whether the deadline was reached. The returned recipe is
itself an exact data record of the selected result.

## Continuous numerical checks and finite-grid screening

Lightness derivative extrema certify monotonicity of each cubic arm, and
value/first-derivative checks enforce C1 joins. Adaptive Bernstein interval
bounds enclose the Oklab-to-linear-sRGB conversion over complete intervals.
Unresolved or out-of-gamut bounds reject a candidate. These are conservative
floating-point numerical certificates, with explicitly recorded tolerances
and subdivision limits; they are not a directed-rounding formal proof.

The unchanged H1 evaluator screens the **actual shipped cubic sampler** at
257 points in both float and round-to-nearest 8-bit encoding. It covers all
normal/CVD conditions, grayscale, arm/center balance and independent CAM02-UCS
measurements. A separate 4,097-point floating-point audit tests CVD lightness
ordering between the original sample locations. The local-step thresholds
remain attached to the fixed H1 grid; they are not incorrectly reused on a
denser grid. Continuous gamut/C1/lightness checks do not establish continuous
perceptual or human-visibility guarantees.

Only arithmetic-sized RGB excursions within the established gamut tolerance
may be snapped after validation. A larger excursion raises an error at
sampling; it is never silently repaired.

## Discrete counts and honest failures

`discrete(n)` uses exactly n endpoint-inclusive samples. It checks floating
and quantized colors separately under normal vision and all H1 CVD conditions,
including CAM02-UCS. Filled-field bins use adjacent separation; data marks use
all pairs and background contrast. Diverging selections compare actual
opposite classes at their selected radii, including their lightness/distance
balance. Even counts omit the center; odd counts include it once.

This is a deliberate extension from H1's odd reference-table evaluation:
rounding an abstract 25% arm radius to the neutral in a short discrete table
would test the neutral against itself. H2 tests **actual opposite classes**
and excludes the shared center from arm-separation tests. The frozen H1
baseline and its published results are preserved.

Every count below each prepared curve's arc-length bound has cached screening
for both contexts; any count beyond that bound is immediately rejected.
Prepared sampling therefore never requires optional audit packages. An
unknown custom recipe runs basic screens locally and needs the optional
CAM02-UCS dependency if it survives them. Counts are not assumed to pass monotonically: different
even/odd samples can expose different arm ambiguities. A failed count raises
`QualityError` with its immutable measured report; colors are never dropped.

`ConstraintConflictError` has a narrower mathematical basis: if
`(n-1)*required_adjacent_distance` exceeds a Bernstein derivative upper bound
on this fixed curve's Oklab arc length, that particular bin request cannot
satisfy the floating-point distance rule. The bound applies to this curve and
profile, not all possible designs. `SearchExhaustedError` instead means no
passing candidate was found in the stated budget and explicitly does not
claim infeasibility. Invalid input raises `ValueError` before optional loading.

## Serialization and evidence

Recipes are finite, schema-checked JSON data with a SHA-256 fingerprint;
there is no executable payload or object deserialization. Recognized prepared
recipe geometry loads its independently bundled evidence and ignores any
substituted report claims. Unknown recipes are numerically certified and
re-screened with design dependencies by default. For lightweight inspection,
`load_recipe(data, validate=False)` permits sampling a numerically certified
unknown path but labels its screening status **unvalidated**. Serialized
pass/fail claims alone cannot approve it.

Every result retains the algorithm/profile versions, recipe identity, measured
criteria, center/arm and independent-space audits, supplied-color changes,
source dependency versions and numerical limitations. `approved_default`
remains false until the later review stage.

## Reproduction

```powershell
uv sync --locked --extra design --extra research
uv run --locked --extra design --extra research pytest
uv run --locked --extra design --extra research python tools/build_ordered.py --check
# Intentionally regenerate experimental data and review figures:
uv run --locked --extra design --extra research python tools/build_ordered.py
```

The check reconstructs saved cubic coefficients from construction parameters,
repeats full continuous/grid/dense checks, and repeats every cached discrete
audit. Numeric comparisons use 1e-8 tolerances. The baseline H1 reproduction
check remains independent and unchanged.

## Numerical sources

- [SciPy PCHIP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html)
- [SciPy SLSQP](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)
- [H1 protocol and fixed thresholds](METHODS_H1.md)
- [References and model sources](REFERENCES_H1.md)
