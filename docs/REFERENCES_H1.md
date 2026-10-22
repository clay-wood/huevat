# H1 reference provenance and attribution

Frozen October 22, 2026. Full versions and source/table hashes are retained in
`src/huevat/data/references-v1.json`, `machado-v1.json`, and `manifest-v1.json`.
The corpus and profiles load using the standard library. Research evaluation
and rendering use the separately installed `huevat[research]` extra.

| Reference | Source and selection |
| --- | --- |
| Okabe-Ito | Eight Figure 2 RGB triples from Wong (2011), in printed order; source-order prefixes for study counts 4/6/8 |
| ColorBrewer Set2, Dark2, Paired | Exact native count-specific tables; no truncation of a larger Brewer palette |
| ColorBrewer Blues, YlGnBu, RdBu, Spectral | Exact native tables, including 5/7/9 discrete bins; largest table supplies the explicitly labeled continuous study adaptation |
| viridis, cividis | Matplotlib 3.11.2 native 256-entry floating-point RGB tables |
| ColorCET fire | ColorCET 3.2.1 `linear_kryw_0_100_c71`, Peter Kovesi |
| ColorCET coolwarm | ColorCET 3.2.1 `diverging_bwr_40_95_c42`, Peter Kovesi |
| ColorCET Glasbey | ColorCET 3.2.1 `glasbey_bw_minc_20`; documented source-order prefixes, not count-specific optimization |

The exact Okabe-Ito hex specifications are #000000, #e69f00, #56b4e9,
#009e73, #f0e442, #0072b2, #d55e00 and #cc79a7. Wong's
[2023 correction](https://www.nature.com/articles/s41592-023-01974-0)
credits the Okabe and Ito 2002 presentation. The supplied
`nmeth.1618.pdf` has SHA-256
`69e19ffe62bc4ca6efc9eed0e230a99e323181fca8ac2527777df0c5a5f5e2c3`.
The article is not redistributed. Its numeric color specifications are
transcribed, rather than estimated from PDF pixels.

The original [ColorBrewer export](https://colorbrewer2.org/export/colorbrewer.json)
is retained at `tools/sources/colorbrewer.json` with its source-file hash.
Attribution: color specifications and designs developed by Cynthia A. Brewer,
Mark Harrower and The Pennsylvania State University. The upstream Apache-2.0
license is retained at `licenses/colorbrewer-Apache-2.0.txt`.

The Matplotlib license and ColorCET CC-BY-4.0 license are retained at
`licenses/matplotlib-LICENSE.txt` and `licenses/colorcet-CC-BY-4.0.txt`.
ColorCET's continuous maps are attributed to Peter Kovesi and its categorical
method to Glasbey and colleagues, as described by
[ColorCET](https://colorcet.holoviz.org/). These data keep their upstream
licensing; Huevat's code license does not replace it.

The Machado matrices are retained from colorspacious 1.1.2, whose source hash
and MIT notice are recorded. The source implementation transcribes the
authors' supplementary tables for DOI 10.1109/TVCG.2009.113. Huevat stores all
eleven tabulated severities for each condition, with linear coefficient
interpolation for intermediate input. Severity 100 remains the default;
study conditions are protan/deutan 50/80/100 and tritan 100. This is model
screening rather than a guarantee of individual human experience.

## Adaptations and preservation

Native source values are immutable tuples in the reference API. Sampling and
quantization produce separate arrays. Ordered reference paths in the study
use **piecewise-linear encoded-sRGB interpolation** on the largest native
table, resampled at 257 parameter values. This is an explicit Huevat study
adaptation; it is not an assertion about the original authors' interpolation
method. 8-bit exports use ties-to-even rounding. Machado display simulations
clip to sRGB and report the amount of clipping separately.

No optimized Huevat default is produced or adopted in H1. No upstream palette
has been adjusted to pass the provisional profiles.

## Reproduction

```powershell
uv sync --locked --extra research
uv run --locked --extra research python tools/freeze_references.py --check
uv run --locked --extra research python tools/build_baseline.py --check
```

The freeze check rebuilds the corpus offline from the retained Brewer export
and locked source packages, comparing bytes. Ordinary study evaluation reads
only the frozen local corpus. Artifact hashes are checked separately from
numerical comparisons (absolute/relative tolerances 1e-8).
