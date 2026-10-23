# Figure doctor

Use the same workflow with Matplotlib, UltraPlot and Plotly:

```python
from huevat import doctor

scene = doctor.inspect(fig)          # private copy; original untouched
print(scene.categories, scene.coverage)
diagnosis = doctor.diagnose(scene)
print(diagnosis["color_screen_pass"], diagnosis["unresolved_pairs"])

closer, separation, simple = doctor.propose(scene)
copy = doctor.preview(fig, separation)
gray = doctor.preview(fig, separation, condition="grayscale")
before = doctor.preview(fig, condition="deutan-100")

change = doctor.apply(fig, separation)  # explicit edit of supported styles
print(change.report["color_screen_pass"])
change.undo()                           # refuses to overwrite newer changes
```

Install the local checkout with `pip install ".[design,matplotlib]"`, or choose
`plotly`/`ultraplot` instead of `matplotlib`. `uv sync --locked --all-extras`
sets up all supported backends and the research examples. Importing
`huevat.doctor` loads no optional packages. Inspection uses the figure's own
backend; diagnosis and negotiation require the independent audit in `[design]`.
No default registrations or global plotting settings are changed.
Matplotlib/UltraPlot preview copies are unmanaged native figures: display them
in a notebook or save with `copy.savefig("preview.png")`. Inspection and preview
do not register hidden pyplot windows or change the active figure.

`closer` reduces Oklab change from supplied colors. `separation` prioritizes
nearby/crossing pairs under normal and all seven H1 simulated conditions.
`simple` adds fewer extra encodings, based on color/grayscale conflicts.
The first two use coordinated markers and dashes. These are bounded local
searches of the selected Clearer count-specific palette; objectives can converge
to the same color assignment. They do not guarantee global optimality.

All three retain an exact color-only report. A hard constraint can prevent a
passing result; the returned option then says so. Distinct markers or dashes
are structural redundancy hints, with human review pending. They never turn a
failed color screen into a pass. Review the native preview at the intended size.

## Keep category identities across figures

```python
options = doctor.propose(scene, locked={
    "Reference": {"color": "#4379a3"},
    "Treatment": {"marker": "square", "dash": "dash"},
})
next_scene = doctor.inspect(next_fig)
next_options = doctor.propose(next_scene, assignments=options[0].assignments)
```

Category identity is the exact label, independent of panel/trace order. Repeat
labels across panels intentionally share an encoding. Use different labels for
different meanings. Anonymous marks get local identities such as
`@axes/0/line/0`; label them to coordinate across figures. Retained assignments
reserve absent labels, and remain fixed when new categories appear. Conflicting
locks raise an error. There are at most twelve reserved categories in v1.

Colors use six-digit hex strings. Portable markers are `circle`, `square`,
`triangle`, `diamond`, `cross`, `triangle-down`, `none`; dashes are `solid`,
`dash`, `dot`, `dashdot`, `none`. A repair cannot remove a visible line or
scatter series. Native line widths, existing marker sizes, data and scales are
preserved. Adding markers to an unmarked Matplotlib/UltraPlot line uses 6 pt
markers at roughly twelve evenly spaced data indices; Plotly adds 6 px markers
at its original sample positions. Inspect both at the intended plotting size.

## Coverage and limits

| Content | Behavior |
| --- | --- |
| Ordinary Cartesian Line2D and uniform scatter | Read colors/alpha, marker face/edge, dashes, widths, labels and data; edit supported styles |
| UltraPlot | Native figure copy and Matplotlib-compatible artist inspection/edits |
| Plotly Cartesian `scatter` | Explicit numeric x/y, explicit mode and scalar line/marker colors; normal template style inheritance |
| Backgrounds and transparency | Composite encoded sRGB over each axes background; overlapping layers remain unmodeled |
| Repeated labels and absent/reordered categories | One assignment per exact identity; explicit retained map reserves absent labels |
| Uncertainty bands, images, scalar maps and colorbars | Inventory and preserve; no automatic palette, normalization or threshold edits |
| Error bars, bars, stems, specialized transforms, effects, variable/mapped styles | Retain and report outside editable coverage |
| Plotly unresolved renderer defaults, unsupported CSS colors, fills, animations, other trace families | Retain and report; explicit hex colors/numeric coordinates resolve common ambiguities |
| Legends | Update unambiguous axes-level native proxies; duplicate-label and figure-level legends retained/reported |

Scenes record scales, limits, labels, data hashes and the modeled styles.
Inspection does not draw or trigger changes in the original figure's lazy
autoscaling. Apply rejects a stale scene and rehearses setters on a copy first.
Native setter failures roll supported styles back; undo restores the exact
previous native style, including custom dashes and automatic marker colors.
Matplotlib stale checks cover the modeled scene; arbitrary internals of
unsupported custom artists are outside that fingerprint. Plotly also hashes its
full native JSON. Apply and undo hold native references; use them in the same
Python session, and do not mutate figures concurrently.

`color_screen_pass` refers to supported mark channels over modeled solid
backgrounds. Reports retain float/u8, normal/CVD Oklab and CAM02-UCS gates,
grayscale pair diagnostics and contrast against actual axes colors. A complete
figure or human-readability pass is never inferred. Previews transform supported
mark composites and backgrounds; unmodeled content and general decorations
remain unchanged. Preview metadata states that this is a partial simulation.

Crossing/nearby detection uses at most 128 sampled vertices per series, keeps
missing-data breaks and transforms log axes. It can miss fine features and does
not model glyph size or occlusion. Large figures also incur a full native copy
and full-data hashing cost, even though relationship geometry is bounded.
Neighboring-region repair and scalar-field palette negotiation are future work.

## Save a reproducible proposal

```python
saved_json = separation.to_json()
restored = doctor.load_proposal(saved_json)
change = doctor.apply(fig, restored)
```

The envelope includes a version, scene fingerprint, assignments, objective,
constraints, change list and audit evidence. Loading verifies the hash/schema;
application independently re-extracts the scene and repeats the exact native
audit. Supplied report claims are never trusted during application. A saved
proposal targets the same modeled scene and compatible backend environment;
use its assignment map to transfer identities to a different figure.

The [offline gallery](../research/doctor-v1/index.html) shows actual native
before/after figures, all H1 simulated conditions, grayscale, mixed content and
deliberately identical locked colors on both backgrounds. Reproduce its numeric
evidence with `python tools/build_doctor.py --check`; omit `--check` to render.
See [the predeclared protocol](METHODS_H4C.md) for the unchanged screen criteria.
