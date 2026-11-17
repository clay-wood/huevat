# Huevat releases

## 0.2 — in development

- Rename the default categorical style to Core, preserving its colors and the
  `clearer` alias. Add Earth and Gem palettes for 2–8 categories on both backgrounds.
- Add cyclic gradients with checked closing pairs and continuous seams.
- Prepare optimized selections for common counts and check nearby alternatives.
- Run custom searches with progress reporting and cancellation.
- Extend Figure doctor with palette comparisons, opt-in filled regions, scalar
  recoloring, paired uncertainty styles and actual-size proof sheets.
- Add a native Julia package with Makie.jl and Plots.jl adapters.

These additions require the current source checkout. New palettes retain
separate visual-review status. The interactive palette editor remains deferred.

## 0.1.0

- Clearer categorical palettes for 2–12 categories.
- Sequential, diverging, multi-hue and Spectral gradients, with light and dark
  variants.
- Eighteen supported gradients for general plots, seismic data, terrain,
  depth and atmospheric fields.
- Matplotlib, Plotly and UltraPlot adapters.
- Evenly spaced sampling and optional optimized color selection.
- Nine-bin default sampling, including the neutral of diverging gradients.
- Named `_r` (reverse), `_d` (dark), and combined suffixes.
- Revised Aerosol, Bathymetry and Thermal routes, plus Cobalt, Copper, Dusk,
  Orchid, Tundra and Verdant. Earlier recipes retain their immutable IDs.
- Figure doctor suggestions for colors, markers and dashes, with previews,
  fixed styles, shared labels and undo.
- JSON designs for reuse, CSV and hex color lists, and CSS gradients.

Requires Python 3.10+. Color selection needs no additional packages; plotting
and custom design use optional extras.

See the [palette gallery](../README.md), [quick start](QUICKSTART.md) and
[plotting examples](../examples/README.md).
