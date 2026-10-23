# v0.1 API guide

The base package imports only the standard library. All generation, native
rendering and figure edits are explicit. For first use see [QUICKSTART.md](QUICKSTART.md).

Prepared factory requests reuse immutable runtime views. Reversal shares frozen
source/evidence, and oriented `.report` reads are cached on that view. Calling
`.to_dict()` still returns an independent mutable copy. Custom search requests
and all numerical methods/recipe formats retain their original behavior. See
[maintenance and profiling](MAINTENANCE.md).

| Operation | Interface | Dependency/behavior |
| --- | --- | --- |
| Categorical | `categorical(n, background="light", style="clearer")` | Prepared counts 2–12 on both backgrounds; original style is `max-separation` |
| Ordered constructors | `sequential()`, `diverging()`, `multihue()`, `spectral()` | Existing prepared defaults retained; custom requests need `[design]` |
| Named alternatives | `gradient_names(family=None, domain=None)`, `gradient_info(name)`, `gradient(name, background=...)` | Twelve experimental routes, 24 variants |
| Release discovery | `design_ids(family=None, background=None, role=None)` | Reads only the small registry; roles `default`, `legacy`, `experimental` |
| Exact identity | `design_info(id)`, `get_design(id)` | Metadata includes recipe hash/review scope; prepared immutable objects cached, at most 16 |
| Sampling | `g.at(t)`, `g.reversed()`, `g.discrete(n, context=None)` | Uniform discrete sampling unchanged; exact count must pass |
| Count advice | `known_counts(g)`, `nearby_counts(g, n, context=None)` | Prepared passing uniform counts only; no search or exhaustive claim |
| Positioned sampling | `optimized_discrete(g, n, context=None, grid=257, max_seconds=10)` | Explicit optional search; returns colors, positions and independent audit |
| Compact status | `summarize(source)` | Small status view; full `.report` remains available |
| Exact recipes | `.to_recipe()`, `.to_json()`, `load_recipe(value, validate=True)` | Existing formats retained, including old categorical colors |
| Export | `export(design, format="json", n=None, context=None, labels=None, source=None, tolerance=.002, max_stops=1025)` | Returns immutable `Export(text, format, report)` with `.sha256`, `.write(path)` |
| Import compact JSON | `load_export(value, validate=True)` | Returns `LoadedExport(design, source, labels)`; `.color_map` requires labeled palette |
| Native adapters | `huevat.adapters.matplotlib`, `.plotly`, `.ultraplot` | Explicit imports and operations; no global registration on import |
| Figure doctor | `inspect`, `diagnose`, `propose`, `preview`, `apply`, `load_proposal` | Lazy backend imports; audits/proposals need `[design]`; explicit apply/guarded undo |

The export format names are `json`, `csv`, `hex`, `css`. JSON retains exact
recipes, source orientation, selected count/positions and labels, without
copying the full audit history. Hex/CSV encode exact exported colors; CSS
continuous ramps are adaptive sRGB approximations, while discrete CSS is an
equal-width swatch view. Source-independent tables do not acquire a continuous
recipe or physical data boundaries. Loaded source evidence is recovered from
known hashes or independently revalidated, never trusted from input claims.

`export(g, n=...)` and `export(p, source=g)` retain uniform selection provenance.
Only the latter needs an explicit parent because an ordinary `Palette` from
`.discrete()` does not itself contain the source path. Positioned and categorical
palettes contain their own recipes. Continuous JSON has no category labels.
Unknown positioned imports need `[design]`; `validate=False` retains their
explicitly unvalidated status.

`Export.report` states whether an output is lossless, its source/exported-color
hash, source version, interpolation/selection scope and any CSS approximation
measurement. Export evidence never grants human approval. `LoadedExport.source`
retains the original gradient when `.design` is a selected palette.

Failures distinguish invalid inputs (`ValueError`), an audited selection failure
(`QualityError`), a proved fixed-path count conflict (`ConstraintConflictError`)
and a finite search that found no passing design (`SearchExhaustedError`). All
quality errors retain immutable reports. Nearby prepared counts can be higher
as well as lower than the requested number.

See [adapter methods](METHODS_H4A.md), [collection methods](METHODS_H4B.md),
[figure doctor](FIGURE_DOCTOR.md), [export/release protocol](METHODS_H4D.md) and
[migration notes](MIGRATION.md) for the relevant scope and limitations.
