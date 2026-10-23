# H4c figure doctor: protocol v1

Declared October 23, 2026, before implementation and example selection.
The H1 numerical thresholds and all existing designs remain frozen.

The API is `inspect → diagnose/propose → preview → apply`. Inspection and
preview operate on copies. Only explicit `apply` changes the supplied figure;
its returned change supports guarded undo. Proposals are data-only, immutable,
versioned and hashed. Loading does not trust supplied audit claims: application
audits the current scene and exact proposed encodings again. Stale scenes fail
before mutation. Category identity is the exact label, sorted independently of
artist order. Anonymous marks have local identities. An explicit retained
assignment map reserves absent categories across related figures; locks are
hard preferences and conflicting locks fail.

Initial editable coverage is ordinary Cartesian Matplotlib/UltraPlot Line2D
and uniform-color scatter PathCollection, and Plotly Cartesian scatter traces
with explicit numeric x/y, mode and scalar line/marker colors. Specialized
transforms, variable styles, mapped colors, filled traces, error bars, animations,
and unresolved renderer/template defaults are reported instead of guessed.
Scalar fields/colorbars and uncertainty bands are inventoried and preserved.
Their presence, shading, complex layering, unsupported content or transparent
marks prevents a complete-figure pass. Numerical evidence applies only to
modeled marks over their solid axes background. Color, alpha, marker faces and
edges, dashes, widths, scales, ranges and data hashes are retained in the scene.

For each axes/mark channel, composite encoded sRGB over the actual opaque
background (alpha-over in display RGB). Audit float and nearest-u8 composites
with every H1 normal/CVD Oklab and CAM02-UCS all-pair criterion and the unchanged
3:1 contrast criterion against that actual background. Compare distinct
categories within panels; identical labels are not different categories.
Grayscale remains an audit, using the H1 normal-distance levels as a
conservative prompt for redundant encodings, not a new accessibility gate.
Do not replace a failed color-only status with a joint-encoding pass.

Figure relationships use a bounded geometric screen: at most 128 evenly spaced
vertices per series in normalized axes coordinates, with missing-data breaks
retained; crossing line segments and nearest sampled points within 0.03 axes
units get extra weight. This finite proxy can miss narrow features and does not
model occlusion, line width, glyph size, or actual human discrimination. Log
axes are transformed before comparison; unsupported scales are excluded.

Negotiation searches permutations of the existing Clearer count-specific
palette, retaining exact locked/reserved colors. Three deterministic objectives
are offered: lower Oklab change from supplied colors; larger weighted worst-CVD
distance on nearby/crossing pairs; and fewer extra encodings. Pairwise swaps
are bounded to 12 passes; they claim a local search, not global optimality.
All baseline pairs are audited, regardless of relationship weights. Results
that fail retain the failure and are marked for review; no thresholds relax.

Portable encodings use six familiar marker shapes and four dash styles. The
coordinated alternative assigns distinct marker/dash combinations; the simple
alternative adds encodings only along grayscale/color-confusable panel edges.
Locks may leave unresolved conflicts, which are reported. Distinct symbols are
a structural redundancy check, not a numerical readability certificate.
No data, physical thresholds, normalization, sign, scales or category labels
are edited. Scalar-field palette repair and neighboring-region optimization
remain outside v1 editable coverage.

Native previews retain the actual plot and transform supported mark colors and
backgrounds for normal, the seven H1 CVD conditions and grayscale. They identify
unsupported/untransformed content; they are partial simulations when coverage
is incomplete. The original is never recolored for simulation. Legend proxies
associated unambiguously with supported labels are updated with their marks.

Acceptance covers repeat/reordered/absent labels, hard locks, crossing lines,
transparent bands, scalar maps/colorbars, unsupported artists, mixed axes
backgrounds, native three-backend copies, stale guards, transactional rollback,
undo, serialization, optional imports and honest failed-color repairs.

Backend contracts checked against primary documentation:
[Matplotlib Line2D](https://matplotlib.org/stable/api/_as_gen/matplotlib.lines.Line2D.html),
[PathCollection](https://matplotlib.org/stable/api/collections_api.html),
[Plotly scatter](https://plotly.com/python/reference/scatter/) and
[Plotly templates](https://plotly.com/python/templates/).
Template defaults are resolved conservatively, rather than calling a browser
renderer during inspection.
