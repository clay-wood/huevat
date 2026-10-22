# Huevat

Huevat is an independent Python library under development for constrained
scientific palettes and gradients. **H0 supplies the numerical foundation;
H1 supplies published references, provisional quality profiles and a baseline
study.** Palette generation and approved defaults remain H2-H4 in
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
install .` or install the built wheel. The optional `huevat[design]` extra
reserves NumPy/SciPy for future generation work; H0 does not implement optimizers.

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
