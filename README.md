# Huevat

Scientific palettes, gradients and coordinated figure styles for Python.
**Private v0.1.0** keeps the current defaults, including the user-selected
**Clearer** categorical style. Twelve additional named gradient routes remain
experimental alternatives.

The base package uses only the standard library. Prepared lookup, sampling,
immutable-ID discovery and portable exports need no NumPy, plotting backend or
browser. Custom design and independent audits live in `huevat[design]`.

[Quick start](docs/QUICKSTART.md) · [API](docs/API.md) ·
[Release overview](research/release-v1/index.html) · [Migration](docs/MIGRATION.md)

## Install from this checkout

```powershell
python -m pip install .
# Add the plotting backend you use:
python -m pip install ".[matplotlib]"
python -m pip install ".[plotly]"
python -m pip install ".[ultraplot]"
# Figure doctor and custom generation:
python -m pip install ".[design,matplotlib]"
```

Python 3.10+ is supported. A locally built wheel and source distribution are in
`dist/`; nothing has been published to PyPI or released publicly.

## Choose and plot

```python
import huevat as hv
from huevat.adapters import matplotlib as hmpl

palette = hv.categorical(6, background="light")
gradient = hv.diverging(background="light")
colors = gradient.discrete(7)
cmap = hmpl.colormap(gradient)
norm = hmpl.normalizer(-2, 8, center=0)
# ax.imshow(data, cmap=cmap, norm=norm)
```

All construction families are available: categorical, sequential, diverging,
multi-hue sequential and Spectral-like. Native adapters support **Matplotlib,
Plotly and UltraPlot**, including explicit centers, category mappings and data
boundaries. [Runnable examples](examples/quickstart.py) cover all three.

```python
ids = hv.design_ids(family="sequential", background="light", role="default")
g = hv.get_design(ids[0])                # exact immutable ID; cached lookup
print(hv.design_info(ids[0]))
print(hv.known_counts(g))
print(hv.nearby_counts(g, 8))

hv.gradient_names(domain="atmosphere")
experimental = hv.gradient("thermal")
```

The registry distinguishes 30 retained default variants, 22 legacy categorical
variants and 24 experimental variants of the twelve new routes. Release role
is separate from frozen scientific reports and their human-review flags.

`.discrete(n)` keeps uniform sampling. `hv.optimized_discrete(g, n)` explicitly
searches positions on the same path and audits that selection; it needs
`[design]`. Neither operation invents physical data-bin boundaries.

## Save and reuse

```python
hv.export(palette, labels=["Control", "A", "B", "C", "D", "E"]).write("palette.json")
saved = hv.load_export(open("palette.json", encoding="utf-8").read())
restored_palette, label_map = saved.design, saved.color_map

hv.export(gradient).write("gradient.json")             # exact path recipe
hv.export(gradient, n=7, format="csv").write("bins.csv")
hv.export(palette, format="hex").write("colors.txt")
css = hv.export(gradient, format="css")                # audited sRGB stops
css.write("gradient.css")
```

Compact JSON retains the source version/hash, exact recipe, orientation,
selection and labels without duplicating the large audit history. Import
recovers frozen evidence or independently revalidates unknown designs. CSV/hex
are exact color tables; CSS continuous ramps have measured approximation error.
Old `.to_json()` recipes remain supported. See [API](docs/API.md) for provenance
when exporting an ordinary palette already selected from a gradient.

## Work with an existing figure

```python
from huevat import doctor
scene = doctor.inspect(fig)
closer, separation, simple = doctor.propose(scene)
copy = doctor.preview(fig, separation, condition="grayscale")
change = doctor.apply(fig, separation)  # explicit edit
change.undo()
```

Figure doctor coordinates colors, markers and dashes for supported Cartesian
line/scatter figures. It retains labels across panels, honors hard locks and
saved assignments, previews on native copies and provides guarded undo. Bands,
scalar maps/colorbars and unsupported content are inventoried and preserved.
A failed color screen remains failed when markers/dashes offer redundancy.
[Usage and coverage](docs/FIGURE_DOCTOR.md) · [Before/after gallery](research/doctor-v1/index.html)

## Review and reproduce

- [Release overview and portable examples](research/release-v1/index.html)
- [Geoscience, geography and atmospheric collection](research/collection-v1/index.html)
- [Three plotting backends and optimized sampling](research/adapters-v1/index.html)
- [Original study](research/baseline-v1/index.html), [ordered designs](research/ordered-v1/index.html),
  [categorical revision](research/categorical-v2/index.html)
- [Technical status](docs/TECHNICAL_STATUS.md), [release notes](docs/RELEASE_NOTES.md),
  [project plan](project_plan.md), [provenance](docs/PROVENANCE.md)

Model screens use the frozen H1 normal/CVD Oklab and CAM02-UCS criteria. They
are provisional engineering screens, not universal human-readability
certificates. Continuous exports/adapters retain finite-grid approximation
limits. Experimental collection adoption and human comparative studies remain
separate. Browser rendering/interaction has not been verified by automation.

```powershell
uv sync --locked --all-extras
uv run --locked --all-extras pytest
uv run --locked --all-extras python tools/build_release.py --check
uv build
uv run --locked --all-extras python tools/check_install.py
```

CI repeats the core on Windows/Linux with Python 3.10/3.12/3.14 and actual-backend
research checks on both platforms. Historical data, recipes and numerical
thresholds remain frozen. The source repository remains independent and private.
