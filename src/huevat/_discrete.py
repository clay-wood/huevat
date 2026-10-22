"""Count-specific screening; basic failures need no optional dependencies."""
import math

from ._data import load_data
from .space import srgb_to_oklab, contrast, distance, to_hex, from_hex
from .vision import simulate


def screen_discrete(rgb, center, family, background, context, *, audit=True):
    profile = load_data("profiles-v1.json")
    thresholds = profile["contexts"][context]
    checks, measurements = [], {}

    def gate(name, value, limit, condition="normal", relation=">=", level="engineering"):
        passed = math.isfinite(value) and (value >= limit if relation == ">=" else value <= limit)
        checks.append({"name": name, "condition": condition, "measured": value, "threshold": limit,
                       "relation": relation, "level": level, "passed": passed})

    encodings = {"float": tuple(rgb), "u8": tuple(from_hex(to_hex(c)) for c in rgb)}
    for encoding, colors in encodings.items():
        if encoding == "u8":
            gate("u8/unique_exported_colors", len(set(map(to_hex, colors))), len(colors), level="mathematical")
        if context == "data-marks":
            gate(encoding+"/background_contrast", min(contrast(c, background) for c in colors), thresholds["background_contrast_min"])
        for condition in profile["conditions"]:
            actual_center = from_hex(to_hex(center)) if encoding == "u8" else center
            if condition == "normal":
                simulated, neutral = colors, actual_center
            else:
                name, severity = condition.rsplit("-", 1)
                simulated = tuple(simulate(c, name, severity=int(severity)) for c in colors)
                neutral = simulate(actual_center, name, severity=int(severity))
            lab = tuple(map(srgb_to_oklab, simulated))
            pairs = [(i, j) for i in range(len(colors)) for j in range(i+1, len(colors))] if context == "data-marks" else [(i, i+1) for i in range(len(colors)-1)]
            values = [distance(lab[i], lab[j]) for i, j in pairs]
            kind = "normal" if condition == "normal" else "cvd"
            limit = thresholds[f"oklab_distance_{kind}_min"] if context == "data-marks" else thresholds[f"discrete_oklab_{kind}_min"]
            prefix = encoding + "/"
            gate(prefix+"oklab_separation", min(values), limit, condition)
            measured = {"minimum_oklab_distance": min(values), "closest_pair": list(pairs[values.index(min(values))])}
            if family == "diverging":
                matched = [(lab[i], lab[-i-1]) for i in range(len(lab)//2)]
                neutral_lab = srgb_to_oklab(neutral)
                imbalance = max(abs(distance(a, neutral_lab)-distance(b, neutral_lab))/max(distance(a, neutral_lab), distance(b, neutral_lab), 1e-12) for a, b in matched)
                gate(prefix+"arm_lightness_balance", max(abs(a[0]-b[0]) for a, b in matched), profile["ordered"]["arm_lightness_difference_max"], condition, "<=")
                gate(prefix+"arm_distance_balance", imbalance, profile["ordered"]["arm_distance_relative_difference_max"], condition, "<=")
                gate(prefix+"opposite_arm_separation", min(distance(a,b) for a,b in matched), profile["ordered"]["arm_separation_oklab_min"], condition)
            measurements[f"{encoding}/{condition}"] = measured
            # CAM02-UCS is deferred until basic screens pass, avoiding an
            # optional dependency merely to explain an excessive bin count.
    basic_pass = all(c["passed"] for c in checks)
    if audit and basic_pass:
        try:
            from colorspacious import cspace_convert
        except ImportError:
            raise ImportError("This count needs an independent CAM02-UCS audit. Install huevat[design], or use a prepared passing count.") from None
        for encoding, colors in encodings.items():
            for condition in profile["conditions"]:
                if condition == "normal":
                    simulated = colors
                else:
                    name, severity = condition.rsplit("-", 1)
                    simulated = tuple(simulate(c, name, severity=int(severity)) for c in colors)
                cam = cspace_convert(simulated, "sRGB1", "CAM02-UCS")
                pairs = [(i,j) for i in range(len(colors)) for j in range(i+1,len(colors))] if context == "data-marks" else [(i,i+1) for i in range(len(colors)-1)]
                separation = min(math.dist(cam[i],cam[j]) for i,j in pairs)
                kind = "normal" if condition == "normal" else "cvd"
                limit = thresholds[f"cam02_distance_{kind}_min"] if context == "data-marks" else thresholds[f"discrete_cam02_{kind}_min"]
                gate(encoding+"/cam02_separation", separation, limit, condition)
                measurements[f"{encoding}/{condition}"]["minimum_cam02_distance"] = separation
    return {"algorithm_version": "h2-discrete-v1", "profile_version": profile["version"],
            "context": context, "background": tuple(background), "count": len(rgb),
            "hex": list(map(to_hex, rgb)), "checks": checks, "measurements": measurements,
            "screen_pass": bool(basic_pass and audit and all(c["passed"] for c in checks)),
            "outcome": "passed" if basic_pass and audit and all(c["passed"] for c in checks) else "selection-failed",
            "cam02_audit": "performed" if basic_pass and audit else "skipped after basic failure" if not basic_pass else "not requested",
            "visual_review": "pending", "approved_default": False,
            "sampling": "endpoint-inclusive; even diverging counts omit the shared center; all actual opposite pairs tested"}
