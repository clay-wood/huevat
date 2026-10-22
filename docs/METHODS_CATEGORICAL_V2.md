# H3 categorical revision: Clearer

October 22, 2026. Algorithm/resource version: `h3-categorical-v2`.

The user selected **Clearer** after reviewing Balanced, Softer and Clearer
alternatives to the original H3 categorical palettes. Clearer is now the public
`categorical()` default. The direction was reviewed at counts 4/6/8 on both
backgrounds; prepared counts 2–12 now pass numerical validation independently.
Expanded-count perceptual review and the final H4 approval remain separate.

## Construction and unchanged quality gates

Clearer prioritizes hard screening requirements, then closeness to coherent
color targets. It does not keep increasing separation after the required
floor is reached. This is the user's approved change to the original H3
objective priority, rather than a relaxation of any H1 threshold.

Each count jointly optimizes 3n encoded RGB coordinates and an auxiliary z
fixed at .043. Every normal Oklab pair distance divided by two and every
simulated pair distance must reach z. Independent CAM02-UCS minima are 8.3
normally and 4.15 in simulated conditions during search. A .004 luminance margin
protects the 3:1 background-contrast boundary against quantization. The final
audits retain H1's original .08/.04 Oklab and 8/4 CAM02-UCS thresholds and 3:1
normal contrast. All eight viewing conditions and both float/8-bit output are
evaluated. Uniqueness, gamut and original H3 construction-range checks remain.

The aesthetic envelope limits normal Oklab lightness to [.43,.72] for light
backgrounds and [.57,.87] for dark backgrounds, chroma to [.04,.18], and per-color
movement from its design target to .065 Oklab. Construction checks use 1e-7
arithmetic tolerance and apply to the floating design. The objective minimizes
summed squared Oklab target error, selecting only fully passing candidates.
Quantized colors receive their own unchanged numerical screens.

The first eight targets are exactly those used for the selected Clearer study.
Four additional anchors extend the same aesthetic to 9–12 categories:

```
#4379a3 #348b83 #ae883b #bd6c60 #9274a3 #5599b4
#9b586d #7e8750 #bd803f #6c7b91 #638759 #b7758f
```

For automatic targets, Oklab chromatic coordinates are multiplied by 1.18.
Dark-background targets additionally increase lightness by .12. Targets are
preferences, not guarantees of passing colors. Counts 4/6/8 reproduce the
selected study's exported hex colors exactly. Each count is jointly optimized;
the prepared results are not truncated from a larger optimized palette.

Custom supplied colors retain their original values in `preferences` and in
supplied-to-produced reports. Their design targets are projected into a narrow
interior of the style's lightness/chroma ranges. This permits controlled
adjustment while avoiding the old maximum-separation objective. Some preference
sets cannot be accommodated by the declared local search/envelope within its
budget. Such a result is search exhaustion, not an infeasibility theorem.

For custom counts above 12, additional deterministic hue/lightness targets
extend the family, with no assertion that the requested count passes. Supported
search sizes remain 2–64. Backgrounds use the same light/dark luminance branch
choice as H3. An intermediate background can therefore exhaust this restricted
style even if a different contrast branch or style could work.

The default custom budget is three starts / 30 seconds, seed 14507 plus count.
Starts perturb targets by seeded Oklab noise; SLSQP uses up to 200 iterations
per start. Prepared builds use three completed starts with a 120-second safety
budget. Objective/constraint/candidate checks enforce cooperative deadlines;
one numerical operation may overrun. Completed runs reproduce on the recorded
numerical stack, while deadline-truncated runs may choose different candidates.

## Versions, immutable data and compatibility

Clearer uses new `categorical.py` and `design_categorical.py` modules and a new
`categorical-v2.json` resource. Previously frozen numerical/design modules and
versioned resources remain unchanged; public exports and the resource manifest
add the revision. The frozen H3 auditor is reused on identical RGB through
a schema proxy, then Clearer-specific aesthetic gates are added. The final
report/recipe carries the new version, style, explicit Oklab targets and hash.

```python
import huevat as hv

p = hv.categorical(6)                       # Clearer
p = hv.categorical(6, style="clearer")       # Explicit
old = hv.categorical(6, style="max-separation")
restored = hv.load_recipe(p.to_json())
```

The original explicit style preserves the recorded H3 prepared colors. All old
data-only recipes still dispatch to their original loaders. Unknown supplied
evidence is ignored and reaudited by default, including aesthetic target checks
for the new version. `validate=False` permits structural inspection with an
unvalidated screening status. Recipe identifiers prevent silent substitution
of new colors in an old serialized design.

Prepared lookup, reports, hex export and recipe round trips remain standard-
library-only. Custom generation and unknown-recipe audit require
`huevat[design]`. Public import and prepared lookup never run optimization.
Changing search options explicitly requests a new search under the existing
factory convention; a custom search is not a latency guarantee.

## Evidence and reproduction

`tools/build_clearer.py` independently reaudits all 22 prepared palettes,
records source hashes, and generates an offline gallery with all counts,
thin lines, small markers and CVD/grayscale views at counts 4/6/8/12. Numeric
reports retain all matrices, contrast values, aesthetic movements and search
versions. It preserves the original H3 and selection-study galleries.

```powershell
uv run --locked --extra design --extra research python tools/build_clearer.py
uv run --locked --extra design --extra research python tools/build_clearer.py --check
```

Tests verify every count on both backgrounds, exact agreement with the selected
study, old/new recipe dispatch, forged-claim rejection, target-envelope failures,
repeatable completed searches, custom preferences/backgrounds, honest deadline
failures, and operation with all optional imports blocked. H1/H2/H3-v1 evidence
checks remain in CI alongside the Clearer check and offline pip/uv installs.
