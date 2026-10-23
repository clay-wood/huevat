# Huevat

Huevat is an independent Python library under development for constrained
scientific palettes and gradients. **H0 supplies the numerical foundation;
H1 supplies published references, provisional quality profiles and a baseline
study; H2 adds sequential/diverging construction; H3 adds count-specific
categorical, multi-hue sequential and Spectral-like construction.**
The categorical default uses the user-selected **Clearer** design. Prepared
designs remain experimental; approved defaults remain H4 in
[project_plan.md](project_plan.md).

The base package uses only the Python standard library. It needs no browser,
renderer, NumPy, SciPy, or plotting package.

## Install and develop

From a checkout with [uv](https://docs.astral.sh/uv/) installed:

```powershell
uv sync --locked
uv run --locked pytest
uv run --locked python tools/check_provenance.py
uv build
uv run --locked python tools/check_install.py
```

`uv.lock` pins the development environment; `.python-version` selects Python
3.12. Python 3.10 or newer is supported. `uv sync --locked --no-dev` installs
only the base package. For an ordinary pip environment, use `python -m pip
install .` or install the built wheel. Install `huevat[design]` for custom
palette/gradient construction and independent audits; normal prepared lookup and
sampling need no optional dependencies.

## Numerical interface

```python
import huevat as hv

rgb = hv.from_hex("#0072b2")
lab = hv.srgb_to_oklab(rgb)
lch = hv.oklab_to_oklch(lab)
mapped = hv.gamut_map((0.65, 0.4, 30))
hex_color = hv.to_hex(mapped)
contrast = hv.contrast(rgb, hv.from_hex("#ffffff"))
protan_display = hv.simulate(rgb, "protan")
```

RGB triples use encoded sRGB channels in [0, 1], Oklab/Oklch use D65 and
lightness on the 0-1 scale, and hue is in degrees. Conversion to sRGB preserves
out-of-gamut results. `gamut_map` reduces chroma at fixed lightness/hue;
`to_hex` rejects out-of-gamut input and rounds to 8-bit channels. Hex input
accepts exactly `#rrggbb`. `distance` takes **Oklab coordinates**.

`simulate` supports Machado severities 0-100 for `protan`, `deutan`, and `tritan`
through the optional `severity=` keyword (default 100).
It applies matrices in linear sRGB, then clips simulated display output.
Distances and simulated vision are screening tools, with no universal
distinguishability guarantee.

## Reference study (H1)

```python
ref = hv.reference("okabe-ito")
colors = ref.colors(8)                 # Exact published values; immutable tuples
path = hv.reference("viridis").sample(257)  # Explicit encoded-sRGB study adaptation
profile = hv.load_profile("filled-fields", "dark")
```

The standard-library base package contains 13 source references and four
versioned context/background profiles. It keeps native count-specific
ColorBrewer tables, the exact Okabe-Ito values, viridis/cividis and representative
ColorCET maps. These are comparison data, with retained attribution and source
hashes. They are not approved Huevat defaults.

Install the separate research tools to evaluate or reproduce the study:

```powershell
uv sync --locked --extra research
uv run --locked --extra research pytest
uv run --locked --extra research python tools/freeze_references.py --check
uv run --locked --extra research python tools/build_baseline.py --check
# Regenerate the offline gallery and machine report:
uv run --locked --extra research python tools/build_baseline.py
```

Open [the offline gallery](research/baseline-v1/index.html) locally. It contains
300-DPI comparisons on both backgrounds, CVD and grayscale panels, discrete
legends, known spatial features, and individual pass/fail reasons. The full
report is compressed JSON; `summary.json` is an uncompressed overview.
Reproduction needs no network once the optional tools are installed.

```python
from huevat.evaluation import evaluate  # Requires huevat[research]
report = evaluate(colors, "categorical", context="data-marks", background="light", encoding="u8")
```

Criteria separate mathematical requirements from provisional engineering
screens. Human review remains explicitly pending. The
[methods protocol](docs/METHODS_H1.md) and thresholds were committed before
baseline evaluation; no palette was changed or threshold relaxed to make it
pass. See [reference provenance](docs/REFERENCES_H1.md) for sources, licenses
and adaptation rules.

See [provenance](docs/PROVENANCE.md) for source versions, hashes, numerical
conventions, and licensing; see [technical status](docs/TECHNICAL_STATUS.md)
for milestone evidence and limits.

## Ordered gradients (H2)

```python
gradient = hv.sequential(color="#0072b2", background="dark")
diverging = hv.diverging(colors=("#0072b2", "#d55e00"), background="light")
rgb = gradient.at(0.35)
colors = diverging.discrete(7)       # Immutable hex-color sequence
reverse = gradient.reversed()
report = gradient.report            # Immutable; report.to_dict() makes a copy
restored = hv.load_recipe(gradient.to_json())
```

The standard preferences load four experimental prepared paths. Each passes
the unchanged H1 float and 8-bit profiles, complete-segment numerical checks,
and a denser CVD ordering audit. They have no accepted H4 default claim.
`discrete(n)` validates that exact selection; even diverging counts omit the
center. Some counts fail although a different count passes. A failed selection
raises `QualityError` with its report and never drops colors.

Custom preferences/backgrounds use optional deterministic SciPy construction:

```powershell
uv sync --locked --extra design --extra research
uv run --locked --extra design --extra research python tools/build_ordered.py --check
```

```python
custom = hv.sequential(color="#0066aa", background="#171d26",
                       seed=4402, starts=2, max_seconds=60)
```

`SearchExhaustedError` means no passing design was found in the stated budget;
it does not prove infeasibility. `ConstraintConflictError` includes an explicit
bound for an excessive count on a particular fixed path. Both carry immutable
reports. Inputs are checked before optional dependency loading.

See the [H2 gallery](research/ordered-v1/index.html) and
[construction methods](docs/METHODS_H2.md) for limits, count-specific results,
serialization rules and measured budgets. Unknown custom recipes are
revalidated by default; `load_recipe(data, validate=False)` permits lightweight
inspection with an explicitly unvalidated screening status.

## Categorical and multi-hue designs (H3)

```python
colors = hv.categorical(6, background="light")
gradient = hv.multihue(background="dark")
signed = hv.spectral(background="light")
colors = signed.discrete(5)  # This exact count is independently screened
restored = hv.load_recipe(signed.to_json())
```

Categorical counts 2–12 on each standard background are independently optimized
Clearer prepared designs. They satisfy the numerical requirements, then preserve
coherent blue/teal/ochre/coral/purple targets. A different count can adjust colors.
Multi-hue sequential
and Spectral-like paths pass the same H1 screens as their H2 counterparts; each
chromatic arm also follows an ordered hue route. Spectral paths have two
multi-hue arms and a shared neutral at `t=.5`.

These lookups, sampling, reversal, cached bin validation and recipe round trips
need only the base package. Custom categorical counts (supported search sizes
2–64), preferences, backgrounds, contexts or search options require `huevat[design]`:

```python
custom = hv.categorical(4, colors=("#0072b2", "#009e73", "#e69f00", "#d55e00"),
                        background="#202a30", starts=2, max_seconds=60)
route = hv.multihue(colors=("#0072b2", "#009e73"), starts=2, max_seconds=60)
```

Supplied colors are adjustable preferences. Reports record every change, all
screening criteria, numerical versions, seed and completed optimizer runs.
Spectral preferences form an even-length sequence: the first half belongs to
the left arm, the second to the right, in traversal order. A search can fail;
it never returns an unapproved candidate as a passing design.

The [H3 gallery](research/families-v1/index.html) includes every prepared count,
matched thin-line/small-marker panels, distance matrices, all screened CVD
conditions, grayscale and known spatial fields on both backgrounds. See
[H3 methods](docs/METHODS_H3.md) for construction limits and reproduction:

```powershell
uv run --locked --extra design --extra research python tools/build_families.py --check
# Re-optimize and regenerate the experimental tables and offline gallery:
uv run --locked --extra design --extra research python tools/build_families.py
```

The user selected **Clearer** after the
[categorical appearance study](research/categorical-aesthetics-v1/index.html).
See the [revised H3 gallery](research/categorical-v2/index.html) and
[Clearer methods and migration notes](docs/METHODS_CATEGORICAL_V2.md).
The original categorical construction remains available explicitly:

```python
current = hv.categorical(6)  # Clearer, h3-categorical-v2
original = hv.categorical(6, style="max-separation")
```

Saved H2/H3 recipes still load with their original colors. New categorical
recipes carry a separate algorithm version and immutable identifier. This
revision preserves all H1 screening thresholds and all H0–H2 implementation/data.

```powershell
uv run --locked --extra design --extra research python tools/build_clearer.py --check
```

The [project review](docs/PROJECT_REVIEW.md) records measured bottlenecks,
usability improvements and proposed features. Reproduce its operational
measurements with `tools/profile_project.py`; raw results are retained in
`research/project-review-v1/benchmarks.json`.

The [next implementation specification](docs/NEXT_STEPS.md) records the
October 23 requirements: required Matplotlib/Plotly/UltraPlot adapters,
optimized discrete sampling, a broader general/seismic/terrain/atmospheric
gradient collection, and an integrated figure doctor. These are planned H4
features; the document distinguishes their proposed API from current behavior.
