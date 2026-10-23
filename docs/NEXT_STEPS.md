# Next implementation requirements

Updated October 23, 2026. This document records the user's approved direction
after the Clearer H3 revision. It is an implementation specification; the
interfaces and features described below are not yet implemented.

## Approved scope and design direction

- Figure doctor combines diagnostics, coordinated color/marker/dash design,
  figure-aware assignment and palette negotiation in one workflow.
- Optimized discrete sampling is an explicit, audited alternative to uniform
  sampling.
- Matplotlib, Plotly and UltraPlot adapters are all required.
- Expand general sequential and diverging defaults, and develop aesthetically
  considered options for geosciences/geography and atmospheric science.
- Use ColorCET and Scientific colour maps as attributed comparisons and
  methodological references. The user appreciates Crameri's work and gallery
  but does not generally prefer those map aesthetics. Do not treat batlow or
  another published scheme as an automatic aesthetic target.
- Preserve the selected Clearer categorical style, all frozen numerical
  thresholds, historical recipes and the dependency-free plotting core.

## H4a: adapters and optimized discrete sampling

### One shared color contract, three real backends

Adapters should accept Huevat gradients/palettes and a common specification:
source recipe/identifier, normalization, center, category order, background,
missing value and under/over-range policy. Return backend-native objects plus
source metadata and measured approximation error. Keep registration explicit
and namespaced. Never alter global defaults on import.

| Backend | Required output/use | Specific acceptance tests |
| --- | --- | --- |
| Matplotlib | Colormap, categorical property cycle and explicit normalizer/boundary mapping | Images, scatter, lines, contours and colorbars; masks/NaNs; reversal; actual neutral value and unequal signed ranges |
| Plotly | Continuous scale stops, discrete sequence/map and category order; trace/layout/coloraxis mapping | Rendered and serialized examples; midpoint/range consistency across traces; null data; explicit policy for unsupported under/over colors |
| UltraPlot | Native continuous/discrete colormaps and property cycles with explicit normalization | Verify continuous versus qualitative classification, `Cycle` behavior, discrete contour/pcolor levels, colorbars and no accidental re-interpolation in another color space |

The adapters approximate the delivered Huevat path, not merely its endpoints.
Use enough lookup samples/stops to meet a stated tolerance, checking the result
against the original sampler on a denser grid. Test simulated/quantized output
when the export changes encoding. Tolerance failures must be visible. Backend
limits should be documented rather than silently reinterpreting the source.

Install each backend through its own optional extra and test actual supported
versions. A Matplotlib-compatible object alone does not establish UltraPlot
compatibility. The UltraPlot docs expose separate continuous/discrete classes
and property cycles, making classification and normalization meaningful parts
of the adapter contract.

Proposed module layout (not committed API):

```python
from huevat.adapters import matplotlib as hmpl
from huevat.adapters import plotly as hplotly
from huevat.adapters import ultraplot as huplt
```

Prefer a small common API vocabulary; keep backend-specific settings explicit.
Do not put NumPy, plotting libraries or browsers in the base dependency set.

### Optimized sampling has explicit positions

Keep `.discrete(n)` uniform for compatibility. A proposed explicit alternative
is `.discrete(n, spacing="optimized")`, with generation budgets separate from
ordinary prepared lookup. The exact public shape should be settled during H4a.

Required returned data: immutable colors, selected normalized positions,
source identity/hash, spacing algorithm/version and the count-specific report.
Positions are representative sample locations, not physical class boundaries.
Any conversion to data bins must be explicit and include the chosen boundaries.
Do not change precipitation thresholds, geological classes or data normalization
merely to improve perceptual spacing.

For sequential paths, retain order and declare the endpoint policy. For
diverging/Spectral paths, preserve the reference center, arm correspondence and
even/odd center policy. Search positions on the existing path; do not deform
that path or silently move its neutral. Validate float/u8, every condition,
Oklab/CAM02-UCS, context, distinctness and applicable arm criteria on the exact
returned selection.

An initial deterministic grid search can reuse precomputed condition-space
coordinates. Adjacent-distance filled-field constraints may admit dynamic
programming; data-mark all-pair constraints need an appropriate all-pair search,
not an adjacent-only shortcut. A failed finite search is not proof that no
continuous selection exists. Preserve explicit fixed-path count-conflict bounds.
Return the best failed criteria and nearby known passing counts when useful.

Acceptance: include cases where uniform sampling fails but optimized selection
passes, cases where it still fails honestly, repeatable completed searches,
zero-centered asymmetric data examples, reversal/serialization and unchanged
uniform results. Cache prepared optimized selections separately by algorithm,
profile, context and count.

## H4b: a broader gradient collection

Start with approximately 10–14 independent candidate paths, selected for
coverage and appearance rather than a large name count. Reversals and alternate
backgrounds are variants, not extra independent designs. Review alternatives
before adopting new immutable defaults.

Proposed aesthetic directions, not promises of passing designs:

| Collection | Hue-route directions | Purpose |
| --- | --- | --- |
| General sequential | Ink–blue–ice; navy–teal–mint; plum–rose–sand; charcoal–amber–cream | Several restrained and more colorful monotone options |
| General diverging | Blue–neutral–coral; teal–neutral–plum; indigo–neutral–ochre | Several balanced signed options, each with appropriate light/dark variants |
| Seismic amplitudes | Ink/coral and indigo/amber alternatives around a declared zero | Resolve both polarities, thin beds and weak reflectors without inventing boundaries |
| Structural properties | Cool mineral and warm mineral sequential routes | Velocity, impedance, density and other ordered property fields |
| Bathymetry/topography | Deep-water blues and lowland–ochre–stone alternatives | Meaningful depth/elevation readings and an explicit sea-level policy |
| Atmosphere | Blue–teal moisture; plum–amber magnitude; cool/warm anomaly routes | Moisture/concentration/magnitude versus signed anomalies |

These directions should share Huevat's controlled visual weight and smooth
transitions. They should not be arbitrary recolorings of one spine presented as
many distinct defaults. At least some routes must be allowed enough shape
freedom to produce genuinely different useful appearances.

### Match map families to physical meaning

- Signed seismic amplitudes are diverging with explicit polarity/reference;
  velocity/density/impedance are sequential. Evaluate on synthetic dipping
  reflectors, a fault offset and thin-bed/wavelet features; include wiggle traces
  and raster sections. Depth-axis reversal must not silently reverse polarity.
- Topography/bathymetry needs units, sea level, separate land/water extents and
  a missing-data policy. A piecewise geographic/sea-level scale is not
  automatically a balanced anomaly diverger. If a semantic shoreline or
  different branch profile is introduced, declare a separate versioned protocol
  before optimizing. Hillshade changes displayed colors; review composited
  shading as a separate use case, not evidence of the unshaded map's quality.
- Atmospheric magnitudes/concentrations use sequential scales; anomalies and
  signed components use diverging scales. Preserve physical threshold levels
  and explicit linear/log/other normalization. Distinguish no signal from
  missing data. Wind direction/phase needs cyclic endpoint/seam criteria;
  introduce that family through a new protocol rather than an ordered profile.

The application gallery should show each candidate on identical representative
fields, with scalar legends and actual units/reference values. Include both
backgrounds, CVD/grayscale, known weak spatial features and deliberately bad
controls. Keep standard diagnostics, but add realistic seismic, elevation and
atmospheric views. A visually attractive overview should lead to complete
method/version/count details rather than an unsupported universal ranking.

## H4c: one figure-doctor workflow

The workflow is **inspect → propose → preview → explicitly apply**.

1. Extract a backend-neutral figure description: series/labels, actual displayed
   colors and alpha, backgrounds, markers, line/dash/width settings, axes/data
   scales, color mappings and visible relationships. Start with supported
   Matplotlib/UltraPlot artists, then Plotly traces. Report unsupported coverage.
2. Diagnose the relevant normal/CVD/grayscale distinctions and actual composite
   colors. Distinguish numerical color screens from multichannel readability.
   Complex unmodeled layering cannot silently receive a full pass.
3. Propose coordinated color, marker and dash assignments, retaining stable
   category identities and explicit locked preferences. Optimize extra
   separation for crossing/overlapping series or neighboring regions while
   retaining the selected baseline gates. Do not alter data, scales, units,
   physical thresholds, sign conventions or category meaning.
4. Offer a small set of passing tradeoffs: closer to the user's colors, more
   separation, or lower encoding complexity. Show the actual plot under normal
   and simulated conditions. Expose which requirements are met and which colors
   changed. Keep aesthetic choice with the user.
5. Return reproducible proposals and an explicit application operation. Inspection
   and previews must leave the original figure untouched. Include before/after
   metadata and an undo/copy policy. Applying unsupported edits should fail
   clearly rather than change unrelated artists.

Acceptance includes repeated labels across panels, absent/reordered categories,
locked colors, crossing lines, transparent uncertainty bands, colorbars and
unsupported artist types. A failed color-only palette may receive a useful
marker/dash repair, but must retain its failed color-only status.

## H4d: adoption and release checks

Adopt only reviewed default IDs and keep old recipes loadable. Include concise
summaries, palette/count discovery, compact exports, adapter examples, clean
installations, optional-import checks, reproducible methods and migration notes.
Reduce runtime evidence copying/loading as needed for interactive previews,
without discarding independent audits or weakening their thresholds.

## Primary references consulted

- [ColorCET user guide](https://www.colorcet.com/userguide/index.html): distinctions
  among sequential, diverging, cyclic and relief-shading use cases.
- [Scientific colour maps](https://www.fabiocrameri.ch/colourmaps/) and
  [batlow](https://www.fabiocrameri.ch/batlow/): versioned diagnostics and a
  comparative design/gallery reference, not a required Huevat aesthetic.
- [UltraPlot colormaps](https://ultraplot.readthedocs.io/en/stable/colormaps.html),
  [cycles](https://ultraplot.readthedocs.io/en/stable/cycles.html), and
  [ContinuousColormap](https://ultraplot.readthedocs.io/en/stable/api/ultraplot.colors.ContinuousColormap.html):
  native backend behavior to verify during adapter implementation.
- [Plotly continuous scales](https://plotly.com/python/colorscales/): shared
  ranges and reference/midpoint behavior to test explicitly.
