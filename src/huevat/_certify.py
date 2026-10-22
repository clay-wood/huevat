"""Standard-library numerical certificates for cubic Oklab recipes.

Gamut is bounded over complete segments by recursive Bernstein interval bounds.
This is conservative floating-point interval screening, not a formal proof
with directed-rounding arithmetic. Unresolved bounds reject the recipe.
"""
import math

from .space import from_hex

_CONE = ((1, .3963377774, .2158037573), (1, -.1055613458, -.0638541728),
         (1, -.0894841775, -1.291485548))
_RGB = ((4.0767416621, -3.3077115913, .2309699292),
        (-1.2684380046, 2.6097574011, -.3413193965),
        (-.0041960863, -.7034186147, 1.707614701))


def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (float, int)) and math.isfinite(value)


def check_structure(recipe):
    required = {"schema_version", "algorithm_version", "family", "background", "context", "knots", "segments", "preferences", "identifier"}
    if not isinstance(recipe, dict) or set(recipe) - {"reversed"} != required:
        raise ValueError("Unknown or missing recipe fields")
    if recipe["schema_version"] != 1 or recipe["algorithm_version"] != "h2-ordered-v1":
        raise ValueError("Unsupported recipe version")
    if recipe["family"] not in ("sequential", "diverging") or recipe["context"] not in ("filled-fields", "data-marks"):
        raise ValueError("Unsupported recipe family/context")
    if not isinstance(recipe.get("reversed", False), bool):
        raise ValueError("reversed must be boolean")
    bg = recipe["background"]
    if not isinstance(bg, (tuple, list)) or len(bg) != 3 or not all(_finite(v) and 0 <= v <= 1 for v in bg):
        raise ValueError("Invalid recipe background")
    if not isinstance(recipe["identifier"], str) or len(recipe["identifier"]) > 256:
        raise ValueError("Invalid recipe identifier")
    prefs = recipe["preferences"]
    if not isinstance(prefs, (list, tuple)) or len(prefs) != (1 if recipe["family"] == "sequential" else 2):
        raise ValueError("Invalid recipe preferences")
    for color in prefs:
        from_hex(color)
    knots, segments = recipe["knots"], recipe["segments"]
    if not isinstance(knots, (tuple, list)) or not 2 <= len(knots) <= 33:
        raise ValueError("A recipe needs 1-32 cubic segments")
    if not all(_finite(x) for x in knots) or knots[0] != 0 or knots[-1] != 1 or any(b-a < 1e-7 for a, b in zip(knots, knots[1:])):
        raise ValueError("Recipe knots must strictly increase from 0 to 1")
    if recipe["family"] == "diverging" and .5 not in knots:
        raise ValueError("Diverging recipe must have one explicit center knot at .5")
    if not isinstance(segments, (list, tuple)) or len(segments) != len(knots)-1:
        raise ValueError("Recipe segment count does not match its knots")
    for segment in segments:
        if not isinstance(segment, (list, tuple)) or len(segment) != 3:
            raise ValueError("Each segment needs L,a,b polynomials")
        for coefficients in segment:
            if not isinstance(coefficients, (list, tuple)) or len(coefficients) != 4 or not all(_finite(v) and abs(v) <= 100 for v in coefficients):
                raise ValueError("Each coordinate needs four bounded finite coefficients")


def _bernstein(c):
    return c[0], c[0]+c[1]/3, c[0]+2*c[1]/3+c[2]/3, sum(c)


def _split(control):
    a, b, c, d = control
    ab, bc, cd = (a+b)/2, (b+c)/2, (c+d)/2
    abc, bcd = (ab+bc)/2, (bc+cd)/2
    middle = (abc+bcd)/2
    return (a, ab, abc, middle), (middle, bcd, cd, d)


def _gamut_bounds(controls):
    cones = []
    for row in _CONE:
        values = [sum(row[k]*controls[k][j] for k in range(3)) for j in range(4)]
        cones.append((min(values)**3, max(values)**3))
    bounds = []
    for row in _RGB:
        lo = sum(w*(bound[0] if w >= 0 else bound[1]) for w, bound in zip(row, cones))
        hi = sum(w*(bound[1] if w >= 0 else bound[0]) for w, bound in zip(row, cones))
        bounds.append((lo, hi))
    return bounds


def _derivative_range(c):
    values = [c[1], c[1]+2*c[2]+3*c[3]]
    if abs(c[3]) > 1e-16:
        root = -c[2]/(3*c[3])
        if 0 < root < 1:
            values.append(c[1]+2*c[2]*root+3*c[3]*root*root)
    return min(values), max(values)


def certify(recipe):
    check_structure(recipe)
    knots, segments = recipe["knots"], recipe["segments"]
    continuity_error = derivative_error = 0.
    lightness_order = True
    for i, segment in enumerate(segments):
        lo, hi = _derivative_range(segment[0])
        direction = 1 if sum(segment[0])-segment[0][0] >= 0 else -1
        lightness_order &= lo >= -1e-10 if direction > 0 else hi <= 1e-10
        if i:
            previous = segments[i-1]
            continuity_error = max(continuity_error, *(abs(sum(a)-b[0]) for a, b in zip(previous, segment)))
            derivative_error = max(derivative_error, *(abs((a[1]+2*a[2]+3*a[3])/(knots[i]-knots[i-1]) - b[1]/(knots[i+1]-knots[i])) for a, b in zip(previous, segment)))
    # A sequential path cannot change its monotone direction at a knot.
    starts = [segments[0][0][0]] + [sum(segment[0]) for segment in segments]
    if recipe["family"] == "sequential":
        sign = 1 if starts[-1] >= starts[0] else -1
        lightness_order &= all(sign*(b-a) >= -1e-10 for a, b in zip(starts, starts[1:]))
    else:
        middle = knots.index(.5)
        for values in (starts[:middle+1], starts[middle:][::-1]):
            sign = 1 if values[-1] >= values[0] else -1
            lightness_order &= all(sign*(b-a) >= -1e-10 for a, b in zip(values, values[1:]))
    pending = [(tuple(_bernstein(c) for c in segment), 0) for segment in segments]
    cells = 0
    gamut_pass = True
    while pending:
        controls, depth = pending.pop()
        cells += 1
        bounds = _gamut_bounds(controls)
        # A small interior margin makes the conservative test stable; no
        # out-of-gamut channel is accepted or silently clipped.
        if all(lo >= -1e-12 and hi <= 1+1e-12 for lo, hi in bounds):
            continue
        if depth >= 16 or cells > 100000:
            gamut_pass = False
            break
        halves = [_split(c) for c in controls]
        pending.append((tuple(pair[0] for pair in halves), depth+1))
        pending.append((tuple(pair[1] for pair in halves), depth+1))
    return {"passed": bool(gamut_pass and lightness_order and continuity_error <= 1e-9 and derivative_error <= 2e-7),
            "method": "cubic derivative extrema and adaptive Bernstein interval gamut bounds",
            "gamut_pass": gamut_pass, "monotone_lightness": bool(lightness_order),
            "continuity_error": continuity_error, "derivative_continuity_error": derivative_error,
            "interval_cells": cells, "max_depth": 16,
            "scope": "continuous numerical gamut/ordering/C1 checks; perceptual screens remain finite-grid tests"}
