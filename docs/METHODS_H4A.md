# H4a: plotting adapters and optimized discrete sampling

Implemented October 23, 2026. The existing H0–H3 numerical implementations,
prepared designs and uniform `.discrete(n)` behavior remain frozen. This pass
adds explicit sampling and optional plotting adapters. Expanded gradients and
figure doctor are described in [collection methods](METHODS_H4B.md) and the
[figure doctor guide](FIGURE_DOCTOR.md).

The October 25 README/gallery revision uses the default `g.discrete()`
nine-color selection. Its central physical bin is −0.1 to +0.1, including zero
in the neutral class. Displayed fields are complete synthetic arrays; the
artificial corner mask is restricted to backend checks. Explicit optimized
eight-color examples remain in the numerical evidence as an optional workflow.

## Installation and public interface

Install the backend you use, plus `design` when optimizing sample positions:

```powershell
python -m pip install ".[design,matplotlib]"
python -m pip install ".[design,plotly]"
python -m pip install ".[design,ultraplot]"
# Complete development/reproduction environment:
uv sync --locked --all-extras
uv run --locked --all-extras pytest
uv run --locked --all-extras python tools/build_adapters.py --check
```

The backend extras are independent. Importing Huevat or its adapter modules
does not import a plotting library, change plotting defaults or register maps.
Invoking an UltraPlot constructor initializes UltraPlot itself, including its
own configuration/registry behavior. No browser is required for the package or
the numerical tests. The lockfile records the exact development versions.

```python
import huevat as hv
from huevat.adapters import matplotlib as hmpl
from huevat.adapters import plotly as hplotly
from huevat.adapters import ultraplot as huplt

g = hv.diverging()
p = hv.optimized_discrete(g, 8)  # Requires huevat[design].
print(p.colors, p.positions, p.report.screen_pass)
restored = hv.load_recipe(p.to_json())  # Independently reaudits the selection.
print(hv.summarize(p))                 # Small status view, no detailed-report copy.
print(hv.known_counts(g))               # Prepared passing uniform counts only.
```

## Sampling contract and search

`optimized_discrete(gradient, n, context=None, grid=257, max_seconds=10)` searches
an odd grid of 33–1025 candidates on the existing path. It retains endpoints
and order. Diverging and Spectral selections use mirrored positions, matched
arms and the exact center for odd counts; even counts omit that center.
`context` defaults to the source context. Colors, positions, source envelope
and report are immutable. Positions are representative locations on the color
path. **They are not data class boundaries.**

For each candidate, the search precomputes floating and 8-bit normal/CVD
Oklab and CAM02-UCS coordinates for all eight frozen conditions. Pair scores
are the weakest distance divided by its applicable H1 threshold. Filled fields
maximize their weakest adjacent score by dynamic programming on this finite
grid. Data marks use all-pair compatibility search with mandatory endpoints,
then bounded threshold refinement. Diverging searches also enforce opposite
arm separation, lightness balance and relative center-distance balance. Data
marks require background contrast for both encodings.

Every returned selection receives a separate exact-selection audit through the
existing H2 discrete screen, with additional selected lightness-order checks.
This includes all conditions, both encodings, Oklab, independent CAM02-UCS,
8-bit uniqueness, context and applicable arm gates. No threshold was relaxed.
The light diverging eight-color uniform selection fails; optimized positions
produce a passing eight-color selection on the same path.

Completed searches are deterministic. The time budget is cooperative: a
coordinate-conversion or array operation may finish after the deadline, and
the final audit always runs for a retained candidate. A timed-out search can
return a previously found passing selection and records the deadline. An
unsuccessful finite search raises `SearchExhaustedError`, with no claim of
continuous infeasibility. The normal-view Oklab path-length upper bound can
prove a count conflict on that fixed path; it raises `ConstraintConflictError`
before importing optional dependencies. This is not a global palette limit.

The `h4-sampling-v1` recipe stores source, exact positions and context; its hash
excludes replaceable evidence and elapsed time. Imported evidence is never
trusted. Default loading revalidates source and selection. `validate=False`
permits standard-library-only inspection with `screen_pass=False`. Reversal
reverses colors/source, transforms positions and reindexes invariant evidence.
Optimized results are generated on request and can be saved as recipes; this
pass does not add a prepared optimized-selection cache or nearby-count search.
`known_counts` does not search or imply failure for unlisted counts. It verifies
the cached passing uniform colors against the source and requires no optional
packages. `summarize` reports context, family, background, count and screening
status without copying the full report.

## Matplotlib and UltraPlot

```python
import matplotlib.pyplot as plt

cmap = hmpl.colormap(g, bad="#b0b0b0", under="#173149", over="#773e32")
norm = hmpl.normalizer(-2, 8, center=0)
fig, ax = plt.subplots()
im = ax.imshow([[-2, -1, 0], [1, 4, 8]], cmap=cmap, norm=norm)
fig.colorbar(im, ax=ax)
```

`normalizer` supplies `Normalize` or `TwoSlopeNorm`: an asymmetric physical
range still places the declared center at path position .5. Bounds are finite
and explicit; a center must lie strictly inside them. Missing and under/over
colors are explicit options on `colormap`; defaults are gray missing values
and endpoint colors outside the range. Linear normalization can clip;
centered normalization keeps under/over behavior explicit.

Matplotlib gradients use dense `ListedColormap` lookup tables. UltraPlot uses
its native `ContinuousColormap` for gradients and `DiscreteColormap` for
palettes. Set `discrete=False` for continuous UltraPlot images/pcolor when its
automatic level handling would otherwise discretize the data:

```python
import ultraplot as uplt

fig, ax = uplt.subplots()
im = ax.pcolormesh([[-2, -1, 0], [1, 4, 8]], cmap=huplt.colormap(g),
                   norm=huplt.normalizer(-2, 8, center=0), discrete=False)
fig.colorbar(im, loc="r")
```

For an explicitly binned display, provide **n+1 physical boundaries** for n
colors. No adapter derives these boundaries from optimized positions:

```python
edges = [-2, -1.5, -1, -.5, 0, 1, 2, 4, 8]
cmap = hmpl.colormap(p)
norm = hmpl.boundary_normalizer(p, edges)
# Use cmap/norm with pcolormesh, or contourf(..., levels=edges).
```

BoundaryNorm uses left-closed/right-open interior bins; the final upper edge
uses its over-range index. With default over color this still shows the final
color. Explicit under/over colors can distinguish out-of-range values.
Contour plots should receive the same explicit `levels`. Alpha, compositing,
interpolation across image pixels and backend resampling can alter the display
and are not revalidated by these adapters.

`cycle(palette, markers=None, linestyles=None)` creates a native property cycle.
Provided marker/dash sequences must contain one entry per color. This pass
preserves your specified coordination; automatic coordinated design belongs to
figure doctor. `color_map(palette, names)` requires unique labels in the desired
order. `hmpl.register(cmap, name=...)` is an explicit action and rejects existing
names, including when UltraPlot has replaced Matplotlib's registry behavior.

## Plotly

```python
import plotly.graph_objects as go

axis = hplotly.coloraxis(g, -2, 8, center=0)
fig = go.Figure(go.Heatmap(z=[[-2, None, 0], [1, 4, 8]], coloraxis="coloraxis"))
fig.update_layout(coloraxis=axis)
# Other traces can share coloraxis="coloraxis".
```

`colorscale(g)` supplies floating encoded-sRGB stops. `coloraxis` supplies an
explicit range and warps those stop positions so the source neutral is at the
requested physical center. It does not rely on `cmid` with manually fixed
limits. Data remain in their original units. `discrete_coloraxis(p, edges)`
creates a step scale at explicit physical boundaries. Exact step-boundary
ownership follows Plotly's renderer; avoid placing class representatives on
interior edges if boundary equality matters.

Plotly clamps under/over values to endpoint colors. Independent special colors
are unsupported here; missing values use native null/gap behavior. These
policies are recorded in the returned object's `huevat_report` attribute,
separately from valid Plotly JSON. Native Plotly copies/serialization discard
that attribute: retain or export it separately when evidence is needed.

For categorical Plotly Express figures, use
`color_discrete_map=hplotly.color_map(palette, names)` and
`category_orders={"category_column": names}`. `sequence(palette)` also supplies
a native color list. Explicit labels prevent data reordering from changing
category colors. Symbols and dashes can be assigned through Plotly's own
symbol/dash maps; those use different names than Matplotlib styles.

## Approximation evidence and limits

Continuous adapters audit the actual exported lookup object or formatted RGB
stops against the source sampler. Default Oklab tolerance is .002. Matplotlib
and UltraPlot start with 1025 lookup samples (cap 16385); Plotly starts with
257 stops (cap 4097). Counts must be odd to retain the exact center. Failed
audits increase sample count up to the cap, then raise `QualityError`.

Evidence includes at least 8193 normal-view sample positions and at least a 1021-position
grid for every simulated condition in both floating and quantized display
encodings. The condition grid avoids alignment with the default lookup knots,
which would conceal lookup approximation errors. The tolerance gates floating
normal/CVD error. Quantized errors are
reported separately: independent 8-bit rounding has its own error floor.
These are finite-grid approximation measurements, not proofs of continuous
error bounds or a fresh H1 approval of the rendered figure. Reports explicitly
set `adapter_profile_revalidated=False`. Mutating a scale or colormap invalidates
its evidence. Discrete adapters preserve the exact exported hex colors.

The [offline gallery](../research/adapters-v1/index.html) contains native figures,
a local interactive Plotly example, selected positions, errors, source hashes
and locked backend versions. `tools/build_adapters.py --check` reaudits retained
recipes and native exports, checks source/gallery hashes and renders backend
smoke figures. It does not demand identical raster bytes across platforms.
The rendered PNGs were visually checked. Plotly's native figures and serialized
configuration were tested; interactive browser inspection of the local HTML
was blocked by the browser tool's file-URL policy.
