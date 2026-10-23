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

Pilot refinements keep those thresholds unchanged. The final finite grid uses
chroma scales `[1, .9, .8, .7, .675, .65]`; sequential endpoint shifts
`[0, -.0125, .0125, -.025, .025]`, lightness-skew adjustments
`[0, .06, .12, .18, .24, .30, .36]` and four declared endpoint ranges. The
fourth range makes the counterpart background's passing interior range
available; background variants need not have different physical color paths.
Near-black/near-white sequential endpoint chroma is deliberately tapered to
20% of the interior envelope. The 65% search floor applies to this declared
background envelope, rather than to those untapered endpoint controls.

Diverging variants use three endpoint shifts, two lightness ranges/skews,
arm strength ratios `[1, .85, 1.15]` and differential lightness offsets
`[0, -.01, .01, -.0175, .0175]`. Offsets grow with the declared first or second
power of arm radius; the Hermite center derivative remains zero. Light centers/endpoints are .965/.38 or
.98/.42; dark centers/endpoints are .12/.86 or .19/.80, before endpoint shifts.
The source records the exact sequential ranges, hues and chroma controls.
Dark endpoint chroma tapers are route-specific for gamut and arm balance.
Estuary's plum arm and Thermal's rose endpoint were refined after pilot
failures. Retained rejection records describe the final declared search;
the original controls remain in protocol commit `5c101d3`.

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

## Delivered interface and reproduction

```python
import huevat as hv
from huevat.adapters import matplotlib as hmpl

names = hv.gradient_names(domain="geography")
info = hv.gradient_info("bathymetry")
g = hv.gradient("bathymetry", background="light")
restored = hv.load_recipe(g.to_json())
cmap = hmpl.colormap(g)
```

`gradient_names` accepts `family="sequential"`/`"diverging"` and domains
`general`, `seismic`, `structure`, `geography` and `atmosphere`. Names and
immutable metadata describe screened experimental candidates, not an automatic
recommendation for arbitrary data. `gradient` supports the two declared
backgrounds and preserves normal reversal, sampling, adapters and serialization.
Use the existing constructors for custom backgrounds or preferences.

Prepared canonical paths reuse the H2 cubic representation and have new
`h4b-{name}-{background}-v1` IDs. Known recipe hashes reload from shipped
evidence without optional packages; forged evidence is ignored. Modified
recipes get full independent validation by default or explicitly unvalidated
inspection with `validate=False`. Earlier H0–H4a paths/recipes remain intact.
The H4a manifest updates only its public-import fingerprint for the added lazy
catalog exports; its samplers, numerical evidence and figures remain unchanged.

Fourteen context/count combinations per variant retain both passing and failing
uniform selections (counts 2, 3, 5, 7, 8, 9 and 11). `known_counts` lists the
prepared passing uniform counts; `optimized_discrete` remains an explicit
alternative. The optimized positions do not define physical class boundaries.

Full rejected search trials are retained in
`research/collection-v1/construction.json.gz`, separate from the lightweight
runtime resource. Runtime reports retain construction parameters, search
statistics and the reference to that evidence. Numerical reports make no
claim that field semantics, hillshade or human readability were validated.

```powershell
uv run --locked --all-extras python tools/build_collection.py --check
uv run --locked --all-extras python tools/build_collection.py
uv run --locked --all-extras python tools/build_collection.py --construct
```

The checker rebuilds each path from its recorded controls (numeric comparison
within 1e-8 across platforms; retained recipe/resource bytes remain hash-checked), independently
repeats its full audit and every prepared discrete report, reproduces bad
controls and verifies source/resource/gallery hashes. Re-rendering is separate
from checks because raster bytes need not match across graphics environments.
All application fields are deterministic synthetic arrays in
`tools/collection_fields.py`; scientific units and boundaries are explicit
illustration conventions. The local HTML has filters without external assets.
