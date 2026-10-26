"""Dependency-free H3 factories, immutable recipes and prepared designs."""
from functools import lru_cache
import json

from ._data import load_data
from .gradients import (Gradient, Palette, QualityReport, QualityError, fingerprint,
                        background_rgb, _request_options, _thaw,
                        load_recipe as _load_ordered)
from .space import from_hex

MULTIHUE_COLORS = ("#0072b2", "#009e73")
SPECTRAL_COLORS = ("#0072b2", "#009e73", "#e69f00", "#d55e00")


@lru_cache(maxsize=1)
def _prepared_data():
    return load_data("families-v1.json")


def _colors(colors, count=None):
    if not isinstance(colors, (tuple, list)) or not 2 <= len(colors) <= 8:
        raise ValueError("colors must contain 2-8 preferred #rrggbb values")
    if count is not None and len(colors) != count:
        raise ValueError("Supply one preferred color for each requested category")
    for color in colors:
        from_hex(color)
    return tuple(c.lower() for c in colors)


def _count(n):
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 64:
        raise ValueError("n must be an integer from 2 to 64 (the supported search size)")


def proxy_recipe(recipe):
    """Reuse the frozen cubic certificate with unchanged geometric coefficients."""
    result = _thaw(recipe)
    result["algorithm_version"] = "h2-ordered-v1"
    result["family"] = "sequential" if recipe["family"] == "multihue" else "diverging"
    result["preferences"] = result["preferences"][:1 if result["family"] == "sequential" else 2]
    return result


def check_recipe(recipe):
    from ._certify import check_structure
    if not isinstance(recipe, dict) or recipe.get("algorithm_version") != "h3-families-v1":
        raise ValueError("Unsupported H3 recipe version")
    family = recipe.get("family")
    if family == "categorical":
        required = {"schema_version", "algorithm_version", "family", "background", "context",
                    "rgb", "preferences", "identifier"}
        if set(recipe) != required or recipe["schema_version"] != 1 or recipe["context"] != "data-marks":
            raise ValueError("Invalid categorical recipe fields/version/context")
        if not isinstance(recipe["background"], (list, tuple)) or len(recipe["background"]) != 3:
            raise ValueError("Recipe background must be an RGB triple")
        background_rgb(recipe["background"])
        if not isinstance(recipe["identifier"], str) or len(recipe["identifier"]) > 256:
            raise ValueError("Invalid recipe identifier")
        rgb = recipe["rgb"]
        if not isinstance(rgb, (list, tuple)):
            raise ValueError("Categorical RGB must be an array")
        _count(len(rgb))
        for row in rgb:
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                raise ValueError("Expected RGB triples")
            background_rgb(row)
        prefs = recipe["preferences"]
        if not isinstance(prefs, (list, tuple)):
            raise ValueError("Preferences must be an array")
        if prefs:
            if len(prefs) != len(rgb):
                raise ValueError("Supply one preference per category")
            for color in prefs:
                from_hex(color)
    elif family in ("multihue", "spectral"):
        prefs = _colors(recipe.get("preferences"))
        if family == "spectral" and len(prefs) % 2:
            raise ValueError("Spectral preferences need equal-length left and right routes")
        check_structure(proxy_recipe(recipe))
    else:
        raise ValueError("Unsupported H3 family")


class CategoricalPalette(Palette):
    """Count-specific hex export; the recipe retains its floating design."""
    def to_recipe(self):
        recipe = self.report.to_dict()["recipe"]
        return {"recipe": recipe, "sha256": fingerprint(recipe), "evidence": self.report.to_dict()}

    def to_json(self):
        return json.dumps(self.to_recipe(), sort_keys=True, indent=2, allow_nan=False)


class HueGradient(Gradient):
    """H3 path with the H2 immutable sampler and family-specific screening."""
    def reversed(self):
        return HueGradient(self._recipe, self._report, self._discrete_records, not self._reverse)

    @property
    def report(self):
        source = Gradient(proxy_recipe(self._recipe), self._report, {}, self._reverse).report.to_dict()
        source["family"] = self.family
        if self._reverse and self.family == "spectral" and "hue_routes" in source:
            source["hue_routes"].reverse()
            for check in source.get("checks", ()):
                if check["name"].startswith("route_0/"):
                    check["name"] = check["name"].replace("route_0/", "route_1/", 1)
                elif check["name"].startswith("route_1/"):
                    check["name"] = check["name"].replace("route_1/", "route_0/", 1)
        return QualityReport(source)

    def discrete(self, n=9, *, context=None):
        proxy = Gradient(proxy_recipe(self._recipe), self._report, self._discrete_records, self._reverse)
        palette = proxy.discrete(n, context=context)
        report = palette.report.to_dict()
        report.update(family=self.family, algorithm_version="h3-discrete-v1")
        return Palette(palette.colors, QualityReport(report))


def categorical(n, colors=None, *, background="light", seed=4403, max_seconds=30., starts=4):
    """Jointly design exactly n categories; standard counts 2-12 use frozen data."""
    _count(n)
    background_rgb(background)
    _request_options("data-marks", seed, max_seconds, starts)
    if colors is not None:
        if not isinstance(colors, (list, tuple)) or len(colors) != n:
            raise ValueError("Supply one preferred #rrggbb color per category")
        for color in colors:
            from_hex(color)
        colors = tuple(c.lower() for c in colors)
    if colors is None and background in ("light", "dark") and n <= 12 and (seed, max_seconds, starts) == (4403, 30., 4):
        entry = _prepared_data()["categorical"][f"{background}/{n}"]
        return CategoricalPalette(tuple(entry["report"]["hex"]), QualityReport(entry["report"]))
    from .design_h3 import generate_categorical
    return generate_categorical(n, colors, background=background, seed=seed, max_seconds=max_seconds, starts=starts)


def _ordered(family, colors, background, context, seed, max_seconds, starts):
    colors = _colors(colors)
    if family == "spectral" and len(colors) % 2:
        raise ValueError("Spectral colors need equal-length left and right preferred routes")
    background_rgb(background)
    _request_options(context, seed, max_seconds, starts)
    standard = MULTIHUE_COLORS if family == "multihue" else SPECTRAL_COLORS
    if colors == standard and background in ("light", "dark") and context == "filled-fields" and (seed, max_seconds, starts) == (4403, 30., 4):
        entry = _prepared_data()["ordered"][f"{family}/{background}"]
        return HueGradient(entry["recipe"], QualityReport(entry["report"]), entry["discrete"], entry["reversed"])
    from .design_h3 import generate_ordered
    return generate_ordered(family, colors, background=background, context=context, seed=seed, max_seconds=max_seconds, starts=starts)


def multihue(colors=MULTIHUE_COLORS, *, background="light", context="filled-fields", seed=4403, max_seconds=30., starts=4):
    """Ordered multi-hue sequential path; preferences run from low to high L."""
    return _ordered("multihue", colors, background, context, seed, max_seconds, starts)


def spectral(colors=SPECTRAL_COLORS, *, background="light", context="filled-fields", seed=4403, max_seconds=30., starts=4):
    """Two multi-hue arms, with one shared neutral center at t=.5.

    Preferred colors run left extreme toward center, then center toward right
    extreme. The even-length sequence is split equally between the two arms.
    """
    return _ordered("spectral", colors, background, context, seed, max_seconds, starts)


def load_recipe(value, *, validate=True):
    """Load H2/H3 data-only recipes; unrecognized evidence is never trusted."""
    if not isinstance(validate, bool):
        raise ValueError("validate must be boolean")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError("Invalid recipe JSON") from None
    if not isinstance(value, dict) or set(value) != {"recipe", "sha256", "evidence"}:
        raise ValueError("Expected a Huevat recipe envelope")
    body = value["recipe"]
    if not isinstance(body, dict) or body.get("algorithm_version") != "h3-families-v1":
        return _load_ordered(value, validate=validate)
    try:
        matches = fingerprint(body) == value["sha256"]
    except (TypeError, ValueError):
        raise ValueError("Recipe must contain finite JSON data") from None
    if not matches:
        raise ValueError("Recipe hash mismatch")
    check_recipe(body)
    reverse = body.get("reversed", False)
    body = {k:v for k,v in body.items() if k != "reversed"}
    category = body["family"] == "categorical"
    entries = _prepared_data()["categorical" if category else "ordered"]
    for entry in entries.values():
        if fingerprint(entry["recipe"]) == fingerprint(body):
            if category:
                return CategoricalPalette(tuple(entry["report"]["hex"]), QualityReport(entry["report"]))
            return HueGradient(body, QualityReport(entry["report"]), entry["discrete"], reverse)
    certificate = None
    if not category:
        from ._certify import certify
        certificate = certify(proxy_recipe(body))
        if not certificate["passed"]:
            raise ValueError("Recipe failed continuous numerical certification")
    report = {"screen_pass": False, "outcome": "unvalidated-recipe", "approved_default": False,
              "recipe": body, "certificate": certificate}
    if validate:
        from .design_h3 import validate_categorical, validate_ordered
        report = validate_categorical(body) if category else validate_ordered(HueGradient(body, QualityReport({}), {}))
        if not report["screen_pass"]:
            raise QualityError("Imported recipe fails its stated profile", report)
    if category:
        from .space import to_hex
        return CategoricalPalette(tuple(map(to_hex, body["rgb"])), QualityReport(report))
    return HueGradient(body, QualityReport(report), {}, reverse)
