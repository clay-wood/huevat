"""Optional H1 numerical screening, with separate mathematical and engineering gates.

Install huevat[research]. Importing huevat itself never imports this module.
"""
import hashlib
import json
import math

try:
    import numpy as np
    from colorspacious import cspace_convert
except ImportError as error:
    raise ImportError("Reference evaluation requires huevat[research]") from error

from .references import load_profile
from .space import contrast, from_hex, srgb_to_oklab, to_hex
from .vision import simulation_matrix

ALGORITHM_VERSION = "h1-evaluation-v1"
FAMILIES = ("categorical", "sequential", "diverging", "spectral")


def rgb_array(colors):
    """Validate finite encoded-sRGB input without clipping or dropping colors."""
    try:
        rgb = np.asarray(colors, dtype=float)
    except (ValueError, TypeError):
        raise ValueError("Expected an N by 3 array of finite sRGB colors") from None
    if rgb.ndim != 2 or rgb.shape[1] != 3 or len(rgb) < 2:
        raise ValueError("Expected at least two RGB triples")
    if not np.isfinite(rgb).all() or np.any(rgb < 0) or np.any(rgb > 1):
        raise ValueError("RGB values must be finite and in [0, 1]")
    return rgb


def quantize(rgb):
    return np.rint(rgb_array(rgb) * 255) / 255


def _linear(rgb):
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def _encode(rgb):
    # Input is nonnegative here; no invalid power is evaluated on negative RGB.
    return np.where(rgb <= .0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - .055)


def condition_colors(rgb, condition):
    if condition == "normal":
        return np.asarray(rgb), {"clipped_channels": 0, "clipped_colors": 0, "clipped_fraction": 0.0}
    name, severity = condition.rsplit("-", 1)
    linear = _linear(np.asarray(rgb)) @ np.asarray(simulation_matrix(name, float(severity))).T
    clipped = (linear < 0) | (linear > 1)
    return _encode(np.clip(linear, 0, 1)), {
        "clipped_channels": int(clipped.sum()), "clipped_colors": int(clipped.any(axis=1).sum()),
        "clipped_fraction": float(clipped.mean()),
    }


def gray_rgb(rgb):
    luminance = _linear(np.asarray(rgb)) @ np.array([.2126, .7152, .0722])
    return np.repeat(_encode(luminance)[:, None], 3, axis=1)


def _lab(rgb):
    return np.array([srgb_to_oklab(row) for row in rgb])


def _spaces(rgb):
    lab, cam = _lab(rgb), np.asarray(cspace_convert(rgb, "sRGB1", "CAM02-UCS"))
    if not np.isfinite(lab).all() or not np.isfinite(cam).all():
        raise ValueError("Color-space conversion produced non-finite coordinates")
    return lab, cam


def _pair_metrics(points, full_matrix):
    matrix = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
    i, j = np.triu_indices(len(points), 1)
    position = int(np.argmin(matrix[i, j]))
    result = {"minimum_pair": float(matrix[i, j][position]),
              "closest_pair": [int(i[position]), int(j[position])],
              "minimum_adjacent": float(np.linalg.norm(np.diff(points, axis=0), axis=1).min())}
    if full_matrix:
        result["distance_matrix"] = matrix.tolist()
    return result


def _longest_run(mask):
    longest = run = 0
    for value in mask:
        run = run + 1 if value else 0
        longest = max(longest, run)
    return longest


def _arms(points, family):
    if family in ("diverging", "spectral"):
        middle = len(points) // 2
        # Both arms oriented from their extreme toward the shared center.
        return (points[:middle + 1], points[middle:][::-1])
    return (points,)


def _feature_gain(lightness, amplitude=.01):
    span = abs(float(lightness[-1] - lightness[0]))
    if span <= 1e-12:
        return 0.0
    x = np.linspace(0, 1, len(lightness))
    locations = np.linspace(.05, .95, 17)
    # On a diverging arm x spans half the original parameter range; +/- .02
    # in arm coordinates corresponds to +/- .01 in the full gradient.
    responses = abs(np.interp(locations + amplitude, x, lightness) -
                    np.interp(locations - amplitude, x, lightness))
    return float(np.min(responses) / (span * 2 * amplitude))


def _path_metrics(points, grayscale_lightness=None, family="sequential", encoding="float"):
    result = []
    gray_arms = _arms(grayscale_lightness[:, None], family) if grayscale_lightness is not None else None
    for index, arm in enumerate(_arms(points, family)):
        lightness = arm[:, 0]
        steps = np.linalg.norm(np.diff(arm, axis=0), axis=1)
        d_lightness = np.diff(lightness)
        direction = 1 if lightness[-1] >= lightness[0] else -1
        directed_lightness = direction * lightness
        p05, p95 = np.percentile(abs(d_lightness), [5, 95])
        mean, median = float(np.mean(steps)), float(np.median(steps))
        # Report undefined ratios as null and explicitly fail those screens.
        metrics = {
            "lightness": lightness.tolist(), "steps": steps.tolist(),
            "span": abs(float(lightness[-1] - lightness[0])),
            "maximum_backward_step": float(max(0, np.max(-direction * d_lightness))),
            "maximum_backward_excursion": float(np.max(np.maximum.accumulate(directed_lightness) - directed_lightness)),
            "speed_cv": float(np.std(steps) / mean) if mean > 1e-12 else None,
            "lightness_step_ratio": float(p95 / p05) if p05 > 1e-12 else None,
            "flat_run_fraction": _longest_run(abs(d_lightness) <= 1e-7) / len(steps),
            "spike_ratio": float(np.max(steps) / median) if median > 1e-12 else None,
            "maximum_step": float(np.max(steps)),
            "feature_gain": _feature_gain(lightness, .02 if family in ("diverging", "spectral") else .01),
        }
        if gray_arms is not None:
            metrics["grayscale_feature_gain"] = _feature_gain(gray_arms[index][:, 0], .02 if family in ("diverging", "spectral") else .01)
        result.append(metrics)
    center = None
    if family in ("diverging", "spectral"):
        left, right = _arms(points, family)
        # Equal lengths and one shared index are required by input validation.
        left_distance = np.linalg.norm(left - left[-1], axis=1)
        right_distance = np.linalg.norm(right - right[-1], axis=1)
        denominator = np.maximum(np.maximum(left_distance, right_distance), 1e-12)
        radius_indices = np.rint((1 - np.array([.25, .5, .75, 1])) * (len(left) - 1)).astype(int)
        center = {
            "lightness_difference_max": float(np.max(abs(left[:, 0] - right[:, 0]))),
            "distance_relative_difference_max": float(np.max(abs(left_distance - right_distance) / denominator)),
            "opposite_arm_separation_min": float(np.min(np.linalg.norm(left[radius_indices] - right[radius_indices], axis=1))),
            "center_chroma": float(np.linalg.norm(points[len(points)//2, 1:])),
            "shared_center": True,
            "arm_center_lightness_is_extreme": bool(all(
                (a[-1, 0] >= max(a[:, 0]) - 1e-7) for a in (left, right)) or all(
                (a[-1, 0] <= min(a[:, 0]) + 1e-7) for a in (left, right))),
        }
    return {"arms": result, "center": center}


def evaluate(colors, family, *, context="filled-fields", background="light", encoding="float", discrete=False):
    """Screen one explicit selection; invalid input raises ValueError.

    This function measures a sampled array, not an unknown continuous function.
    A passing numerical screen leaves human review pending and approval false.
    """
    if family not in FAMILIES:
        raise ValueError(f"Unknown family {family!r}")
    if encoding not in ("float", "u8"):
        raise ValueError("Choose float or u8 encoding")
    profile = load_profile(context, background)
    if family == "categorical" and context != "data-marks":
        raise ValueError("Categorical references require the data-marks context")
    rgb = rgb_array(colors)
    if family != "categorical" and (len(rgb) < 3 or (family in ("diverging", "spectral") and len(rgb) % 2 == 0)):
        raise ValueError("Ordered input needs at least three samples; diverging input needs an odd count and shared center")
    if encoding == "u8":
        rgb = quantize(rgb)
    criteria = []

    def gate(name, measured, threshold, relation, level="engineering", condition="normal"):
        finite = measured is not None and math.isfinite(float(measured))
        passed = finite and (measured >= threshold if relation == ">=" else measured <= threshold)
        criteria.append({"name": name, "condition": condition, "level": level,
                         "measured": measured, "relation": relation, "threshold": threshold,
                         "passed": bool(passed),
                         "reason": "within stated criterion" if passed else
                         ("undefined or non-finite metric" if not finite else "outside stated criterion")})

    unique = len({to_hex(row) for row in rgb})
    if family == "categorical" or discrete:
        gate("unique_exported_colors", unique, len(rgb), ">=", "mathematical")
    contrast_values = [contrast(row, from_hex(profile["background"])) for row in rgb]
    if context == "data-marks":
        gate("background_contrast", min(contrast_values), profile["criteria"]["background_contrast_min"], ">=")
    measured_conditions = {}
    for condition in profile["conditions"]:
        rendered, clipping = condition_colors(rgb, condition)
        lab, cam = _spaces(rendered)
        normal = condition == "normal"
        full_matrix = family == "categorical" or discrete
        measurement = {"clipping": clipping}
        if full_matrix:
            measurement["oklab"] = _pair_metrics(lab, True)
            measurement["cam02_ucs"] = _pair_metrics(cam, True)
            suffix = "normal" if normal else "cvd"
            for space, key in (("oklab", "oklab"), ("cam02", "cam02_ucs")):
                metric = "minimum_pair" if context == "data-marks" else "minimum_adjacent"
                threshold_key = f"{space}_distance_{suffix}_min" if context == "data-marks" else f"discrete_{space}_{suffix}_min"
                gate(f"{space}_{metric}", measurement[key][metric], profile["criteria"][threshold_key], ">=", condition=condition)
        if family != "categorical":
            gray_l = _lab(gray_rgb(rendered))[:, 0]
            path = _path_metrics(lab, gray_l, family, encoding)
            cam_path = _path_metrics(cam, family=family, encoding=encoding)
            measurement.update(oklab_path=path, cam02_path=cam_path, grayscale_lightness=gray_l.tolist())
            for index, arm in enumerate(path["arms"]):
                prefix = f"arm_{index}/"
                tolerance = profile["numerical"][f"lightness_backward_{encoding}_max"]
                if normal:
                    gate(prefix + "lightness_order", arm["maximum_backward_excursion"], tolerance, "<=", "mathematical", condition)
                else:
                    gate(prefix + "lightness_order", arm["maximum_backward_excursion"], tolerance, "<=", condition=condition)
                if discrete:
                    continue
                thresholds = profile["ordered"]
                span_key = "sequential_span_min" if family == "sequential" else "diverging_arm_span_min"
                gate(prefix + "lightness_span", arm["span"], thresholds[span_key], ">=", condition=condition)
                for name, threshold_name, relation in (
                    ("speed_cv", "speed_cv_max", "<="), ("lightness_step_ratio", "lightness_step_ratio_max", "<="),
                    ("flat_run_fraction", "flat_run_fraction_max", "<="), ("spike_ratio", "spike_ratio_max", "<="),
                    ("maximum_step", "step_oklab_max", "<="), ("feature_gain", "feature_gain_min", ">="),
                    ("grayscale_feature_gain", "feature_gain_min", ">="),
                ):
                    gate(prefix + name, arm[name], thresholds[threshold_name], relation, condition=condition)
            if path["center"] is not None:
                center = path["center"]
                if normal:
                    gate("center_is_lightness_extreme", int(center["arm_center_lightness_is_extreme"]), 1, ">=", "mathematical", condition)
                for name, threshold, relation in (
                    ("center_chroma", "center_chroma_max", "<="),
                    ("lightness_difference_max", "arm_lightness_difference_max", "<="),
                    ("distance_relative_difference_max", "arm_distance_relative_difference_max", "<="),
                    ("opposite_arm_separation_min", "arm_separation_oklab_min", ">="),
                ):
                    gate(name, center[name], profile["ordered"][threshold], relation, condition=condition)
        measured_conditions[condition] = measurement
    mathematical = [entry for entry in criteria if entry["level"] == "mathematical"]
    grayscale_audit = None
    if family == "categorical" or discrete:
        gray_lab, gray_cam = _spaces(gray_rgb(rgb))
        grayscale_audit = {"oklab": _pair_metrics(gray_lab, True),
                           "cam02_ucs": _pair_metrics(gray_cam, True),
                           "decision": "audit only; redundant coding remains a visual-review consideration"}
    return {"algorithm_version": ALGORITHM_VERSION, "profile": profile["id"],
            "family": family, "encoding": encoding, "discrete": discrete, "count": len(rgb),
            "rgb_sha256": hashlib.sha256(json.dumps(rgb.tolist(), separators=(",", ":")).encode()).hexdigest(),
            "hex": [to_hex(row) for row in rgb], "background_contrast": contrast_values,
            "conditions": measured_conditions, "criteria": criteria,
            "grayscale_audit": grayscale_audit,
            "mathematical_pass": all(entry["passed"] for entry in mathematical),
            "screen_pass": all(entry["passed"] for entry in criteria),
            "visual_review": "pending", "approved_default": False}
