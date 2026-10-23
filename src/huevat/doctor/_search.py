"""Bounded deterministic palette negotiation using the selected Clearer designs."""
from copy import deepcopy
from collections.abc import Mapping
import math
from itertools import combinations

from ..categorical import categorical
from ..space import from_hex, to_hex, srgb_to_oklab
from ..vision import simulate
from ..gradients import _thaw
from . import VERSION, MARKERS, DASHES, _styles
from ._audit import audit, relationships


def _preferences(locked, assignments):
    reserved = {} if assignments is None else _thaw(assignments)
    _styles(reserved)
    locks = {} if locked is None else _thaw(locked)
    if not isinstance(locks, Mapping): raise ValueError("Locked preferences must be a category mapping")
    for category, fields in locks.items():
        if not isinstance(category, str) or not category or not isinstance(fields, Mapping) or not fields:
            raise ValueError("Locks need a category and at least one style preference")
        if set(fields)-{"color", "marker", "dash"}: raise ValueError("Unknown locked preference")
        for k, v in fields.items():
            if k == "color": from_hex(v)
            elif v not in (MARKERS if k == "marker" else DASHES): raise ValueError("Unknown locked encoding")
            if category in reserved and reserved[category][k] != v:
                raise ValueError("Locked preference conflicts with retained assignment")
    for category, style in reserved.items(): locks.setdefault(category, {}).update(style)
    return reserved, locks


def hypothetical(scene, assignments):
    result = deepcopy(scene)
    for m in result["marks"]:
        style = assignments[m["category"]]
        if m["line_visible"] and style["dash"] == "none": raise ValueError("Repair cannot remove an existing line")
        if m["kind"] == "scatter" and style["marker"] == "none": raise ValueError("Repair cannot remove scatter markers")
        for c in m["channels"]: c["rgb"] = list(from_hex(style["color"]))
        if style["marker"] != "none" and not m["marker_visible"]:
            m["channels"].append({"kind": "face", "rgb": list(from_hex(style["color"])), "alpha": m["channels"][0]["alpha"]})
        m["marker"], m["marker_visible"] = style["marker"], style["marker"] != "none"
        if m["line_visible"]: m["dash"] = style["dash"]
    return result


def negotiate(scene, locked, assignments):
    data = scene.to_dict()
    if not scene.marks: raise ValueError("No supported visible line/scatter marks to repair; inspect coverage")
    reserved, locks = _preferences(locked, assignments)
    categories = sorted(set(scene.categories) | set(locks) | set(reserved))
    if len(categories) > 12: raise ValueError("Doctor v1 supports at most 12 reserved categories; split the figure or retain manual encodings")
    backgrounds = [m["background"] for m in data["marks"]]
    # Prepared palette selection only. Actual panel backgrounds are audited
    # independently; this choice is not a custom-background certification.
    bg = "dark" if sum(srgb_to_oklab(b)[0] for b in backgrounds)/len(backgrounds) < .55 else "light"
    palette = list(categorical(max(2, len(categories)), background=bg))
    originals = {}
    for key in categories:
        colors = [c["rgb"] for m in data["marks"] if m["category"] == key for c in m["channels"]]
        originals[key] = srgb_to_oklab(colors[0]) if colors else srgb_to_oklab(from_hex(locks[key].get("color", palette[0])))
    fixed = {k: v["color"].lower() for k, v in locks.items() if "color" in v}
    available = palette[:]
    # Reserve the nearest prepared slot for each hard color, leaving all other
    # supplied colors untouched. Exact duplicates remain honestly auditable.
    for color in fixed.values():
        if available:
            nearest = min(available, key=lambda c: math.dist(srgb_to_oklab(from_hex(c)), srgb_to_oklab(from_hex(color))))
            available.remove(nearest)
    free = [k for k in categories if k not in fixed]
    initial = dict(fixed)
    for key in free:
        color = min(available, key=lambda c: (math.dist(originals[key], srgb_to_oklab(from_hex(c))), c))
        initial[key] = color; available.remove(color)
    edges = relationships(data)
    points = {}
    for color in set(palette+list(fixed.values())):
        rgb = from_hex(color)
        points[color] = [srgb_to_oklab(rgb)] + [srgb_to_oklab(simulate(rgb, condition, severity=severity))
            for condition, severity in (("protan", 50), ("protan", 80), ("protan", 100),
                                        ("deutan", 50), ("deutan", 80), ("deutan", 100), ("tritan", 100))]
    def distance(a, b): return min(math.dist(u, v) for u, v in zip(points[a], points[b]))
    def objective(colors, name):
        change = sum(math.dist(originals[k], points[v][0]) for k, v in colors.items())
        separation = sum(e["weight"]*distance(colors[e["categories"][0]], colors[e["categories"][1]]) for e in edges)
        return change if name in ("closer", "simple") else -separation+.1*change
    results = []
    for name in ("closer", "separation", "simple"):
        colors = initial.copy()
        for _ in range(12):
            current = objective(colors, name); best = None
            for a, b in combinations(free, 2):
                trial = colors.copy(); trial[a], trial[b] = trial[b], trial[a]
                score = objective(trial, name)
                if score < current-1e-12: current, best = score, trial
            if best is None: break
            colors = best
        styles = {k: {"color": colors[k], "marker": "none", "dash": "solid"} for k in categories}
        scatter = {m["category"] for m in data["marks"] if m["kind"] == "scatter"}
        if name == "simple":
            # First inspect color/grayscale conflicts with minimal encodings.
            for k in scatter: styles[k]["marker"] = "circle"
            for k, fields in locks.items(): styles[k].update(fields)
            report = audit(hypothetical(data, styles))
            adjacency = {k: set() for k in categories}
            for pair in report["pairs"]:
                if pair["color_confusable"] or pair["grayscale_confusable"]:
                    a, b = pair["categories"]; adjacency[a].add(b); adjacency[b].add(a)
            for k in sorted(categories, key=lambda c: (-len(adjacency[c]), c)):
                neighbors = adjacency[k]
                if not neighbors: continue
                # Use dashes for lines, markers where a scatter participates.
                use_marker = k in scatter or any(v in scatter for v in neighbors)
                field, options = ("marker", MARKERS[:-1]) if use_marker else ("dash", DASHES[:-1])
                if field not in locks.get(k, {}):
                    used = {styles[v][field] for v in neighbors}
                    styles[k][field] = next((v for v in options if v not in used), options[0])
        else:
            for i, k in enumerate(categories):
                styles[k].update(marker=MARKERS[i % 6], dash=DASHES[(i//6+i) % 4])
        for k, fields in locks.items(): styles[k].update(fields)
        hypothetical_scene = hypothetical(data, styles)
        report = audit(hypothetical_scene)
        report.update(status="color-screen-passing; visual review pending" if report["color_screen_pass"] else "color screen failed; review redundant encodings",
                      objective=name, search="deterministic prepared-palette permutations; at most 12 local-swap passes",
                      locked=locks, reserved_categories=categories,
                      changes=[{"category": k, "before": [to_hex(c["rgb"]) for m in data["marks"] if m["category"] == k for c in m["channels"]],
                                "after": styles[k]} for k in scene.categories])
        results.append({"version": VERSION, "scene_sha256": scene.fingerprint, "name": name,
                        "assignments": styles, "report": report})
    return results
