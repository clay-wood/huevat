# Figure doctor

Improve an existing line or scatter figure with coordinated colors, markers
and dashes. Matplotlib, Plotly and UltraPlot are supported.

| Before | After |
| --- | --- |
| ![Original figure](../research/doctor-v1/matplotlib-light-before.png) | ![Suggested colors, markers and dashes](../research/doctor-v1/matplotlib-light-separation.png) |

## Compare suggestions

Install from PyPI with `python -m pip install "huevat[design,matplotlib]"`.
Replace `matplotlib` with `plotly` or `ultraplot` for those libraries.

```python
from huevat import doctor

scene = doctor.inspect(fig)
closer, separation, simple = doctor.propose(scene)
preview = doctor.preview(fig, separation)
gray = doctor.preview(fig, separation, condition="grayscale")

change = doctor.apply(fig, separation)
change.undo()
```

- **Closer** keeps more of the original color appearance.
- **Separation** prioritizes series that cross or run close together.
- **Simple** uses fewer additional markers and dashes.

Suggestions can be similar when the same choice works best for the figure.
Preview creates a copy. For Matplotlib and UltraPlot, save it with
`preview.savefig("preview.png")` or display it in a notebook. For Plotly, use
`preview.show()`. `apply` changes the original figure; `undo` restores the
previous styles and checks for changes made since the suggestion was applied.

## Keep specific colors or styles

```python
options = doctor.propose(scene, locked={
    "Reference": {"color": "#4379a3"},
    "Treatment": {"marker": "square", "dash": "dash"},
})
```

Fixed styles stay exact. If they prevent colors from passing the checks, the
report says so. Markers and dashes can still help readers follow the series.

## Keep labels consistent across figures

```python
next_scene = doctor.inspect(next_fig)
next_options = doctor.propose(next_scene, assignments=separation.assignments)
```

The same label keeps its style when series are reordered or temporarily absent.
Use consistent, unique labels for categories you want to match.

## Check and save a suggestion

```python
print(separation.report["color_screen_pass"])
gray = doctor.preview(fig, separation, condition="grayscale")
simulated = doctor.preview(fig, separation, condition="deutan-100")

saved_json = separation.to_json()
restored = doctor.load_proposal(saved_json)
```

A saved suggestion applies to the same figure data and settings. Use its
`.assignments` to carry styles to a different figure.

## Supported figures

Figure doctor edits ordinary Cartesian lines and scatter series with uniform
colors. It supports repeated labels across panels and respects each panel's
background. Images, colorbars, uncertainty bands and unsupported plot types
are kept as they are. Plotly works best with explicit numeric coordinates,
trace modes and colors. Not every legend or custom artist can be updated.

Color checks cover the supported marks. They do not assess the whole figure;
crossing detection can miss small features. Review the preview at the intended
figure size. The [methods notes](METHODS_H4C.md) give detailed coverage.

## Compare different palettes

Pass `palette="earth"`, `palette="gem"`, or a checked Huevat palette to
`doctor.propose`. With `palettes=("core", "earth", "gem")`, it compares the
sets and chooses a candidate for each of the three suggestions. Fixed styles
and saved assignments still take priority. `palette="custom"` searches for a
new palette near the figure's original colors and can fail its color checks.

## Filled bars, regions and uncertainty bands

Use `scene = doctor.inspect(fig, fills=True)` to include uniform Matplotlib
and UltraPlot bars, patches and filled bands. Plotly supports vertical bars
and explicitly colored filled scatter traces on the primary Cartesian axes.
The same label can connect a line with its uncertainty band. Data, geometry
and transparency are preserved. Filled regions use the filled-field color
checks; overlapping layers and shading are still outside those checks.

`doctor.band_styles(palette, labels, alpha=.2)` returns paired `color`, `fill`
and `edge` choices under `["styles"]`, plus a color-check report. Pale
fills may fail separation checks even when their lines pass; the report keeps
that distinction. See the [runnable example](../examples/advanced.py).

## Recolor a scalar field

`doctor.fields(fig)` lists supported images, heatmaps and scalar collections.
`doctor.field_preview(fig, gradient, center=0)` returns a recolored copy.
`change = doctor.recolor(fig, gradient, center=0)` edits the figure;
`change.undo()` restores it.

Existing data limits and normalizers are preserved unless you explicitly
provide new limits or a center. Existing discrete boundaries stay fixed and
their number of colors must pass. Use `keys=[...]` to choose fields from the
list. Plotly supports heatmap/contour traces and shared color axes; all fields
sharing an axis must be selected together. Supply an explicit center for a
signed Plotly field. Data and missing-value masks are preserved.

## Export a proof sheet

```python
doctor.proof_sheet(fig, "proof.pdf", width_mm=85, dpi=200)
```

This saves normal, simulated deuteranopia and grayscale views, with each panel
at the requested figure width. Individual PNGs and a short settings file are
saved beside the combined PNG/PDF. Other supported conditions can be supplied
with `conditions=(...)`. Simulations transform the entire rendered image,
including colorbars and fills. The original figure and plotting settings are
unchanged. Plotly proofs need `python -m pip install ".[proof]"` and Chrome or
another Kaleido-supported browser. These previews support visual review;
they do not certify readability.
