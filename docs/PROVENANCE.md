# Numerical foundation provenance

Extraction date: October 22, 2026. Huevat H0 is derived from the local
`sketchplot` working tree at <https://github.com/clay-wood/sketchplot>, based on
commit `84a0cb0d57cd161adffdcb17f6958b04d99033d6`.
The extracted color files were **untracked** in that checkout. The base commit
does not identify their content. `extraction.json` records SHA-256 hashes of
the actual source snapshot and Huevat destinations, with CRLF normalized to LF.
No sibling project is needed to install, import, or test Huevat.

H1 adds the separately documented [reference corpus](REFERENCES_H1.md).
`vision.py` now reads frozen Machado severity tables and interpolates between
tabulated severities; default severity-100 behavior and its coefficients are
retained. `extraction.json` preserves the H0 destination hash in addition to
the current H1 hash and the unchanged original source hash.

## Extracted material and changes

- `src/sketchplot/colors/space.py` to `src/huevat/space.py`: conversions,
  fixed-lightness/hue chroma reduction, hex encoding, distance, and contrast.
  Huevat adds docstrings, strict six-digit hex validation, rejection of string
  coordinate triples, finite/nonnegative gamut-tolerance validation, and
  `math.dist` for Euclidean distance. Matrix coefficients are unchanged.
- `src/sketchplot/colors/vision.py` to `src/huevat/vision.py`: Machado
  severity-100 matrices and display simulation. Huevat freezes the matrix
  mapping and handles unhashable condition input as a `ValueError`.
- Numerical reference and regression cases in `tests/test_colors.py` informed
  Huevat's separate tests. Palette-specific gates and rendering tests were not
  extracted. The complete source test-file hash is recorded.
- The sketchplot MIT license is retained in `licenses/sketchplot-MIT.txt`.
  The colorspacious MIT notice is retained in `licenses/colorspacious-MIT.txt`
  because the source matrix transcription was checked against that project.

The parser, named-color registry, generated palettes, weighted greedy search,
browser assets, and plotting interface remain in sketchplot. Existing
sketchplot colors are not promoted to accepted Huevat defaults.

## Mathematical sources and conventions

1. [Bjorn Ottosson, Oklab](https://bottosson.github.io/posts/oklab/):
   D65, the updated January 25, 2021 linear-sRGB matrices. Huevat decodes sRGB
   before converting; L uses the 0-1 scale. The finite-precision inverse is
   tested to an absolute encoded-RGB error of 2e-6. Neutral Cartesian chroma
   at or below 1e-12 receives the conventional hue zero.
2. [W3C relative luminance and contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html):
   the sRGB transfer breakpoint is 0.04045; relative luminance weights are
   0.2126, 0.7152, 0.0722; contrast is `(Y_max + .05)/(Y_min + .05)`.
   This function supplies a measurement, not an H1 quality profile.
3. Machado, Oliveira, Fernandes (2009), DOI
   [10.1109/TVCG.2009.113](https://doi.org/10.1109/TVCG.2009.113),
   [author supplement](https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html).
   H0 retains severity 100 for protan/deutan/tritan. Coefficients were checked
   against the [colorspacious transcription](https://github.com/njsmith/colorspacious/blob/master/colorspacious/cvd.py).
   The author supplement timed out during H0 verification; that limitation
   remains explicit. Simulation multiplies linear RGB, clips the simulated
   display channels to [0, 1], then re-encodes.

Gamut membership permits 1e-7 encoded-channel roundoff by default; callers can
request zero tolerance. Gamut mapping performs 32 chroma bisections and snaps
only roundoff-sized boundary excursions after finding an admissible result.
It is a bounded numerical fallback, not CSS local-MINDE. Requested L=0/1 maps
to exact black/white. Hex export rounds to nearest 8-bit channels, with ties
to even, and rejects out-of-gamut values beyond the stated tolerance.

These are numerical conventions and regression tolerances. H1 must establish
perceptual thresholds before optimizing defaults. This foundation does not
establish human distinguishability, full CVD severity coverage, independent
CAM02-UCS audits, or scientific gradient quality.

## Recheck

```powershell
uv run --locked python tools/check_provenance.py
# Optional comparison with the original source snapshot:
uv run --locked python tools/check_provenance.py --source-root ../sketchplot
```

The manifest fingerprints this extraction. If later foundation changes are
intentional, update the destination fingerprint with an explained change;
retain the original source fingerprint.
