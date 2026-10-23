# Huevat 0.1 quick start

From this private checkout:

```powershell
python -m pip install .
# Choose the plotting backend you use:
python -m pip install ".[matplotlib]"
python -m pip install ".[plotly]"
python -m pip install ".[ultraplot]"
# Figure doctor and custom generation also need [design].
python -m pip install ".[design,matplotlib]"
```

The base install has no dependencies. Prepared palettes, gradients, immutable
ID discovery, compact JSON/CSV/hex/CSS exports and known recipe loading work
offline. The local wheel is in `dist/`; no package has been published to PyPI.

## Six series, with stable labels

```python
import numpy as np
import matplotlib.pyplot as plt
import huevat as hv
from huevat.adapters import matplotlib as hmpl

labels = ["Control", "A", "B", "C", "D", "E"]
palette = hv.categorical(len(labels))
colors = hmpl.color_map(palette, labels)
x = np.linspace(0, 10, 100)
fig, ax = plt.subplots()
for i, label in enumerate(labels):
    ax.plot(x, np.sin(x/2+i/3), color=colors[label], label=label)
ax.legend()
fig.savefig("six-series.png", dpi=180)
```

Clearer is the retained categorical default. Changing the category count can
change every color: save the label mapping or use figure doctor's retained
assignments when categories appear/disappear across figures.

## An ordered field and a signed field

```python
fig, axes = plt.subplots(1, 2, figsize=(9, 3))
field = np.linspace(0, 1, 120).reshape(10, 12)
ordered = hv.sequential()
axes[0].imshow(field, cmap=hmpl.colormap(ordered), vmin=0, vmax=1)
signed = hv.diverging()
image = axes[1].imshow(10*field-2, cmap=hmpl.colormap(signed),
                       norm=hmpl.normalizer(-2, 8, center=0))
fig.colorbar(image, ax=axes[1], label="Anomaly (K)")
fig.savefig("fields.png", dpi=180)
```

The explicit normalizer keeps zero at the neutral even though the negative and
positive extents differ. Missing and out-of-range policies are backend-specific;
see [adapter details](METHODS_H4A.md). Data thresholds never follow perceptual
sampling positions automatically.

For Plotly use `huevat.adapters.plotly.coloraxis(gradient, -2, 8, center=0)`
and attach the returned dictionary with `fig.update_layout(coloraxis=...)`.
For UltraPlot use its dedicated adapter and pass `discrete=False` for continuous
`pcolormesh` fields. The runnable example covers all three backends:

```powershell
python examples/quickstart.py --backend matplotlib
python examples/quickstart.py --backend plotly
python examples/quickstart.py --backend ultraplot
```

## Discover exact designs and useful counts

```python
ids = hv.design_ids(family="diverging", background="light", role="default")
info = hv.design_info(ids[0])
same_design = hv.get_design(ids[0])   # cached immutable prepared object
passing = hv.known_counts(same_design)
near_eight = hv.nearby_counts(same_design, 8)  # includes 7 and 9
print(hv.summarize(same_design))
```

Unlisted counts are unknown, not demonstrated failures. `.discrete(n)` retains
uniform sampling; `hv.optimized_discrete(g, n)` explicitly searches sample
positions and needs `[design]`. Exact IDs preserve old colors across releases.

The twelve additional named routes remain experimental:

```python
hv.gradient_names(domain="geography")
depth = hv.gradient("bathymetry")
hv.gradient_info("bathymetry")
```

## Save colors with their provenance

```python
hv.export(palette, labels=labels).write("palette.json")
saved = hv.load_export(open("palette.json", encoding="utf-8").read())
restored_palette = saved.design
restored_label_map = saved.color_map

hv.export(signed).write("signed-gradient.json")  # exact continuous recipe
hv.export(signed, n=7).write("seven-colors.json")
hv.export(signed, n=7, format="csv").write("seven-colors.csv")
hv.export(palette, format="hex").write("colors.txt")
css = hv.export(signed, format="css")
css.write("gradient.css")
print(css.report["maximum_float_error_oklab"])
```

CSV/hex require an explicit passing count when the source is continuous. JSON
is the lossless exchange format. CSV/hex/CSS are display exports, not recipe
files. CSS explicitly requests sRGB interpolation and has a measured finite-grid
error; `.text` is the CSS gradient value to use in a declaration such as
`background: ...`. Discrete CSS gives equal-width swatches, not physical bins.

If you already have `p = g.discrete(7)`, use `hv.export(p, source=g)` for JSON
provenance, or export directly with `hv.export(g, n=7)`. Save positioned palettes
from `optimized_discrete` directly; the JSON retains their exact positions.
Unknown imports need independent validation; `validate=False` is for explicitly
unvalidated inspection. Imported report claims never grant a numerical pass.

## Repair an existing figure

```python
from huevat import doctor
scene = doctor.inspect(fig)
closer, separation, simple = doctor.propose(scene)
preview = doctor.preview(fig, separation, condition="grayscale")
preview.savefig("proof.png")   # original untouched; no hidden pyplot windows
change = doctor.apply(fig, separation)
change.undo()
```

Figure doctor currently edits supported Cartesian lines/scatter. It inventories
and preserves bands, scalar maps/colorbars and unsupported content. Marker/dash
differences do not promote failed color screens. See [coverage and locks](FIGURE_DOCTOR.md).

Start with the [release overview](../research/release-v1/index.html), then browse
the [application collection](../research/collection-v1/index.html) or
[figure doctor comparisons](../research/doctor-v1/index.html). Model screens do
not certify universal human readability; review at your intended figure size.
