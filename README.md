# Huevat

Huevat is an independent Python library under development for constrained
scientific palettes and gradients. **H0 supplies the numerical foundation.**
Palette generation, approved defaults, quality profiles, and the gallery remain
later milestones in [project_plan.md](project_plan.md).

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

`simulate` supports Machado severity 100 for `protan`, `deutan`, and `tritan`.
It applies matrices in linear sRGB, then clips simulated display output.
Intermediate severities and independent-space audits belong to H1.
Distances and simulated vision are screening tools, with no universal
distinguishability guarantee.

See [provenance](docs/PROVENANCE.md) for source versions, hashes, numerical
conventions, and licensing; see [technical status](docs/TECHNICAL_STATUS.md)
for milestone evidence and limits.
