# Quick start

Install from the project folder with your plotting library:

```sh
python -m pip install ".[matplotlib]"
```

Use `plotly` or `ultraplot` instead of `matplotlib` for those libraries.
Python 3.10+ is required. See the [gallery](../README.md) and
[plotting examples](../examples/README.md) to compare the colors.

## Colors for categories

```python
import numpy as np
import matplotlib.pyplot as plt
import huevat as hv
from huevat.adapters import matplotlib as hmpl

labels = ["Control", "A", "B", "C", "D", "E"]
palette = hv.categorical(len(labels))
colors = hmpl.color_map(palette, labels)

x = np.linspace(0, 10, 100)
series_fig, ax = plt.subplots()
for i, label in enumerate(labels):
    ax.plot(x, np.sin(x / 2 + i / 3), color=colors[label], label=label)
ax.legend()
series_fig.savefig("six-series.png", dpi=180)
```

Clearer is the default style, with palettes for 2–12 categories. Changing the
category count can change all the colors. Save your labels with the palette
when you want to use the same colors in another figure.

## Gradients for fields

```python
fig, axes = plt.subplots(1, 2, figsize=(9, 3))
field = np.linspace(0, 1, 120).reshape(10, 12)

ordered = hv.sequential()
axes[0].imshow(field, cmap=hmpl.colormap(ordered), vmin=0, vmax=1)

signed = hv.diverging()
image = axes[1].imshow(10 * field - 2, cmap=hmpl.colormap(signed),
                       norm=hmpl.normalizer(-2, 8, center=0))
fig.colorbar(image, ax=axes[1], label="Anomaly (K)")
fig.savefig("fields.png", dpi=180)
```

The normalizer places zero at the neutral color, even when the range extends
farther in one direction. The other defaults are `hv.multihue()` and
`hv.spectral()`. Pass `background="dark"` to any palette or gradient factory
when plotting on a dark background.

The twelve named alternatives are experimental:

```python
depth = hv.gradient("bathymetry")
print(hv.gradient_names(domain="atmosphere"))
```

Use `.reversed()` to change direction and `.at(0.5)` to read an individual
RGB color. Positions run from 0 to 1.

## Choose separate colors from a gradient

```python
print(hv.known_counts(signed))
print(hv.nearby_counts(signed, 8))
seven_colors = signed.discrete(7)
```

`discrete(n)` samples evenly and checks the requested count. Not every count
passes. With `python -m pip install ".[design,matplotlib]"`, you can also use
`hv.optimized_discrete(signed, 8)` to search for better-spaced colors.
Choose the data-bin boundaries separately from the color sample positions.

## Save and reuse

```python
hv.export(palette, labels=labels).write("palette.json")
saved = hv.load_export(open("palette.json", encoding="utf-8").read())
restored_palette = saved.design
restored_label_map = saved.color_map

hv.export(signed).write("gradient.json")
hv.export(signed, n=7, format="csv").write("seven-colors.csv")
hv.export(palette, format="hex").write("colors.txt")
```

JSON saves the design, labels and any selected positions for reuse. CSV and
hex save color lists. Use `format="css"` for a CSS gradient value.
If you already selected `p = signed.discrete(7)`, use
`hv.export(p, source=signed)` to save its original gradient too.

## Improve an existing figure

Figure doctor needs the `design` extra and your plotting library.

```python
from huevat import doctor

scene = doctor.inspect(series_fig)
closer, separation, simple = doctor.propose(scene)
preview = doctor.preview(series_fig, separation, condition="grayscale")
preview.savefig("preview.png")

change = doctor.apply(series_fig, separation)
change.undo()
```

Figure doctor suggests colors, markers and dashes for line and scatter plots.
It keeps images, colorbars and uncertainty bands as they are. See the
[Figure doctor guide](FIGURE_DOCTOR.md) for fixed colors and shared labels.

Palettes are checked with color-vision simulations. Review your figure at its
intended size, especially when using many categories or overlapping marks.
