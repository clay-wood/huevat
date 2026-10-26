# API guide

```python
import huevat as hv
```

Start with the [quick start](QUICKSTART.md) or the [palette gallery](../README.md).

## Choose colors

| Function | Use |
| --- | --- |
| `categorical(n, background="light", style="clearer")` | Distinct categories; default palettes cover 2–12 colors |
| `sequential(background="light")` | Ordered values from low to high |
| `diverging(background="light")` | Values on either side of a center |
| `multihue(background="light")` | Ordered values with a wider hue range |
| `spectral(background="light")` | A diverging gradient with several hues |
| `gradient(name, background=None)` | One of eighteen supported gradients; defaults to light, `_d` selects dark, `_r` reverses |
| `gradient_names(family=None, domain=None)` | List named gradients, optionally filtered |
| `gradient_info(name)` | Read a named gradient's intended uses and direction |

Use `background="dark"` for dark figures. A categorical palette provides hex
strings in `.colors`. A gradient provides RGB tuples through `.at(t)`.

## Sample and inspect

| Operation | Use |
| --- | --- |
| `g.at(t)` | Read a color at a position from 0 to 1 |
| `g.reversed()` | Reverse a gradient |
| `g.discrete(n=9, context=None)` | Select evenly spaced colors; nine bins include a diverging neutral |
| `known_counts(g)` | List prepared counts that passed the checks |
| `nearby_counts(g, n, context=None)` | Find tested counts near the one requested |
| `optimized_discrete(g, n, context=None, grid=257, max_seconds=10)` | Search for better-spaced positions; requires `design` |
| `summarize(source)` | Read a short summary of the color checks |
| `source.report` | Read the full numerical results |

Some counts fail the color checks; an unlisted count has not necessarily failed.
Sample positions do not set physical data-bin boundaries.
Explicit even counts retain their requested size and omit the neutral midpoint.
Named suffixes compose in either order: `gradient("balance_d_r")` equals
`gradient("balance", background="dark").reversed()`. `_d` conflicts with an
explicit `background="light"`; repeated suffixes are invalid. `gradient_info`
accepts suffixes and returns the base route's metadata; `gradient_names` lists
base names.

## Save and load

```python
hv.export(palette, labels=labels).write("palette.json")
saved = hv.load_export(open("palette.json", encoding="utf-8").read())
palette = saved.design
colors_by_label = saved.color_map

hv.export(gradient, n=7, format="csv").write("colors.csv")
```

`export(design, format="json", n=None, context=None, labels=None, source=None)`
supports `json`, `csv`, `hex` and `css`. The result has `.text`, `.report` and
`.write(path)`. JSON preserves the design and labels; CSV and hex provide color
lists. CSS approximates continuous gradients with checked color stops.
Its optional `tolerance=.002` and `max_stops=1025` control that approximation.

For JSON, export a gradient with `n=7` or supply its original gradient as
`export(palette, source=gradient)`. Categorical palettes and palettes from
`optimized_discrete` already contain the information needed to save them.
Labels must be unique and match the number of colors.

`load_export(value, validate=True)` returns `.design`, `.source`, `.labels`
and, for labeled palettes, `.color_map`. Loading unfamiliar designs can require
`design` to repeat the checks. `validate=False` skips those checks and leaves
the result unvalidated.

You can also save with `.to_recipe()` or `.to_json()` and restore with
`load_recipe(value, validate=True)`.

## Find a particular design

`design_ids(family=None, background=None, role=None)` lists saved designs.
`design_info(id)` describes one; `get_design(id)` loads it. Roles are `default`,
`legacy` and `collection`. Saving an ID lets you request the same design later.

## Plotting and Figure doctor

Adapters live in `huevat.adapters.matplotlib`, `.plotly` and `.ultraplot`.
See the [complete plotting examples](../examples/README.md).

Figure doctor provides `inspect`, `diagnose`, `propose`, `preview`, `apply` and
`load_proposal`. Its suggestions require the `design` extra. See the
[Figure doctor guide](FIGURE_DOCTOR.md).

## Errors

`ValueError` indicates an invalid argument. `QualityError` means a color check
failed. `ConstraintConflictError` means the fixed gradient cannot meet the
requested count under the selected rules. `SearchExhaustedError` means the
search ended without finding a passing result. Color-check errors include
their numerical report.

The [methods notes](METHODS_H1.md) describe the checks and their limits.
