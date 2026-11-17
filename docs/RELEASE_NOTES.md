# Huevat 0.1.0

- Core categorical palettes for 2–12 categories; `clearer` remains an alias.
- Earth and Gem alternatives for 2–8 categories on both backgrounds.
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
- Cyclic gradients for phase and directions, with checked periodic sampling.
- Prepared optimized selections, nearby-count searches and cancellable custom
  generation with progress reporting.
- Optional filled-region repairs, comparisons across palette sets, scalar
  recoloring, paired uncertainty styles and actual-size proof sheets.
- A native Julia package with Makie.jl and Plots.jl adapters.

Requires Python 3.10+. Color selection needs no additional packages; plotting
and custom design use optional extras.

See the [palette gallery](../README.md), [quick start](QUICKSTART.md) and
[plotting examples](../examples/README.md).
