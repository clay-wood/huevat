# Huevat 0.1.0

Private source release, October 23, 2026. This completes the scoped first
implementation: the existing defaults remain, new named routes remain
experimental, and no package/public release has been published.

- All construction families: categorical Clearer and retained original style,
  sequential/diverging, multi-hue and Spectral-like paths.
- Twelve additional named routes for general plots, seismic/subsurface,
  geography and atmosphere, with light/dark variants and explicit status.
- Native Matplotlib, Plotly and UltraPlot adapters; explicit normalization,
  signed centers, boundaries and missing/out-of-range policies.
- Explicit optimized discrete sampling with exact positions and count-specific
  audit; uniform sampling remains unchanged.
- Figure doctor: supported Cartesian line/scatter inspection, three coordinated
  color/marker/dash tradeoffs, stable labels, locks, native copied previews and
  explicit transactional apply with guarded undo.
- Small discovery registry with 76 immutable IDs: 30 retained default variants,
  22 legacy categorical variants and 24 experimental collection variants.
- Compact hashed JSON exchange, exact CSV/hex tables and audited sRGB CSS
  gradients. Labels and selected positions retain their provenance.
- Prepared-count advice, cached ID lookup, usage/migration guides, runnable
  examples and reproducible offline review artifacts.

Numerical screens remain the provisional H1 model criteria. They do not certify
universal human readability or replace appearance review at the intended size.
Frozen evidence and old recipes remain loadable. Continuous exports/adapters
retain finite-grid approximation limits; Plotly browser rendering and local
gallery interaction have not been exercised by browser automation.

The base package requires Python 3.10+ and has no runtime dependencies. Optional
extras remain `design`, `research`, `matplotlib`, `plotly`, `ultraplot`.
See [quick start](QUICKSTART.md), [API](API.md), [migration](MIGRATION.md),
[verification status](TECHNICAL_STATUS.md) and the
[release overview](../research/release-v1/index.html).

Verification: 301 local tests and all eight Windows/Linux CI jobs passed at
`33891a5`, including clean offline installs, every earlier evidence check,
compact export/immutable-ID reproduction and the three native examples:
[v0.1.0 validation](https://github.com/clay-wood/huevat/actions/runs/40033917895).

Remaining research/extension work is explicit: human comparative studies and
expanded collection adoption; complex layering, scalar-map/neighboring-region
repairs; cyclic palettes; large-figure audit scaling and lazy historical
evidence storage; optimizer derivatives/progress/cancellation; optional
prepared optimized caches. These are outside the scoped v0.1 release.
