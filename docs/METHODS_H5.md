# Additional palettes, figures and Julia

Declared November 17, 2026 before generating new resources. The user chose
`core`, `earth` and `gem`. Core is the existing Clearer palette with a shorter
public name; `clearer` remains accepted and saved recipes retain their colors.

New categorical sets use the existing normal/CVD, float/8-bit Oklab and
CAM02-UCS separation, 3:1 background contrast, gamut and target-movement checks.
Each count is optimized jointly; only independently passing counts are shipped.
Light and dark variants are checked separately. Appearance review remains
separate from these numerical checks. No thresholds are relaxed for new sets.

Cyclic paths need their own rules: exact closure, matching seam derivatives,
continuous gamut checks and measured normal/CVD step variation. Their lightness
is periodic, never claimed monotone. Discrete cyclic selections exclude the
duplicate endpoint and check the closing pair. Their results do not inherit a
sequential or diverging approval.

Figure edits preserve data, scales, limits and explicit scalar centers. Filled
regions and uncertainty fills are inspected as displayed composites; no whole
figure readability claim is made. Scalar recoloring is an explicit operation
with copied previews and undo. Palette selection can compare supplied palettes
without relaxing existing color checks. Proof sheets show the actual figure at
the requested width and identify any content not included in simulations.

Prepared optimized selections store exact source recipes, positions and checked
colors. Unknown selections still require independent validation. Count advice
distinguishes passing, failed and search-exhausted cases. Long custom searches
run separately, report elapsed time and can be cancelled without changing data.

Julia uses the same exported colors and cubic Oklab coefficients, with optional
Makie.jl and Plots.jl adapters. Tests compare Python and Julia colors, reversal,
category identities and asymmetric signed centers. Plotting backends are not
loaded by the Julia base package. No interactive palette editor is included.
