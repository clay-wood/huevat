# Migrating development snapshots to 0.1.0

Existing constructor calls keep their colors and numerical rules. No H0–H4c
algorithm, threshold, recipe ID or prepared color/path was changed for this
release. The package version becomes `0.1.0`; source installation remains
private and no PyPI publication accompanies the version change.

The explicit release policy retains current defaults, including Clearer. The
twelve named gradient routes remain experimental. `design_info(id)["role"]`
records release inclusion separately from the frozen report's original
`approved_default=False` and review flags. These historical flags remain
unchanged; they do not prevent using the retained release defaults.

| Existing usage | v0.1 behavior/action |
| --- | --- |
| `categorical(n)` after the Clearer revision | Same count-specific colors; save label mappings when categories change |
| Original H3 categorical appearance | Use `categorical(n, style="max-separation")` or load its saved old recipe |
| `sequential()`, `diverging()`, `multihue()`, `spectral()` | Same prepared values, orientation, backgrounds and recipe IDs |
| `.discrete(n)` | Same uniform locations and exact count checks; no automatic optimization |
| `.to_recipe()`, `.to_json()`, `load_recipe()` | All previous formats remain supported with their original evidence behavior |
| Huge JSON solely to preserve a design | `export(source)` omits large audit evidence and reuses/revalidates it on import |
| `p = g.discrete(7)` for portable files | `export(g, n=7)` or `export(p, source=g)` retains source provenance |
| Named collection routes | Still `gradient(name)`; explicit experimental role is discoverable |
| Repeated prepared constructor calls | Reuse the object, or use cached `get_design(immutable_id)` |
| “Reduce n” after a failed count | Check `nearby_counts(g, n)`; both lower and higher known counts may pass |
| Adapter attribute evidence | Still retain `.huevat_report` separately when native copies drop attributes |
| Figure doctor | Existing inspect/propose/preview/apply/undo and proposal schema unchanged |

To transfer compact JSON:

```python
output = hv.export(gradient, n=7, labels=["a", "b", "c", "d", "e", "f", "g"])
output.write("design.json")
loaded = hv.load_export(open("design.json", encoding="utf-8").read())
palette, source_gradient, labels = loaded.design, loaded.source, loaded.labels
```

An export fingerprint detects accidental modification, not malicious authorship.
Import validates schemas and source recipes independently and compares exact
exported colors. `validate=False` never upgrades unknown evidence. Keep this
flag out of ordinary plotting workflows that require a numerical pass.

CSV, hex and CSS are display exports. They cannot reconstruct an exact
continuous path or validate a newly edited table. Use JSON as a sidecar when
these files need provenance. Normalized sampling positions do not define
physical bins; keep original levels, units, reference centers and missing-data
policies explicit in your plotting code.
