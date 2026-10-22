# Categorical appearance study

October 22, 2026. This study responds to the user's rejection of the original
H3 categorical appearance and preference for balanced scientific colors:
blue, teal, ochre, coral and purple. H0–H2 and the multi-hue/Spectral methods
are outside the requested redesign.

## Why the original categorical designs look harsh

The H3 categorical optimizer maximizes the minimum normal/simulated pair
distance over a broad color region. Its admissible chroma reaches .26 and
lightness spans .22–.95 before contrast constraints. This drives designs toward
extremes of saturation, hue and lightness. Supplied preferences are secondary
and can change the maximum minimum distance by only 1e-6. Consequently, they
have little influence over the appearance of the resulting palettes. Passing
the numerical gates does not establish attractive balance or visual approval.

The response should change the construction objective, rather than simply
rerunning that broad search with another random seed.

## Three construction options

1. **Aesthetic targets with constrained adjustment — recommended.** Choose
   coherent blue/teal/ochre/coral/purple targets, require every existing H1
   separation and contrast gate, and minimize movement from the chosen targets.
   This prioritizes the user's aesthetic preference over additional separation
   beyond the accepted floor. It explicitly revises H3's earlier objective
   priority; no H1 acceptance threshold changes.
2. **Maximum separation within a restricted aesthetic region.** Keep the
   auxiliary maximin objective, but use narrower lightness/chroma ranges and
   hue neighborhoods. This retains the original optimization philosophy while
   limiting its appearance. It may still favor boundaries of those ranges.
3. **Interior representatives or curated published palettes.** Clustering an
   admissible color region can produce interior representatives rather than
   maximally repelled extremes. Alternatively, offer exact attributed
   published palettes as opt-in references, with their actual count/background
   audit results. Neither method automatically passes Huevat's unchanged
   profiles; no untested accessibility claim follows from the palette's name.

[iWantHue's theory](https://medialab.github.io/iwanthue/theory/) illustrates
repulsion versus clustering and restriction of lightness/chroma to control
palette appearance. [Seaborn's palette guidance](https://seaborn.pydata.org/tutorial/color_palettes.html)
discusses qualitative hue variation and saturation/intensity balance.
[Paul Tol's qualitative schemes](https://sronpersonalpages.nl/~pault/) provide
curated bright, vibrant and muted alternatives. These are design references;
the candidates here use independently chosen targets, not renamed copies of
those published palettes.

## Implemented candidates

The comparison implements option 1 with three variants of the user's preferred
balanced direction. They share the same semantic color order.

| Variant | Intended appearance | Target chroma multiplier | Oklab chroma cap |
| --- | --- | --- | --- |
| Balanced | Moderate colorfulness and weight; recommended starting point | 1.00 | .155 |
| Softer | More understated, suitable for dense figures | .78 | .125 |
| Clearer | Stronger colorfulness for small marks and thin lines | 1.18 | .180 |

Independent base targets are `#4379a3`, `#348b83`, `#ae883b`, `#bd6c60`,
`#9274a3`, `#5599b4`, `#9b586d`, `#7e8750`. Four-color targets use the first
four; six use the first six; eight use all eight. Each count is optimized
jointly, so a higher-count result is not a truncation of an optimized larger
palette. Dark-background targets increase Oklab lightness by .12 while
preserving the initial chromatic coordinates. Targets are aesthetic preferences,
not necessarily passing colors themselves.

The study searches 3n RGB coordinates and an auxiliary distance z constrained
to .043. Every normal Oklab pair distance divided by two and every simulated
pair distance must reach z. CAM02-UCS pairs must reach 8.3 normally and 4.15
under all seven simulated conditions. Contrast has a .004 luminance safety
margin beyond the applicable 3:1 threshold. RGB remains inside [.002,.998].
Lightness is restricted to [.43,.72] on white and [.57,.87] on #121212, chroma
is at least .04 and at most the variant cap, and each color can move no more
than .065 Oklab from its adjusted target. The objective minimizes summed
squared Oklab target errors. It does not keep increasing separation after the
required floor is reached.

Three deterministic SLSQP starts use seed 14507 plus the count, with a 200-step
limit per start. Every result is screened independently through the frozen H3
categorical validator, including all H1 float/u8, Oklab/CAM02-UCS, background
contrast, uniqueness and construction-range requirements. Results retain every
matrix, check, movement, solver outcome and floating recipe. The original H3
tables are retained for comparison and have not been replaced or re-approved.

## Evidence and review

All **18** alternatives pass: three variants × counts 4/6/8 × two backgrounds.
The gallery places each variant against the original using identical swatch,
marker and overlapping-line geometry. Six-color balanced candidates also have
all eight simulated-viewing-condition panels. Full float/8-bit pair matrices
and grayscale audits are retained in `results.json`. The study does not
establish results for counts outside 4/6/8, and these candidates are not
silently substituted by the public `categorical()` factory.

My aesthetic recommendation is Balanced. Softer and Clearer expose nearby
choices for visual review. After the user selects a direction, the production
change can extend this construction to the supported counts, expose an
explicit style, and version the new prepared tables without changing H0–H2.

Reproduce or verify locally with the optional design/research environment:

```powershell
uv run --locked --extra design --extra research python tools/explore_categorical_styles.py
uv run --locked --extra design --extra research python tools/explore_categorical_styles.py --check
```

The study records exact numerical package versions and source hashes; its check
mode reaudits every saved passing candidate at 1e-8 and verifies gallery hashes.
Visual inspection checks layout, not universal human distinguishability.

Verification: all 18 saved float/8-bit reports reproduced within 1e-8, gallery
hashes matched, the 21 categorical/ordered core-interface tests passed, and
the unchanged H2 complete-path/discrete evidence reproduced on both backgrounds.
