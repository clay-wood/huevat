"""Exact displayed-color screens, separate from structural redundancy hints."""
import math
from itertools import combinations

from ..space import contrast, to_hex, srgb_to_oklab
from ..references import load_profile


def relationships(scene):
    import numpy as np
    edges = {}
    for a, b in combinations(scene["marks"], 2):
        if a["category"] == b["category"] or a["panel"] != b["panel"]: continue
        pair = tuple(sorted((a["category"], b["category"])))
        ap = np.array([p for p in a["points"] if p is not None], dtype=float).reshape(-1, 2)
        bp = np.array([p for p in b["points"] if p is not None], dtype=float).reshape(-1, 2)
        ap = ap[((ap >= 0) & (ap <= 1)).all(axis=1)]
        bp = bp[((bp >= 0) & (bp <= 1)).all(axis=1)]
        near = bool(len(ap) and len(bp) and np.linalg.norm(ap[:, None]-bp[None, :], axis=2).min() <= .03)
        def segments(mark):
            return np.array([[p, q] for p, q in zip(mark["points"], mark["points"][1:])
                             if p is not None and q is not None], dtype=float).reshape(-1, 2, 2)
        cross = False
        if a["line_visible"] and b["line_visible"]:
            aa, bb = segments(a), segments(b)
            if len(aa) and len(bb):
                p, r = aa[:, 0, None, :], (aa[:, 1]-aa[:, 0])[:, None, :]
                q, s = bb[None, :, 0, :], (bb[:, 1]-bb[:, 0])[None, :, :]
                def det(u, v): return u[..., 0]*v[..., 1]-u[..., 1]*v[..., 0]
                denominator = det(r, s)
                with np.errstate(divide="ignore", invalid="ignore"):
                    t, u = det(q-p, s)/denominator, det(q-p, r)/denominator
                hit = (abs(denominator) > 1e-14) & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
                intersection = p + np.where(np.isfinite(t), t, 0)[..., None]*r
                hit &= ((intersection >= 0) & (intersection <= 1)).all(axis=-1)
                cross = bool(hit.any())
        edge = edges.setdefault(pair, {"categories": list(pair), "panels": [], "crossing": False, "nearby": False, "weight": 1})
        if a["panel"] not in edge["panels"]: edge["panels"].append(a["panel"])
        edge["crossing"] |= cross; edge["nearby"] |= near
        edge["weight"] = 3 if edge["crossing"] else 2 if edge["nearby"] else 1
    return [edges[k] for k in sorted(edges)]


def audit(scene):
    try:
        import numpy as np
        from colorspacious import cspace_convert
        from ..evaluation import condition_colors, gray_rgb
    except ImportError as error:
        raise ImportError("Figure diagnosis and proposals require huevat[design]") from error
    profile = load_profile("data-marks")
    gates, panels, conflicts = [], [], {}
    def gate(name, measured, threshold, panel, encoding, condition, pair=None):
        passed = bool(math.isfinite(measured) and measured >= threshold)
        gates.append(dict(name=name, measured=float(measured), threshold=threshold, passed=passed,
                          panel=panel, encoding=encoding, condition=condition, pair=pair))
        return passed
    for axis in scene["axes"]:
        members = [m for m in scene["marks"] if m["panel"] == axis["key"]]
        colors, identities = [], []
        displayed = []
        for m in members:
            for c in m["channels"]:
                rgb = [v*c["alpha"]+b*(1-c["alpha"]) for v, b in zip(c["rgb"], m["background"])]
                colors.append(rgb); identities.append(m["category"])
                displayed.append({"mark": m["key"], "category": m["category"], "channel": c["kind"],
                                  "alpha": c["alpha"], "rgb": rgb, "hex": to_hex(rgb)})
        if not colors: continue
        pairs = [(i, j) for i, j in combinations(range(len(colors)), 2) if identities[i] != identities[j]]
        for encoding in ("float", "u8"):
            rgb = np.array(colors)
            if encoding == "u8": rgb = np.rint(rgb*255)/255
            gate("background_contrast", min(contrast(row, axis["background"]) for row in rgb), 3.,
                 axis["key"], encoding, "normal")
            for condition in profile["conditions"] + ["grayscale"]:
                rendered = gray_rgb(rgb) if condition == "grayscale" else condition_colors(rgb, condition)[0]
                lab = np.array([srgb_to_oklab(c) for c in rendered])
                cam = cspace_convert(rendered, "sRGB1", "CAM02-UCS")
                thresholds = (.08, 8.) if condition in ("normal", "grayscale") else (.04, 4.)
                minima = [float("inf"), float("inf")]
                for i, j in pairs:
                    pair = tuple(sorted((identities[i], identities[j])))
                    ratio = min(float(np.linalg.norm(points[i]-points[j]))/threshold
                                for points, threshold in zip((lab, cam), thresholds))
                    entry = conflicts.setdefault(pair, {"categories": list(pair), "color_confusable": False,
                                                        "grayscale_confusable": False, "minimum_ratio": None})
                    entry["grayscale_confusable" if condition == "grayscale" else "color_confusable"] |= ratio < 1
                    if condition != "grayscale":
                        entry["minimum_ratio"] = min(entry["minimum_ratio"] if entry["minimum_ratio"] is not None else ratio, ratio)
                    for space, points, threshold, k in zip(("oklab", "cam02"), (lab, cam), thresholds, (0, 1)):
                        d = float(np.linalg.norm(points[i]-points[j])); minima[k] = min(minima[k], d)
                if pairs and condition != "grayscale":
                    for space, d, threshold in zip(("oklab", "cam02"), minima, thresholds):
                        gate(space+"_minimum_pair", d, threshold, axis["key"], encoding, condition)
        panels.append({"panel": axis["key"], "background": axis["background"], "displayed": displayed})
    redundant, unresolved = [], []
    for pair, entry in sorted(conflicts.items()):
        comparisons = [(a, b) for a in scene["marks"] for b in scene["marks"]
                       if a["category"] == pair[0] and b["category"] == pair[1] and a["panel"] == b["panel"]]
        secondary = all((a["marker_visible"] and b["marker_visible"] and a["marker"] != b["marker"]) or
                        (a["line_visible"] and b["line_visible"] and a["dash"] != b["dash"]) for a, b in comparisons)
        entry["distinct_secondary_encoding"] = bool(comparisons and secondary)
        if entry["color_confusable"] or entry["grayscale_confusable"]:
            (redundant if secondary else unresolved).append(list(pair))
    return {"version": "h4c-doctor-v1", "profile": "h1-screening-v1/data-marks/actual-background",
            "color_screen_pass": bool(gates) and all(g["passed"] for g in gates),
            "color_scope": "supported visible mark channels over solid axes backgrounds",
            "complete_figure_screen_pass": False, "multichannel_screen_pass": None,
            "coverage": scene["coverage"], "criteria": gates, "panels": panels,
            "relationships": relationships(scene), "pairs": [conflicts[k] for k in sorted(conflicts)],
            "redundant_pairs": redundant, "unresolved_pairs": unresolved,
            "visual_review": "pending", "approved_default": False,
            "limits": ["Finite geometry screen; occlusion and display size are not modeled",
                       "Marker/dash differences are structural hints, not human readability certification",
                       "Unsupported content and layering are excluded from the color screen"]}
