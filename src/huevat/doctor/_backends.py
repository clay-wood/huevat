"""Lazy native readers/setters. Unsupported content is never silently repaired."""
from copy import deepcopy
import hashlib
import json
import math
import re

from ..gradients import fingerprint, _thaw
from ..space import from_hex, to_hex, linearize, encode
from ..vision import simulate

MPL_MARKER = {"circle": "o", "square": "s", "triangle": "^", "diamond": "D",
              "cross": "X", "triangle-down": "v", "none": "None"}
MPL_DASH = {"solid": "-", "dash": "--", "dot": ":", "dashdot": "-.", "none": "None"}
PLOT_MARKER = {**{k: k for k in MPL_MARKER}, "triangle": "triangle-up", "none": "circle"}
PLOT_MARKER["cross"] = "x"


def backend(figure):
    modules = [cls.__module__ for cls in type(figure).__mro__]
    if any(m.startswith("plotly.") for m in modules): return "plotly"
    if any(m.startswith("matplotlib.figure") for m in modules):
        return "ultraplot" if any(m.startswith("ultraplot.") for m in modules) else "matplotlib"
    raise TypeError("Figure doctor supports Matplotlib, UltraPlot and Plotly figures")


def clone(figure):
    """Native copy without pyplot manager registration or interactive draws.

    Figure's default pickle/deepcopy protocol re-registers pyplot figures and
    may call draw_if_interactive. Use the same state protocol with that restore
    flag removed, seeding the self-reference before copying axes and artists.
    """
    if backend(figure) == "plotly": return deepcopy(figure)
    copied = object.__new__(type(figure))
    state = figure.__getstate__()
    state.pop("_restore_to_pylab", None)
    copied.__setstate__(deepcopy(state, {id(figure): copied}))
    return copied


def _hash_array(value):
    # Native arrays can contain masked/non-finite data; bytes keep the exact
    # payload without admitting NaN to the portable JSON scene.
    import numpy as np
    a = np.ma.asarray(value)
    if a.dtype.kind == "O": payload = repr(a.tolist()).encode("utf-8")
    else: payload = a.tobytes()
    return hashlib.sha256(str((a.shape, str(a.dtype))).encode() + payload +
                          np.ma.getmaskarray(a).tobytes()).hexdigest()


def _points(x, y, xscale="linear", yscale="linear", limits=None):
    import numpy as np
    x, y = np.ma.asarray(x, dtype=float).filled(np.nan), np.ma.asarray(y, dtype=float).filled(np.nan)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y): raise ValueError("Expected paired 1D data")
    if len(x) == 0: return []
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.log10(x) if xscale == "log" else x
        y = np.log10(y) if yscale == "log" else y
    indices = np.unique(np.linspace(0, len(x)-1, min(len(x), 128)).astype(int))
    ranges = limits or [(float(np.nanmin(a)), float(np.nanmax(a))) if np.isfinite(a).any() else (0, 1) for a in (x, y)]
    out = []
    for index, i in enumerate(indices):
        # A decimated segment may never bridge a missing-data gap.
        if index and (not np.isfinite(x[indices[index-1]:i+1]).all() or
                      not np.isfinite(y[indices[index-1]:i+1]).all()): out.append(None)
        point = [(float(a[i])-lo)/(hi-lo or 1) for a, (lo, hi) in zip((x, y), ranges)]
        out.append(point if all(math.isfinite(v) for v in point) else None)
    return out


def _channel(kind, rgba, alpha=None):
    rgba = tuple(float(v) for v in rgba)
    return {"kind": kind, "rgb": list(rgba[:3]), "alpha": float(rgba[3] if alpha is None else alpha)}


def extract(figure):
    kind = backend(figure)
    result = _plotly(figure) if kind == "plotly" else _mpl(figure)
    result["backend"] = kind
    result["version"] = "h4c-doctor-v1"
    result["coverage"] = {"editable_marks": len(result["marks"]),
        "read_only": len(result["read_only"]), "unsupported": len(result["unsupported"]),
        "complete": not (result["read_only"] or result["unsupported"] or result["warnings"]),
        "scope": "modeled Cartesian marks over solid backgrounds; no occlusion model"}
    return result


def _mpl(fig):
    import numpy as np
    from matplotlib.colors import to_rgba
    from matplotlib.collections import PathCollection
    from matplotlib.markers import MarkerStyle
    result = dict(marks=[], axes=[], read_only=[], unsupported=[], warnings=[])
    paper = fig.get_facecolor()
    if paper[3] != 1: result["warnings"].append("Transparent figure background: opaque display backing unknown")
    result["paper"] = list(paper)
    result["size"] = list(map(float, fig.get_size_inches()))
    result["dpi"] = float(fig.dpi)
    for ai, ax in enumerate(fig.axes):
        panel = f"axes/{ai}"
        face = ax.get_facecolor()
        bg = [face[i]*face[3]+paper[i]*(1-face[3]) for i in range(3)]
        axis = {"key": panel, "background": bg, "background_alpha": float(face[3]),
                "xscale": ax.get_xscale(), "yscale": ax.get_yscale(),
                "xlim": list(map(float, ax.get_xlim())), "ylim": list(map(float, ax.get_ylim())),
                "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(), "title": ax.get_title(),
                "position": list(map(float, ax.get_position().bounds))}
        result["axes"].append(axis)
        colorbar = hasattr(ax, "_colorbar")
        if colorbar:
            result["read_only"].append({"key": panel, "type": "colorbar", "reason": "normalization and ticks preserved"})
            continue
        eligible = ax.name == "rectilinear" and axis["xscale"] in ("linear", "log") and axis["yscale"] in ("linear", "log")
        limits = []
        for dim in ("x", "y"):
            vals = axis[dim+"lim"]
            limits.append([math.log10(v) for v in vals] if axis[dim+"scale"] == "log" else vals)
        def reject(key, obj, reason):
            result["unsupported"].append({"key": key, "type": type(obj).__name__, "reason": reason})
        contained = set()
        for ci, container in enumerate(ax.containers):
            contained.update(id(child) for child in container.get_children())
            reject(f"{panel}/container/{ci}", container, "container semantics (error bars, stems, bars) preserved")
        def common(key, obj, x, y, channels, kind, marker, dash, width, line, marker_on, **extra):
            category = obj.get_label()
            category = category if isinstance(category, str) and category and not category.startswith("_") else "@"+key
            if any(c["alpha"] < 1 for c in channels):
                result["warnings"].append(key+": transparency modeled over axes only; overlaps unmodeled")
            return {"key": key, "panel": panel, "category": category, "kind": kind,
                "channels": channels, "marker": marker, "dash": dash, "width": float(width),
                "line_visible": line, "marker_visible": marker_on, "background": bg,
                "data_sha256": fingerprint([_hash_array(x), _hash_array(y)]),
                "points": _points(x, y, axis["xscale"], axis["yscale"], limits), **extra}
        for li, obj in enumerate(ax.lines):
            if not obj.get_visible() or id(obj) in contained: continue
            key = f"{panel}/line/{li}"
            if not eligible or obj.get_transform() != ax.transData or obj.get_path_effects() or obj.get_gapcolor() is not None:
                reject(key, obj, "special axes/transform, path effect or gap color"); continue
            if obj.get_drawstyle() != "default": reject(key, obj, "step/other drawstyle"); continue
            try:
                channels = []
                line = obj.get_linestyle() not in ("None", "", " ") and obj.get_linewidth() > 0
                marker_on = obj.get_marker() not in ("None", None, "", " ") and obj.get_markersize() > 0
                if line:
                    rgba = to_rgba(obj.get_color(), alpha=obj.get_alpha())
                    if rgba[3]: channels.append(_channel("line", rgba))
                    else: line = False
                if marker_on:
                    for name, color in (("face", obj.get_markerfacecolor()), ("edge", obj.get_markeredgecolor())):
                        rgba = to_rgba(color, alpha=obj.get_alpha())
                        if rgba[3] and (name != "edge" or obj.get_markeredgewidth() > 0):
                            channels.append(_channel(name, rgba))
                if not channels: continue
                x, y = obj.get_data(orig=False)
                marker = next((k for k, v in MPL_MARKER.items() if v == obj.get_marker()), str(obj.get_marker()))
                dash = next((k for k, v in MPL_DASH.items() if v == obj.get_linestyle()), str(obj.get_linestyle()))
                # Preserve custom dash offset/sequence as fingerprint evidence.
                extra = {"dash_pattern": repr(getattr(obj, "_unscaled_dash_pattern", None)),
                    "marker_size": float(obj.get_markersize()), "markevery": repr(obj.get_markevery()),
                    "zorder": float(obj.get_zorder())}
                result["marks"].append(common(key, obj, x, y, channels, "line", marker, dash,
                                                    obj.get_linewidth(), line, marker_on, **extra))
            except (ValueError, TypeError, OverflowError) as error: reject(key, obj, str(error))
        for ci, obj in enumerate(ax.collections):
            if not obj.get_visible() or id(obj) in contained: continue
            key = f"{panel}/collection/{ci}"
            array = obj.get_array()
            if array is not None:
                norm = obj.norm
                result["read_only"].append({"key": key, "type": type(obj).__name__, "reason": "scalar mapping preserved",
                    "data_sha256": _hash_array(array), "cmap": obj.cmap.name,
                    "norm": type(norm).__name__, "vmin": norm.vmin, "vmax": norm.vmax,
                    "boundaries": list(map(float, norm.boundaries)) if hasattr(norm, "boundaries") else None})
                continue
            if not isinstance(obj, PathCollection):
                result["read_only"].append({"key": key, "type": type(obj).__name__,
                    "reason": "band/collection retained; layering unmodeled", "paths": len(obj.get_paths()),
                    "geometry_sha256": fingerprint([_hash_array(p.vertices) for p in obj.get_paths()]),
                    "face_sha256": _hash_array(obj.get_facecolors())})
                continue
            if not eligible or obj.get_offset_transform() != ax.transData or len(obj.get_paths()) != 1 or obj.get_path_effects():
                reject(key, obj, "nonstandard scatter transform/paths/effects"); continue
            try:
                faces, edges = obj.get_facecolors(), obj.get_edgecolors()
                if len(faces) > 1 or len(edges) > 1 or len(obj.get_sizes()) != 1 or len(obj.get_linewidths()) != 1:
                    reject(key, obj, "variable scatter color or size"); continue
                if obj.get_sizes()[0] <= 0: continue
                channels = [_channel(name, colors[0]) for name, colors in (("face", faces), ("edge", edges))
                            if len(colors) and colors[0, 3] > 0 and (name != "edge" or obj.get_linewidths()[0] > 0)]
                if not channels: continue
                offsets = obj.get_offsets()
                marker = "custom"
                for name, code in MPL_MARKER.items():
                    if name == "none": continue
                    ms = MarkerStyle(code); path = ms.get_path().transformed(ms.get_transform())
                    p = obj.get_paths()[0]
                    if p.vertices.shape == path.vertices.shape and np.array_equal(p.vertices, path.vertices): marker = name; break
                result["marks"].append(common(key, obj, offsets[:, 0], offsets[:, 1], channels, "scatter", marker,
                    "none", float(obj.get_linewidths()[0]), False, True,
                    marker_size=float(obj.get_sizes()[0]), marker_path=_hash_array(obj.get_paths()[0].vertices),
                    zorder=float(obj.get_zorder())))
            except (ValueError, TypeError, OverflowError) as error: reject(key, obj, str(error))
        for ii, obj in enumerate(ax.images):
            result["read_only"].append({"key": f"{panel}/image/{ii}", "type": type(obj).__name__,
                "reason": "image/scalar mapping preserved", "data_sha256": _hash_array(obj.get_array()),
                "cmap": obj.cmap.name, "norm": type(obj.norm).__name__, "vmin": obj.norm.vmin, "vmax": obj.norm.vmax})
        for pi, obj in enumerate(ax.patches):
            if obj.get_visible(): reject(f"{panel}/patch/{pi}", obj, "patch/neighboring-region repair outside v1")
        for ti, obj in enumerate(ax.texts):
            if obj.get_visible(): reject(f"{panel}/text/{ti}", obj, "annotation retained; contrast not audited")
        if ax.artists or ax.tables: result["warnings"].append(panel+": custom artists/tables outside coverage")
        if ax.child_axes: result["warnings"].append(panel+": inset/child axes retained outside coverage")
        legend = ax.get_legend()
        if legend is not None:
            labels = [t.get_text() for t in legend.get_texts()]
            result.setdefault("legends", []).append({"panel": panel, "labels": labels})
            if len(labels) != len(set(labels)):
                result["warnings"].append(panel+": ambiguous repeated legend labels; proxies retained")
    if fig.legends or fig.artists or fig.texts or fig.images or fig.patches or fig.lines or fig.subfigs:
        result["warnings"].append("Figure-level legends/artists/text/images/subfigures retained; outside proxy and contrast coverage")
    return result


def _css(value):
    if not isinstance(value, str): raise ValueError("Unresolved/array color; supply an explicit scalar sRGB color")
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value): return (*from_hex(value), 1.)
    if re.fullmatch(r"#[0-9a-fA-F]{3}", value): return (*from_hex("#"+"".join(c*2 for c in value[1:])), 1.)
    named = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "blue": "#0000ff",
             "green": "#008000", "gray": "#808080", "grey": "#808080", "transparent": "#000000"}
    if value.lower() in named: return (*from_hex(named[value.lower()]), 0. if value.lower() == "transparent" else 1.)
    match = re.fullmatch(r"rgba?\(([^)]+)\)", value)
    if match:
        nums = [float(v.strip()) for v in match[1].split(",")]
        if len(nums) in (3, 4) and all(math.isfinite(v) and 0 <= v <= 255 for v in nums[:3]):
            alpha = nums[3] if len(nums) == 4 else 1.
            if 0 <= alpha <= 1: return (*(v/255 for v in nums[:3]), alpha)
    raise ValueError("Color not resolved in v1; use #rrggbb or rgb/rgba numeric channels")


def _merge(base, own):
    result = deepcopy(base)
    for k, v in own.items():
        result[k] = _merge(result.get(k, {}), v) if isinstance(v, dict) else deepcopy(v)
    return result


def _plotly(fig):
    # Plotly's JSON encoder normalizes NumPy arrays to binary JSON containers.
    serialized = fig.to_json()
    native = json.loads(serialized)
    result = dict(marks=[], axes=[], read_only=[], unsupported=[], warnings=[],
                  native_sha256=hashlib.sha256(serialized.encode()).hexdigest())
    template = native.get("layout", {}).get("template", {})
    layout = _merge(template.get("layout", {}), native.get("layout", {}))
    try:
        paper = _css(layout.get("paper_bgcolor", "#ffffff"))
        bg = _css(layout.get("plot_bgcolor", "#ffffff"))
    except ValueError as error:
        result["unsupported"].append({"key": "layout", "type": "background", "reason": str(error)})
        result["warnings"].append("Background unresolved; editable marks excluded rather than assuming a canvas color")
        return result
    actual_bg = [bg[i]*bg[3]+paper[i]*(1-bg[3]) for i in range(3)]
    result["paper"] = list(paper)
    if paper[3] != 1: result["warnings"].append("Transparent paper background: opaque backing unknown")
    if fig.frames: result["warnings"].append("Animation frames retained; current-frame repairs unsupported")
    if layout.get("shapes") or layout.get("images") or layout.get("annotations"):
        result["warnings"].append("Layout shapes/images/annotations retained and unmodeled")
    if template.get("layout", {}).get("shapes") or template.get("layout", {}).get("images"):
        result["warnings"].append("Template overlays retained and unmodeled")
    type_counts = {}
    for i, obj in enumerate(fig.data):
        key = f"trace/{i}"
        own = native["data"][i]
        defaults = template.get("data", {}).get(obj.type, [])
        type_index = type_counts.get(obj.type, 0); type_counts[obj.type] = type_index+1
        trace = _merge(defaults[type_index % len(defaults)] if defaults else {}, own)
        if trace.get("visible") in (False, "legendonly"): continue
        reason = None
        if obj.type != "scatter": reason = "trace type outside editable Cartesian scatter coverage"
        if trace.get("fill", "none") != "none": reason = "filled trace/layering preserved"
        if trace.get("error_x", {}).get("visible") or trace.get("error_y", {}).get("visible"):
            reason = "error bars preserved"
        if fig.frames: reason = "animated figure"
        xkey = trace.get("xaxis", "x").replace("x", "xaxis", 1)
        ykey = trace.get("yaxis", "y").replace("y", "yaxis", 1)
        panel = xkey+"/"+ykey
        axis = {"key": panel, "background": actual_bg, "xscale": layout.get(xkey, {}).get("type", "linear"),
                "yscale": layout.get(ykey, {}).get("type", "linear"),
                "xlim": layout.get(xkey, {}).get("range"), "ylim": layout.get(ykey, {}).get("range"),
                "xaxis": layout.get(xkey, {}), "yaxis": layout.get(ykey, {})}
        # JSON-safe: layout contains only validated Plotly scalar/list values.
        if panel not in {a["key"] for a in result["axes"]}: result["axes"].append(axis)
        if axis["xscale"] not in ("linear", "log") or axis["yscale"] not in ("linear", "log"):
            reason = "non-numeric/category/date scale"
        if reason:
            result["unsupported"].append({"key": key, "type": obj.type, "reason": reason}); continue
        try:
            mode = trace.get("mode")
            if mode not in ("lines", "markers", "lines+markers"):
                raise ValueError("Unresolved/text mode; set lines, markers or lines+markers explicitly")
            if obj.x is None or obj.y is None: raise ValueError("Explicit numeric x and y required")
            line, marker_on = "lines" in mode, "markers" in mode
            ls, ms = trace.get("line", {}), trace.get("marker", {})
            if ls.get("shape", "linear") != "linear" or trace.get("stackgroup"):
                raise ValueError("Spline/step/stacked traces outside v1")
            if ms.get("coloraxis") or ms.get("colorscale") or ms.get("showscale"):
                raise ValueError("Scalar marker mapping preserved")
            alpha = trace.get("opacity", 1.)
            channels = []
            if line:
                c = _css(ls.get("color")); channels.append({**_channel("line", c, c[3]*alpha), "color_alpha": c[3]})
            if marker_on:
                c = _css(ms.get("color")); channels.append({**_channel("face", c, c[3]*alpha*ms.get("opacity", 1.)), "color_alpha": c[3]})
                if ms.get("line", {}).get("width", 0) > 0:
                    c = _css(ms["line"].get("color")); channels.append({**_channel("edge", c, c[3]*alpha*ms.get("opacity", 1.)), "color_alpha": c[3]})
                if not isinstance(ms.get("size", 6), (int, float)) or not isinstance(ms.get("symbol", "circle"), str):
                    raise ValueError("Variable marker size/symbol outside v1")
            if not channels or any(not math.isfinite(c["alpha"]) for c in channels): raise ValueError("Invalid alpha")
            if any(c["alpha"] < 1 for c in channels): result["warnings"].append(key+": transparency over axes only; overlaps unmodeled")
            result["marks"].append({"key": key, "panel": panel, "category": str(trace.get("name") or "@"+key),
                "kind": "line" if line else "scatter", "channels": channels, "background": actual_bg,
                "line_visible": line, "marker_visible": marker_on, "marker": ms.get("symbol", "circle") if marker_on else "none",
                "dash": ls.get("dash", "solid") if line else "none", "width": float(ls.get("width", 2.)),
                "marker_size": float(ms.get("size", 6)), "opacity": alpha, "marker_opacity": ms.get("opacity", 1.),
                "data_sha256": fingerprint([_hash_array(obj.x), _hash_array(obj.y)]),
                "points": _points(obj.x, obj.y, axis["xscale"], axis["yscale"])})
        except (TypeError, ValueError, OverflowError) as error:
            result["unsupported"].append({"key": key, "type": obj.type, "reason": str(error)})
    # Per-series normalization would invent relationships; normalize all points
    # with shared panel ranges from their joint data (or explicit axis range).
    for axis in result["axes"]:
        members = [m for m in result["marks"] if m["panel"] == axis["key"]]
        if not members: continue
        raw = []
        for m in members:
            obj = fig.data[int(m["key"].split("/")[1])]
            raw.append(_points(obj.x, obj.y, axis["xscale"], axis["yscale"], [(0, 1), (0, 1)]))
        bounds = []
        for dim, name in enumerate(("xlim", "ylim")):
            nums = [p[dim] for points in raw for p in points if p is not None]
            bounds.append(axis[name] or [min(nums, default=0.), max(nums, default=1.)])
        for m, points in zip(members, raw):
            m["points"] = [None if p is None else [(v-lo)/(hi-lo or 1) for v, (lo, hi) in zip(p, bounds)] for p in points]
    return result


def _target(fig, mark):
    bits = mark["key"].split("/")
    if bits[0] == "trace": return fig.data[int(bits[1])]
    ax = fig.axes[int(bits[1])]
    return (ax.lines if bits[2] == "line" else ax.collections)[int(bits[3])]


def _set_mpl(obj, mark, style):
    from matplotlib.markers import MarkerStyle
    color = style["color"]
    channels = {c["kind"]: c for c in mark["channels"]}
    def rgba(kind): return (*from_hex(color), channels.get(kind, mark["channels"][0])["alpha"])
    if mark["kind"] == "line":
        if "line" in channels: obj.set_color(rgba("line"))
        if mark["line_visible"]:
            if style["dash"] == "none": raise ValueError("Repair cannot remove an existing line")
            obj.set_linestyle(MPL_DASH[style["dash"]])
        obj.set_marker(MPL_MARKER[style["marker"]])
        if style["marker"] != "none":
            if not mark["marker_visible"]:
                obj.set_markersize(6); obj.set_markevery(max(1, len(obj.get_xdata())//12))
            # Existing hollow markers retain their transparent face.
            if "face" in channels or not mark["marker_visible"]: obj.set_markerfacecolor(rgba("face"))
            if "edge" in channels or not mark["marker_visible"]: obj.set_markeredgecolor(rgba("edge"))
    else:
        if style["marker"] == "none": raise ValueError("Scatter markers cannot be removed")
        ms = MarkerStyle(MPL_MARKER[style["marker"]])
        obj.set_paths([ms.get_path().transformed(ms.get_transform())])
        for name, setter in (("face", obj.set_facecolor), ("edge", obj.set_edgecolor)):
            ch = next((c for c in mark["channels"] if c["kind"] == name), None)
            if ch: setter((*from_hex(color), ch["alpha"]))


def _legend(fig, scene, assignments):
    for entry in scene.get("legends", []):
        legend = fig.axes[int(entry["panel"].split("/")[1])].get_legend()
        if len(entry["labels"]) != len(set(entry["labels"])): continue
        handles = getattr(legend, "legend_handles", [])
        for label, obj in zip(entry["labels"], handles):
            marks = [m for m in scene["marks"] if m["panel"] == entry["panel"] and m["category"] == label]
            if marks and label in assignments:
                from matplotlib.lines import Line2D
                from matplotlib.collections import PathCollection
                if isinstance(obj, (Line2D, PathCollection)):
                    mark = deepcopy(marks[0]); mark["kind"] = "line" if isinstance(obj, Line2D) else "scatter"
                    _set_mpl(obj, mark, assignments[label])
                    if isinstance(obj, Line2D): obj.set_markevery([len(obj.get_xdata())//2])


def mutate(fig, scene, assignments):
    if backend(fig) == "plotly":
        for m in scene["marks"]:
            obj, style = _target(fig, m), assignments[m["category"]]
            channels = {c["kind"]: c for c in m["channels"]}
            def color(kind):
                alpha = channels.get(kind, m["channels"][0]).get("color_alpha", 1.)
                rgb = [round(v*255) for v in from_hex(style["color"])]
                return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha})"
            if m["line_visible"]:
                if style["dash"] == "none": raise ValueError("Repair cannot remove an existing line")
                obj.line.update(color=color("line"), dash=style["dash"])
            if style["marker"] == "none" and m["kind"] == "scatter": raise ValueError("Scatter markers cannot be removed")
            mode = "lines" if m["line_visible"] else ""
            if style["marker"] != "none": mode += ("+" if mode else "")+"markers"
            if not mode: raise ValueError("Repair cannot hide a series")
            obj.mode = mode
            if style["marker"] != "none":
                obj.marker.symbol = PLOT_MARKER[style["marker"]]
                obj.marker.color = color("face")
                if "edge" in channels: obj.marker.line.color = color("edge")
                if not m["marker_visible"]: obj.marker.size = 6
        return
    for m in scene["marks"]: _set_mpl(_target(fig, m), m, assignments[m["category"]])
    _legend(fig, scene, assignments)


def snapshot(fig, scene):
    if backend(fig) == "plotly":
        states = [(obj, deepcopy(obj.to_plotly_json())) for obj in [_target(fig, m) for m in scene["marks"]]]
        def restore():
            for obj, data in states:
                for field in ("line", "marker", "mode"):
                    obj[field] = deepcopy(data.get(field))
        return restore
    objects = [_target(fig, m) for m in scene["marks"]]
    for ax in fig.axes:
        legend = ax.get_legend()
        if legend: objects.extend(getattr(legend, "legend_handles", []))
    from matplotlib.lines import Line2D
    from matplotlib.collections import PathCollection
    states = []
    for obj in objects:
        if isinstance(obj, Line2D):
            data = {name: deepcopy(getattr(obj, "get_"+name)()) for name in
                    ("color", "marker", "markerfacecolor", "markeredgecolor", "markersize", "markevery")}
            # Getters resolve 'auto' colors; keep their native sentinel so undo
            # also restores future color inheritance, not just today's RGB.
            data["markerfacecolor"] = deepcopy(obj._markerfacecolor)
            data["markeredgecolor"] = deepcopy(obj._markeredgecolor)
            pattern = getattr(obj, "_unscaled_dash_pattern", None)
            data["linestyle"] = deepcopy(pattern if pattern and pattern[1] is not None else obj.get_linestyle())
            states.append((obj, data))
        elif isinstance(obj, PathCollection):
            states.append((obj, {"paths": deepcopy(obj.get_paths()), "facecolor": obj.get_facecolors().copy(),
                                 "edgecolor": obj.get_edgecolors().copy()}))
    def restore():
        for obj, data in states:
            for name, value in data.items(): getattr(obj, "set_"+name)(deepcopy(value))
    return restore


def simulate_copy(fig, scene, condition, report):
    from ..references import load_profile
    conditions = load_profile()["conditions"] + ["grayscale"]
    if condition not in conditions: raise ValueError("Choose normal, grayscale or an H1 CVD condition")
    if condition != "normal" and "paper" not in scene:
        raise ValueError("Background unresolved; supply an explicit sRGB background before simulation")
    def transform(rgb):
        if condition == "normal": return tuple(rgb)
        if condition == "grayscale":
            v = encode(sum(w*linearize(c) for w, c in zip((.2126, .7152, .0722), rgb)))
            return (v, v, v)
        name, severity = condition.rsplit("-", 1)
        return simulate(rgb, name, severity=int(severity))
    if condition != "normal":
        if backend(fig) == "plotly":
            fig.layout.paper_bgcolor = to_hex(transform(scene["paper"][:3]))
            if scene["axes"]: fig.layout.plot_bgcolor = to_hex(transform(scene["axes"][0]["background"]))
            for m in scene["marks"]:
                obj = _target(fig, m)
                for c in m["channels"]:
                    # Transform composite, then make opaque: simulation must
                    # follow compositing, since CVD is nonlinear in sRGB.
                    rgb = [v*c["alpha"]+b*(1-c["alpha"]) for v, b in zip(c["rgb"], m["background"])]
                    color = to_hex(transform(rgb))
                    if c["kind"] == "line": obj.line.color = color
                    elif c["kind"] == "face": obj.marker.color = color
                    else: obj.marker.line.color = color
                obj.opacity = 1.; obj.marker.opacity = 1.
        else:
            fig.patch.set_facecolor(transform(scene["paper"][:3]))
            for a in scene["axes"]: fig.axes[int(a["key"].split("/")[1])].set_facecolor(transform(a["background"]))
            for m in scene["marks"]:
                obj = _target(fig, m)
                for c in m["channels"]:
                    rgb = [v*c["alpha"]+b*(1-c["alpha"]) for v, b in zip(c["rgb"], m["background"])]
                    color = transform(rgb)
                    name = {"line": "color", "face": "markerfacecolor", "edge": "markeredgecolor"}[c["kind"]] if m["kind"] == "line" else c["kind"]+"color"
                    getattr(obj, "set_"+name)(color)
                obj.set_alpha(None)
            # Simulate the edited proxies from their native actual colors.
            from matplotlib.colors import to_rgba
            for ax in fig.axes:
                legend = ax.get_legend()
                if not legend: continue
                for obj in getattr(legend, "legend_handles", []):
                    for name in ("color", "markerfacecolor", "markeredgecolor"):
                        if hasattr(obj, "get_"+name):
                            try: getattr(obj, "set_"+name)(transform(to_rgba(getattr(obj, "get_"+name)())[:3]))
                            except (ValueError, TypeError): pass
    metadata = {"version": "h4c-doctor-v1", "condition": condition,
        "complete_simulation": False, "modeled_marks_complete": bool(scene["coverage"]["complete"]),
        "coverage": scene["coverage"],
        "report": _thaw(report), "note": "Only supported marks and backgrounds simulated; unmodeled content retained"}
    # Plotly forbids arbitrary public attributes; its meta field is data-only.
    if backend(fig) == "plotly":
        existing = fig.layout.meta
        fig.layout.meta = {"huevat_doctor_preview": metadata, "original_meta": existing}
    else: fig.huevat_doctor_preview = metadata
    return fig
