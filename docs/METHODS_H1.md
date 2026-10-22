# H1 reference-study protocol, version 1

Frozen October 22, 2026, before baseline evaluation and before any Huevat
default optimization. `src/huevat/data/profiles-v1.json` is the executable
threshold specification. New criteria require a new profile version and
rationale; baseline failures do not justify loosening this version.

## Purpose and contexts

Compare published references under explicit models and common rendering
conditions. No aggregate ranking, winning palette, approved default, or claim
of universal accessibility follows from this study. Published schemes have
different design goals, so a failed Huevat engineering screen can describe a
tradeoff rather than an error in the source.

Four profiles combine `data-marks` / `filled-fields` with `light` / `dark`.
Light is #ffffff and dark is #121212. All colors are encoded sRGB/D65. Data
marks use 3:1 background contrast where applicable, pairwise separation and
rendered line/marker inspection. Filled fields use ordered lightness, local
contrast shape, continuity and feature preservation; pale cells need not have
3:1 background contrast. Both backgrounds receive identical study coverage.

## Corpus and sampling

Freeze exact source tables with source version, origin, license, raw-file
hashes and canonical RGB-table hashes. The Okabe-Ito categorical reference is
the eight exact colors reproduced by Wong (2011), attributed to Okabe and Ito
(2002) according to the [2023 correction](https://www.nature.com/articles/s41592-023-01974-0).
No black replacement, adjusted yellow, or renamed adaptation overwrites it.

Include ColorBrewer Set2/Dark2/Paired, Blues/YlGnBu, RdBu and Spectral, plus
viridis, cividis and representative ColorCET linear, diverging and Glasbey
maps. ColorBrewer's count-specific tables remain discrete originals. Evaluate
categorical counts 4/6/8 with native count-specific Brewer tables and explicit
prefixes for the fixed Okabe-Ito/Glasbey sequences. Prefix use is a study
selection rule, not a claim of optimality for each count.

Ordered comparisons use 257 uniformly spaced parameter samples. Piecewise
linear interpolation of **encoded sRGB** is an explicitly named study
adaptation of the native tables, not a claim about their authors' continuous
interpolation. Retain native tables unchanged. Evaluate both floating-point
adaptations and round-to-nearest 8-bit exports. Test 5/7/9 discrete bins
separately, using native count-specific Brewer tables where available and
uniform endpoint-inclusive sampling for the other maps. Record that sampling
rule in every result. Spectral receives diverging-arm tests, never a global
sequential ordering test. A sampled table establishes only finite-grid
behavior; continuous-path certification belongs to H2/H3.

## Measurements and decisions

Every result separates normal vision from Machado protan/deutan severities
50/80/100 and tritan severity 100. Simulations operate on linear RGB with
documented matrix interpolation; record out-of-gamut display clipping. These
are model outputs, not diagnoses. Include full categorical distance matrices
and closest pairs for every condition in both Oklab and CAM02-UCS.

CAM02-UCS is an independent audit through colorspacious, using its standard
sRGB viewing conditions (D65 XYZ100, Y_b=20, L_A approximately 4.074 cd/m²,
average surround). Use the same viewing conditions for both backgrounds to
isolate the palette comparison; this does not model dark adaptation.
Report that limitation instead of interpreting a dark background as a change
in human adaptation. Record exact runtime parameters in machine output.

Ordered measurements include lightness traces, adjacent perceptual steps,
speed coefficient of variation, lightness-step 95th/5th percentile ratio,
longest flat run, maximum/median step ratio and maximum step. Diverging maps
are tested per arm, with one shared center, center chroma, matched arm
lightness/distance and opposite-arm separation at matched radii. Discrete
ordered tests measure adjacent classes separately; data-mark use additionally
tests all pairs and background contrast.

The feature probe samples 17 locations per arm with +/-0.01 parameter
perturbations. Normalize each peak-to-trough lightness response by the global
average arm slope times .02. Report the minimum gain, including luminance
grayscale. Also render an oscillating ramp with decreasing feature amplitude,
Gaussian features and a signed field whose zero is exactly the center.
The probe is a numerical contrast proxy. Visual spatial-feature review remains
a distinct, pending human assessment.

Profile entries identify their rationale. **Mathematical requirements** cover
input, gamut, count, unique exported categorical colors and normal-vision
monotone lightness per ordered arm. **Provisional engineering screens** cover
the numerical distances, spans, uniformity, center/arm balance and feature
gains. **Visual evidence** contains matched rendered panels and a pending
review record, with no automatic pass. A numerical pass never changes the
review status or creates an accepted default.

## Rendering and reproducibility

Use identical data, category count, sampling, dimensions, mark sizes and sRGB
encoding for each reference. Render both backgrounds, overlapping curves at
0.75/1.5 pt, filled markers at 3/5 pt, discrete legends, ramps, grayscale,
lightness/speed traces, synthetic fields and normal/simulated views. Export
publication-size 300-DPI PNGs and an offline HTML gallery with local images;
do not load web scripts/fonts. Keep condition names and supplied color values
visible. Asset hashes identify a particular rendering; PNG bytes need not be
portable across different Matplotlib/font versions.

The machine report includes the corpus/profile/protocol hashes, source and
algorithm versions, dependency versions, parameters, measured values,
individual criteria and reasons. Numeric reproduction compares within
documented absolute/relative tolerances (1e-8), not platform PNG hashes.
Rebuilding a frozen corpus is an explicit maintenance command; normal study
generation reads local resources and requires no network.

Implementation clarification from negative-control testing: the lightness
ordering tolerance applies to maximum backward excursion from the running
monotone envelope, not just one adjacent step. This prevents a broad reversal
from accumulating many individually small steps. Both quantities are retained
in reports. The profile values frozen in commit `90e7b60` are unchanged. The
shared diverging center must be an extremum of both arms within the arithmetic
1e-7 tolerance, including after 8-bit export; the separate 0.002 allowance
for small accumulated export-order perturbations does not move the center.

Negative controls must detect repeated categorical colors, red-green encoded
RGB interpolation lightness artifacts, a lightness reversal, a broad flat
region, a narrow contrast spike and an excessive discrete class count. Include
them in the report, label them defective, and keep them out of reference
comparisons. Every declared metric must have a defined zero/degenerate case;
invalid or non-finite values fail explicitly rather than producing an apparent
pass. H1 includes no search, so it makes no infeasibility claim.

## Sources

- [Okabe and Ito, Color Universal Design](https://jfly.uni-koeln.de/color/)
- Wong (2011), *Points of view: Color blindness*, DOI 10.1038/nmeth.1618,
  supplied PDF; [attribution correction](https://www.nature.com/articles/s41592-023-01974-0)
- [ColorBrewer family semantics](https://colorbrewer2.org/learnmore/schemes_full.html)
- [Kovesi (2015), Good Colour Maps](https://arxiv.org/abs/1509.03700)
- [ColorCET documentation](https://colorcet.holoviz.org/)
- [Colorspacious model and viewing-condition documentation](https://colorspacious.readthedocs.io/en/latest/reference.html)
- [WCAG graphical contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
