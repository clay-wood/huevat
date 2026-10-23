# H4b: named gradient candidates and application review

Protocol declared October 23, 2026, before candidate construction. This pass
adds twelve independent aesthetic routes, with two background variants each.
They remain experimental candidates until the user reviews them. No existing
default or historical recipe is replaced. Categorical Clearer is unchanged.

## Fixed quality criteria

Use the unchanged `h1-screening-v1` filled-field sequential/diverging profiles:
normal vision, protan/deutan severities 50/80/100 and tritan 100, floating and
8-bit encodings, Oklab and independent CAM02-UCS. Retain complete-segment gamut,
C1 continuity and normal-lightness checks, 4097-position CVD ordering, speed,
flat/spike/feature screens, and neutral/balanced diverging-arm criteria.
Count-specific selections are checked separately. Record all rejected searches;
finite search failure does not prove infeasibility. Human appearance review
and numeric screening remain distinct.

No new family-specific threshold is introduced in this pass. Each branch of
the geographic example uses an ordinary sequential profile. The combined
land/water illustration has a declared sea-level boundary and **no combined
balanced-diverger approval claim**. A dedicated geographic scale would need
its own versioned profile. Cyclic phase/wind maps remain outside this pass.

## Independent path construction

Six Oklab control locations have individually specified positions, hue routes,
chroma envelopes and lightness skew. PCHIP coordinate derivatives create C1
cubic Hermite paths. Diverging arms have independently specified chromatic
routes, a common neutral and zero center derivative. They can use different
chroma strengths and small compensating lightness offsets. This permits curve
shapes beyond a rotation/recoloring of one frozen H2/H3 spine.

Search a finite deterministic set of global chroma factors, endpoint lightness
adjustments and arm-balance adjustments, retaining at least 65% of the specified
chroma. Do not clip channels to repair a design. Prefer the closest passing
design to the specified control path. Retain parameters, candidate count,
rejections, numerical versions and source hashes. Construction uses the
optional design stack; prepared named lookup and recipe loading remain
standard-library-only.

The delivered paths reuse the stable `h2-ordered-v1` **cubic recipe encoding**;
the separate construction provenance is `h4b-free-knots-v1`. This does not
assert that the new paths were constructed by the old H2 optimizer. New
identifiers begin `h4b-` and retain version/background. Unknown recipes undergo
the existing full revalidation. Known shipped recipes ignore supplied evidence
and use the hash-checked shipped audit.

## Candidate directions

| Name | Route | Primary examples |
| --- | --- | --- |
| Ink | Indigo–blue–ice | General ordered fields |
| Lagoon | Navy–teal–mint | General fields, atmospheric moisture |
| Rosewood | Plum–rose–sand | General ordered fields |
| Ember | Charcoal–rust–amber–cream | Magnitudes and structural properties |
| Mineral | Slate–violet–blue–pale green | Velocity, density, impedance |
| Bathymetry | Ice–azure–deep navy with increasing depth | Positive water depth |
| Highland | Forest–olive–ochre–stone with increasing elevation | Land above sea level |
| Aerosol | Midnight plum–rose–amber | Atmospheric concentrations/magnitudes |
| Balance | Blue–neutral–coral | Signed fields and seismic polarity |
| Estuary | Green teal–neutral–plum | Anomalies and signed components |
| Strata | Indigo–neutral–ochre | Seismic amplitudes and anomalies |
| Thermal | Slate blue–neutral–rose | Atmospheric anomalies |

Generic sequential variants use a light-background descending-lightness view
and a dark-background ascending-lightness view. Bathymetry always darkens with
increasing positive depth; Highland always lightens with increasing elevation.
These physical conventions remain explicit across backgrounds. Diverging
negative/positive arms do not swap when the depth axis is reversed.

## Application evidence and review

Use synthetic, deterministic data, clearly labeled as illustrations rather
than real observations or a validated forward/inverse model:

- Seismic: dipping reflectors, fault offsets, a pair of thin reflectors and
  weak amplitudes, convolved with a zero-phase Ricker wavelet. Show matched
  raster and wiggle views, trace position, two-way time in seconds, arbitrary
  signed amplitude, frequency and polarity. Reverse the vertical time axis
  without changing scalar color assignment.
- Structure: a smoothly varying velocity field in km/s, interfaces and a weak
  anomaly, with a declared linear physical range.
- Terrain: one elevation field in meters relative to sea level, separate water
  depth (0–4000 m) and land elevation (0–3000 m) mappings, a shoreline and missing
  patch. Show unshaded and separately identified shaded renderings. The shading
  composite is not covered by the unshaded palette report.
- Atmosphere: positive concentration in arbitrary units on explicitly stated
  log scale, moisture in g/kg on a linear scale and temperature anomaly in K
  with an explicit zero. Preserve class thresholds and distinguish zero/no
  signal from missing cells; log scales mask nonpositive values explicitly.

For identical fields/ranges, provide both backgrounds, all eight normal/CVD
conditions, luminance grayscale, scalar colorbars and named candidates.
Retain weak-feature probes, exact count reports and deliberately bad controls
(a hue rainbow, a flat grayscale plateau and a misplaced neutral). Failed
controls must retain their failures. Do not rank models as universally better.

ColorCET and Scientific colour maps inform diagnostics and gallery organization;
no published table or screenshot is copied into the candidate construction.
Primary methodological references:
[ColorCET user guide](https://www.colorcet.com/userguide/index.html),
[Scientific colour maps](https://www.fabiocrameri.ch/colourmaps/), and
[Matplotlib hillshading example](https://matplotlib.org/stable/gallery/specialty_plots/topographic_hillshading.html).
