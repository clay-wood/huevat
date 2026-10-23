# Huevat: constrained design of scientific palettes and gradients

## 1. Direction and agreed choices

Build **Huevat** as an independent Python library for generating and evaluating perceptual color palettes. Oklab/Oklch provide the design coordinates; the principal contribution is the construction method, quality criteria, and useful defaults.

The first release will include:

- Categorical palettes optimized for each requested category count.
- Sequential gradients, including single-hue and multi-hue designs.
- Diverging gradients and Spectral-like multi-hue diverging designs.
- Continuous evaluation and discrete sampling of ordered gradients.
- Equally reviewed defaults for light and dark backgrounds.
- A small Python interface, quantitative reports, and a generated comparison gallery.
- First-class, optional adapters for **Matplotlib, Plotly, and UltraPlot**.
- Explicit optimized discrete sampling, preserving the continuous path and
  returning the selected sample positions.
- A figure doctor that combines inspection, coordinated color/marker/dash
  design, figure-aware assignment, and palette negotiation.
- A broader default collection for general work, seismic/subsurface plots,
  topography/bathymetry, and atmospheric fields.

Supplied colors are preferences that the generator may adjust. Generated results must pass their selected quality profile. Failed searches return an explanation rather than an apparently approved palette.

Create a separate **private** `huevat` repository, subject to confirming repository availability.

Initial exclusions: a standalone general-purpose interactive palette editor,
CSS theme generation, wide-gamut output, printer-profile guarantees, and
universal claims of accessibility. Figure-doctor previews and palette
negotiation are now in scope as optional workflows.

**Scope update, October 23, 2026:** the user accepted the figure-doctor workflow
and optimized discrete sampling, requested more sequential/diverging defaults
with general and application-specific aesthetics, and made all three plotting
adapters required. ColorCET and Fabio Crameri's Scientific colour maps are
methodological/comparison references. Their exact tables retain attribution;
new Huevat defaults should develop an independently reviewed appearance rather
than inherit their aesthetics automatically. Detailed requirements, proposed
API shapes and acceptance gates are in [NEXT_STEPS.md](docs/NEXT_STEPS.md).

## 2. Mathematical design and quality criteria

### Establish the reference study first

Use the exact Wong/Okabe–Ito colors as an attributed categorical reference. Preserve those reference values; generated adaptations receive different names. Include ColorBrewer categorical, sequential, diverging, and Spectral schemes, plus viridis, cividis, and representative ColorCET maps.

The attached Wong article and its correction supply the provenance for the Okabe–Ito reference. :codex-file-citation{path="C:/Users/local.cw43566/Downloads/nmeth.1618.pdf" purpose="source"} [Attribution correction](https://www.nature.com/articles/s41592-023-01974-0)

Evaluate references under matched conditions: category count, background, mark size, gradient resolution, and output encoding. Record limitations rather than assigning one universal “best palette” score.

Before optimizing published defaults, establish versioned quality profiles containing the metrics, numerical tolerances, screening thresholds, and their rationale. Separate mathematical requirements, provisional engineering thresholds, and evidence from visual review. Thresholds must not be relaxed after seeing candidate results merely to make a default pass.

### Use different rules for different families

| Family | Construction and requirements |
|---|---|
| Categorical | Jointly optimize the requested number of colors. Maximize the weakest pairwise separation across normal and simulated vision, subject to background contrast and controlled lightness/chroma ranges. |
| Sequential | Construct a smooth perceptual path with monotone lightness and controlled local contrast. Optimize hue and chroma without introducing unintended emphasis or flat regions. |
| Diverging | Join two ordered arms at a shared neutral center. Match their lightness progression and perceptual distance from the center; validate that the arms remain distinguishable. |
| Multi-hue sequential | Follow an ordered hue route while retaining monotone lightness. Additional hues must not create false boundaries. |
| Spectral-like diverging | Use two multi-hue arms around a meaningful center. Apply diverging criteria rather than treating it as a rainbow sequential map. |

Application semantics determine the family: signed seismic amplitudes and
atmospheric anomalies use a declared reference value; velocity/density,
concentration and magnitude fields use ordered scales. Topography/bathymetry
needs an explicit sea-level mapping and separate review of any land/water
transition. Direction/phase data require a cyclic family and its own protocol;
they must not be presented as ordinary sequential gradients.

This distinction follows [ColorBrewer’s scheme semantics](https://colorbrewer2.org/learnmore/schemes_full.html).

**H3 visual-review revision (October 22, 2026):** the user selected the
Clearer categorical direction. Its default construction satisfies the frozen
separation/contrast gates, then preserves coherent aesthetic targets. Additional
separation beyond those gates is secondary to the chosen appearance. The
original auxiliary-maximin categorical construction remains an explicit
`style="max-separation"` option; its frozen tables and old recipes are retained.

### Implement constrained optimization

- Represent ordered gradients with a small number of perceptual control points. Use monotone piecewise-cubic lightness profiles and smooth chromatic paths; handle neutral regions in Cartesian Oklab coordinates to avoid undefined hue.
- Optimize in floating-point color, with sRGB gamut constraints. Use constant-lightness/hue chroma reduction as a controlled fallback, then revalidate the resulting path.
- Use deterministic multi-start constrained optimization through SciPy. Categorical optimization uses an auxiliary minimum-distance variable rather than an arbitrary weighted average that can hide a poorly separated pair.
- Apply priorities in order: satisfy hard constraints, improve the weakest perceptual relationships, preserve supplied color preferences, then reduce unnecessary curvature and local contrast variation.
- Validate exported, quantized colors as well as the underlying floating-point design. Never repair a failed result by clipping RGB channels or silently dropping requested colors.

Equal Oklab arc length alone will not establish a good scientific gradient. Include lightness progression and spatial-feature tests, following the concerns demonstrated by [Kovesi](https://arxiv.org/abs/1509.03700).

### Make screening context-specific

Provide versioned profiles for **data marks** and **filled fields**, each supporting light and dark backgrounds.

- Data marks: pairwise separation, background contrast, and screening at representative line widths and marker sizes. Use 3:1 background contrast where applicable.
- Filled fields: ordered lightness, local contrast consistency, continuity, and feature preservation. Do not require every pale heatmap cell to contrast 3:1 with its background.
- Discrete ordered palettes: validate the requested bins separately; continuous gradient quality does not guarantee distinguishable discrete classes.
- CVD screening: evaluate documented Machado protan/deutan severities and tritanopia, with normal vision assessed separately.
- Independent audit: evaluate in CAM02-UCS as well as Oklab, and include grayscale and rendered spatial tests.

A passing report means the design passed a stated model and context. It does not establish universal human distinguishability.

Distinguish invalid input, demonstrated constraint conflicts, and **search exhausted without a passing result**. An unsuccessful optimizer is not proof of infeasibility.

## 3. Public interface and package architecture

Keep common use limited to family, category count, preferred colors, and background:

```python
import huevat as hv

colors = hv.categorical(6, background="light")

gradient = hv.sequential(
    color="#0072b2",
    background="dark",
)

diverging = hv.diverging(
    colors=("#0072b2", "#d55e00"),
    background="light",
)

spectral = hv.spectral(background="light")

colors = gradient.discrete(7)
rgb = gradient.at(0.35)
report = gradient.report
```

Interface behavior:

- `categorical()` returns an immutable palette; changing its count may change every color.
- Ordered constructors return immutable gradient objects supporting `.at(t)`, `.discrete(n)`, and `.reversed()`.
- `.discrete(n)` validates that particular selection and can reject an excessive count.
- Optimized discrete sampling is an explicit alternative. It returns colors
  and sample positions, validates the exact selection, and keeps the existing
  uniform behavior unchanged. Perceptual sample positions do not silently
  redefine physical data-bin boundaries.
- Explicit background colors are supported and validated separately from the reviewed light/dark defaults.
- Reports expose measured scores, pass/fail criteria, supplied-to-produced color changes, algorithm/profile versions, and reproducibility information.
- Custom designs serialize to data-only recipes. Accepted defaults have immutable versioned identifiers.

Provide lightweight loading, sampling, JSON/hex export, and recipe reading in the base package. Put NumPy/SciPy generation dependencies in **`huevat[design]`**. Keep Matplotlib adapters and gallery/research tooling optional.

Use prepared designs for normal plotting; do not run optimization during import, palette lookup, or gradient sampling. CSS gradient exports must use enough stops to meet a measured approximation tolerance rather than assuming endpoint interpolation reproduces Huevat’s path.

Adapters must preserve data normalization, signed centers, category order,
reversal, missing values and under/over-range behavior, with a measured color
approximation tolerance. UltraPlot gets dedicated colormap/cycle/normalization
tests as a supported backend. Plotting imports and global registrations remain
explicit; base import stays dependency-free.

Figure doctor inspects a supported figure without modifying it, reports the
actual displayed/composited colors and supported-artist coverage, and returns
audited proposals. Proposals can jointly assign color, marker and dash using
figure overlap/adjacency and stable category identities. Palette negotiation
offers several passing tradeoffs and respects locked colors. Applying a repair
requires an explicit API call; data, axes scales, physical units and thresholds
must remain unchanged.

Add a reproducible export/import bridge with source version and hashes; adopt new defaults only after comparative review.

## 4. Validation and review artifacts

Build four independent validation layers:

1. **Numerical:** conversion references, gamut boundaries, neutral handling, monotonicity, reversal, center continuity, discrete sampling, and serialization.
2. **Perceptual screening:** categorical distance matrices, background contrast, gradient lightness/speed profiles, arm balance, CVD results, and independent-space audits.
3. **Rendered review:** thin lines, small filled markers, overlapping series, discrete legends, ramps, synthetic fields with known features, and signed fields centered on zero—on both backgrounds.
4. **Operational:** clean uv and pip installations, offline operation, absent optional dependencies, optimizer deadlines, deterministic reproduction, and wheel/source-distribution contents.

Include deliberately defective examples: repeated colors, RGB interpolation artifacts, lightness reversals, broad flat regions, narrow contrast spikes, and excessive requested class counts. Tests must detect these failures.

Generate an offline HTML gallery, publication-size PNG comparisons, machine-readable results, and a methods report. Publish tradeoffs and failing conditions alongside successful results.

Benchmark core import, default lookup, gradient sampling, generation by family/count, peak memory, and installation footprint. Set generation budgets from measured prototypes; preserve a lightweight core without browser or plotting dependencies.

## 5. Delivery sequence and acceptance

| Stage | Deliverable | Completion gate |
|---|---|---|
| H0 | Independent private repository, uv workflow, extracted numerical foundation, provenance | Clean installation; no browser dependency|
| H1 | Reference corpus, methods protocol, quality profiles, baseline gallery | Reproducible evaluations; numerical thresholds documented before default optimization |
| H2 | Sequential and diverging construction, continuous/discrete API | Numerical and screening gates pass on both backgrounds; failures are actionable |
| H3 | Categorical and multi-hue/Spectral construction | Count-specific validation, arm/order checks, repeatable optimization, complete gallery |
| H4 | Reviewed defaults, exports, packaging | All families represented; independent audits and visual review complete; frozen identifiers and migration documentation |

The expanded H4 work is divided into reviewable slices:

| Slice | Deliverable | Completion gate |
| --- | --- | --- |
| H4a | Matplotlib, Plotly and UltraPlot adapters; optimized discrete sampling; concise summaries and count discovery | Real-backend examples/tests; approximation error and normalization verified; exact optimized samples audited; no optional imports during base lookup |
| H4b | Broader sequential/diverging collection and application gallery | Distinct reviewed hue routes; light/dark variants; seismic, terrain and atmospheric test fields; profiles declared before any new-family optimization |
| H4c | Figure doctor with coordinated encodings, figure-aware assignment and palette negotiation | Explicit inspection/preview/apply stages; supported/unsupported coverage; stable labels/locks; original figure/data unchanged until apply; model screens and human review kept separate |
| H4d | Final default adoption, exports, packaging and migration | Cross-backend regression checks, reviewed defaults/identifiers, clean installations and retained old recipes |

H4a is implemented: three optional native adapters, explicit optimized sampling,
compact status summaries and prepared uniform-count discovery. See
`docs/METHODS_H4A.md` and `research/adapters-v1`. H4b adds twelve named candidate
routes with light/dark variants, free-knot construction and the application
gallery in `research/collection-v1`; appearance review is pending. H4c (figure
doctor) is the next implementation slice. Existing H0–H3 numerical baselines and the selected Clearer categorical
direction remain the foundation. Prepared optimized caches and nearby-count
search remain follow-up usability work.

All families belong to the first release; the ordering above allows earlier methods to inform the harder constructions. A family remains experimental if its gates fail. Record that result explicitly instead of weakening its criteria to declare completion.

Maintain a living technical document with task status, evidence, verification date, limitations, and relevant commits. Do not publish to PyPI or change either repository’s privacy as part of this work.
