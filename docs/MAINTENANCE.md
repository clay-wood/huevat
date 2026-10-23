# Repository layout and performance

October 23, 2026. The current repository keeps the package, licenses/provenance,
user documentation, four current galleries, four focused test files and nine
maintenance commands. Older study plots, optimizer experiments, one-off scripts
and fifteen additional test files are ignored and removed from the Git index.
All 135 affected files remain on this machine, and the complete pre-cleanup
snapshot is commit `6f8fc02`. About 60.8 MiB of historical development material
is no longer part of the current tracked tree. Existing Git history is retained.

The four maintained test files cover the numerical foundation, optional imports,
portable recipes/native adapters, figure doctor, immutable views and the ramp
overlay regression. `tools/verify.py` additionally checks all eight packaged
resource hashes, all 76 registered designs, continuous certificates, recipe
roundtrips, reversal and prepared passing counts. `--research` independently
repeats the normal/CVD float/u8 Oklab/CAM02-UCS audits. Current gallery checks
and actual backend examples remain in CI.

```powershell
uv sync --locked --all-extras
uv run --locked --all-extras pytest
uv run --locked --all-extras python tools/verify.py --research
uv run --locked --all-extras python tools/build_collection.py --check
uv run --locked --all-extras python tools/build_release.py --check
uv build
uv run --locked --all-extras python tools/check_install.py
```

Default pytest discovery targets the four maintained files. On this machine,
`pytest tests` explicitly runs the larger ignored historical suite as well.
Fresh checkouts intentionally do not contain that historical suite. To recover
it without changing the checkout, export the old snapshot:

```powershell
git archive --format=zip --output=artifacts/historical-studies.zip 6f8fc02 tests tools research
```

The sdist explicitly includes only the maintained tests/scripts. Historical
research plots and local test output are excluded even when present on disk.
The wheel retains all numerical resources; cleanup does not remove runtime
reference tables, certificates, recipes or quality evidence.

## Center line correction

The collection overview drew `axvline` on top of each diverging ramp. Its gray
reference marker looked like a color defect and also appeared in the embedded
release overview. Both light/dark overviews now show only sampled colors. Their
description places the neutral at the midpoint; the gradient recipes, exact
neutral, exported CSS, scalar centers and numerical thresholds are unchanged.

## Measured bottlenecks and changes

Five warmed timing medians on Windows/Python 3.12.14 showed that recursive
copying/freezing of large immutable reports and discrete-count evidence
dominated repeated lookup/reversal. A separate runtime view layer now reuses
already-frozen internals, caches prepared requests (64 entries), caches oriented
reports on each immutable view and reuses the H3 discrete proxy. Original
construction/audit modules remain unchanged. Custom searches still execute
explicitly, and argument types remain part of cache keys so invalid bool/float
settings cannot reuse a valid cached result.

| Warm operation | Original engine | Runtime view |
| --- | --- | --- |
| Spectral lookup | ~4.7 ms | ~0.004 ms |
| Spectral reversal | ~9.3 ms | ~0.00045 ms |
| Spectral seven-color selection | ~9.4 ms | ~0.50 ms |
| Named path lookup | ~2.3 ms | ~0.002 ms |
| 25 reversed Spectral views, traced retained allocations | ~32.5 MB | ~3.3 KB |

Repeated report reads become cached immutable access. The first oriented report
still incurs its construction cost. Sampling 4,096 scalar positions remains
roughly 14–19 ms; it uses the unchanged scalar color conversion. Compact JSON
export is approximately 0.2–0.3 ms in this example. These are host measurements,
not timing gates or predictions for every figure.

Reproduce the comparison against the unchanged original factories:

```powershell
python tools/profile_runtime.py --legacy
python tools/profile_runtime.py --compare artifacts/runtime-profile-legacy.json
```

Raw results stay under ignored `artifacts/`. Remaining costs include cold JSON
reading/parsing, large full-report serialization, Python scalar sampling for
very large images and figure doctor's full copies/data hashing and pair audits.
Reuse designs or request compact exports for plotting; deeper lazy evidence
storage/vectorization would require a separate measured change.
