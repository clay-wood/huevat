"""Immutable cubic Oklab gradients and lightweight, validated sampling."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from functools import lru_cache
from types import MappingProxyType

from ._data import load_data
from .space import from_hex, in_gamut, oklab_to_srgb, srgb_to_oklab, distance, to_hex


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class QualityError(ValueError):
    """A specific, measured selection failed its stated profile."""
    def __init__(self, message, report):
        super().__init__(message)
        self.report = QualityReport(report)


class ConstraintConflictError(QualityError):
    """A stated constraint conflict has an explicit mathematical bound."""


class SearchExhaustedError(QualityError):
    """No passing result was found within the budget; not infeasibility proof."""


@dataclass(frozen=True)
class QualityReport(Mapping):
    _values: Mapping

    def __post_init__(self):
        object.__setattr__(self, "_values", _freeze(_thaw(self._values)))

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def to_dict(self):
        return _thaw(self._values)

    def __repr__(self):
        return f"QualityReport(screen_pass={self.screen_pass}, checks={len(self._values.get('checks', ()))})"

    @property
    def screen_pass(self):
        return self._values.get("screen_pass", False)


@dataclass(frozen=True)
class Palette(Sequence):
    """Immutable exported hex colors, with the count-specific report."""
    colors: tuple
    report: QualityReport

    def __post_init__(self):
        object.__setattr__(self, "colors", tuple(self.colors))
        for color in self.colors:
            from_hex(color)
        if not isinstance(self.report, QualityReport):
            object.__setattr__(self, "report", QualityReport(self.report))

    def __len__(self):
        return len(self.colors)

    def __getitem__(self, key):
        return self.colors[key]

    @property
    def rgb(self):
        return tuple(map(from_hex, self.colors))

    def __repr__(self):
        return f"Palette({self.colors!r}, screen_pass={self.report.screen_pass})"


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def background_rgb(value):
    if value in ("light", "dark"):
        return from_hex("#ffffff" if value == "light" else "#121212")
    if isinstance(value, str):
        return from_hex(value)
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError("Background must be light, dark, #rrggbb, or an RGB triple")
    result = tuple(_finite(v, "Background channel") for v in value)
    if not in_gamut(result, tolerance=0):
        raise ValueError("Background RGB must be in [0, 1]")
    return result


def _request_options(context, seed, max_seconds, starts):
    if context not in ("data-marks", "filled-fields"):
        raise ValueError("Context must be data-marks or filled-fields")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    if _finite(max_seconds, "max_seconds") <= 0:
        raise ValueError("max_seconds must be positive")
    if isinstance(starts, bool) or not isinstance(starts, int) or not 1 <= starts <= 32:
        raise ValueError("starts must be an integer in [1, 32]")


def _polynomial(coefficients, u):
    return ((coefficients[3]*u + coefficients[2])*u + coefficients[1])*u + coefficients[0]


def _arc_bound(segments):
    total = 0.
    for segment in segments:
        # Derivative quadratic in Bernstein form; norm is convex.
        derivatives = [(c[1], c[1] + c[2], c[1] + 2*c[2] + 3*c[3]) for c in segment]
        total += max(math.sqrt(sum(channel[index]**2 for channel in derivatives)) for index in range(3))
    return total


@dataclass(frozen=True)
class Gradient:
    """Piecewise cubic Oklab path; construction is through checked factory calls."""
    _recipe: Mapping
    _report: QualityReport
    _discrete_records: Mapping
    _reverse: bool = False

    def __post_init__(self):
        object.__setattr__(self, "_recipe", _freeze(_thaw(self._recipe)))
        object.__setattr__(self, "_discrete_records", _freeze(_thaw(self._discrete_records)))
        if not isinstance(self._report, QualityReport):
            object.__setattr__(self, "_report", QualityReport(self._report))

    @property
    def family(self):
        return self._recipe["family"]

    @property
    def background(self):
        return tuple(self._recipe["background"])

    def __repr__(self):
        return f"Gradient(family={self.family!r}, background={to_hex(self.background)!r}, screen_pass={self.report.screen_pass}, reversed={self._reverse})"

    def at(self, t):
        """Return floating-point encoded sRGB; no optimization or channel repair."""
        _finite(t, "t")
        if not 0 <= t <= 1:
            raise ValueError("t must be in [0, 1]")
        if self._reverse:
            t = 1 - t
        knots = self._recipe["knots"]
        index = min(next((i for i in range(len(knots)-1) if t <= knots[i+1]), len(knots)-2), len(knots)-2)
        u = (t - knots[index]) / (knots[index+1] - knots[index])
        lab = tuple(_polynomial(c, u) for c in self._recipe["segments"][index])
        rgb = oklab_to_srgb(lab)
        if not in_gamut(rgb):
            raise ValueError("Recipe evaluation left sRGB gamut; this path cannot be sampled as approved")
        # Only arithmetic-sized excursions are snapped, after gamut validation.
        return tuple(min(1., max(0., v)) for v in rgb)

    def reversed(self):
        return Gradient(self._recipe, self._report, self._discrete_records, not self._reverse)

    @property
    def report(self):
        data = self._report.to_dict()
        data["reversed"] = self._reverse
        data["metric_parameterization"] = "stored source path; metrics are orientation invariant"
        if self._reverse:
            for change in data.get("preferred_changes", []):
                change["parameter"] = 1-change["parameter"]
        if self._reverse and self.family == "diverging":
            for item in data.get("checks", []):
                name = item.get("name", "")
                item["name"] = name.replace("/arm_0/", "/arm_TEMP/").replace("/arm_1/", "/arm_0/").replace("/arm_TEMP/", "/arm_1/")
            for encoding in data.get("measurements", {}).values():
                for condition in encoding.values():
                    condition["oklab_arms"].reverse()
                    condition["cam02_arms"].reverse()
        return QualityReport(data)

    def discrete(self, n, *, context=None):
        """Validate exactly n endpoint-inclusive bins and return immutable hex colors."""
        if isinstance(n, bool) or not isinstance(n, int) or n < 2:
            raise ValueError("n must be an integer of at least two")
        context = self._recipe["context"] if context is None else context
        if context not in ("filled-fields", "data-marks"):
            raise ValueError("Context must be filled-fields or data-marks")
        from ._discrete import screen_discrete
        key = f"{context}/{n}"
        minimum = .04 if context == "filled-fields" else .08
        bound = _arc_bound(self._recipe["segments"])
        if (n-1)*minimum > bound + 1e-12:
            report = {"outcome": "constraint-conflict", "screen_pass": False,
                      "scope": "this fixed gradient and floating-point adjacent-bin requirement",
                      "requested_count": n, "required_total_distance": (n-1)*minimum,
                      "path_length_upper_bound": bound, "minimum_adjacent_distance": minimum}
            raise ConstraintConflictError(f"{n} bins require at least {(n-1)*minimum:.3g} Oklab path length; this path's upper bound is {bound:.3g}. Reduce n.", report)
        canonical = self.reversed() if self._reverse else self
        rgb = tuple(self.at(i/(n-1)) for i in range(n))
        if self._reverse:
            rgb = rgb[::-1]
        stored = self._discrete_records.get(key)
        if stored is not None and stored["hex"] == tuple(map(to_hex, rgb)):
            result = _thaw(stored)
        else:
            result = screen_discrete(rgb, canonical.at(.5), self.family, self.background, context)
        if not result["screen_pass"]:
            failures = sorted({item["name"] for item in result["checks"] if not item["passed"]})
            raise QualityError(f"{n} bins fail {context}: {', '.join(failures[:5])}. Reduce n or select another path/context.", result)
        values = tuple(result["hex"])
        if self._reverse:
            values = values[::-1]
            for measurement in result["measurements"].values():
                if "closest_pair" in measurement:
                    measurement["closest_pair"] = sorted(n-1-i for i in measurement["closest_pair"])
        result["hex"] = list(values)
        result["reversed"] = self._reverse
        return Palette(values, QualityReport(result))

    def to_recipe(self):
        recipe = _thaw(self._recipe)
        recipe["reversed"] = self._reverse
        return {"recipe": recipe, "sha256": fingerprint(recipe),
                "evidence": self._report.to_dict()}

    def to_json(self):
        return json.dumps(self.to_recipe(), sort_keys=True, indent=2, allow_nan=False)


@lru_cache(maxsize=1)
def _ordered_data():
    return load_data("ordered-v1.json")


def _prepared(family, background):
    data = _ordered_data()
    entry = data["designs"][f"{family}/{background}"]
    return Gradient(entry["recipe"], QualityReport(entry["report"]), entry["discrete"], entry["reversed"])


def sequential(color="#0072b2", *, background="light", context="filled-fields", seed=4402, max_seconds=20., starts=8):
    """Construct a passing single-hue path; standard lookup uses prepared data."""
    from_hex(color)
    background_rgb(background)
    _request_options(context, seed, max_seconds, starts)
    if color.lower() == "#0072b2" and background in ("light", "dark") and context == "filled-fields" and seed == 4402 and max_seconds == 20. and starts == 8:
        return _prepared("sequential", background)
    from .design import generate
    return generate("sequential", (color,), background=background, context=context, seed=seed, max_seconds=max_seconds, starts=starts)


def diverging(colors=("#0072b2", "#d55e00"), *, background="light", context="filled-fields", seed=4402, max_seconds=20., starts=8):
    """Construct two balanced arms with one shared Cartesian neutral center."""
    if not isinstance(colors, (tuple, list)) or len(colors) != 2:
        raise ValueError("colors must contain two preferred #rrggbb values")
    for value in colors:
        from_hex(value)
    background_rgb(background)
    _request_options(context, seed, max_seconds, starts)
    if tuple(c.lower() for c in colors) == ("#0072b2", "#d55e00") and background in ("light", "dark") and context == "filled-fields" and seed == 4402 and max_seconds == 20. and starts == 8:
        return _prepared("diverging", background)
    from .design import generate
    return generate("diverging", tuple(colors), background=background, context=context, seed=seed, max_seconds=max_seconds, starts=starts)


def load_recipe(value, *, validate=True):
    """Read a data-only recipe; unknown recipes require revalidation by default."""
    if not isinstance(validate, bool):
        raise ValueError("validate must be boolean")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            raise ValueError("Invalid recipe JSON") from None
    if not isinstance(value, dict) or set(value) != {"recipe", "sha256", "evidence"}:
        raise ValueError("Expected a Huevat recipe envelope")
    recipe = value["recipe"]
    try:
        matches = fingerprint(recipe) == value["sha256"]
    except (TypeError, ValueError):
        raise ValueError("Recipe must contain finite JSON data") from None
    if not matches:
        raise ValueError("Recipe hash mismatch")
    from ._certify import check_structure, certify
    check_structure(recipe)
    reverse = recipe.get("reversed", False)
    body = {key: item for key, item in recipe.items() if key != "reversed"}
    data = _ordered_data()
    for entry in data["designs"].values():
        if fingerprint(body) == fingerprint(entry["recipe"]):
            return Gradient(body, QualityReport(entry["report"]), entry["discrete"], reverse)
    certificate = certify(body)
    if not certificate["passed"]:
        raise ValueError("Recipe failed continuous numerical certification")
    gradient = Gradient(body, QualityReport({"screen_pass": False, "outcome": "unvalidated-recipe",
                                            "approved_default": False, "certificate": certificate}), {}, reverse)
    if validate:
        from .design import validate_gradient
        report = validate_gradient(Gradient(body, gradient._report, {}))
        if not report["screen_pass"]:
            raise QualityError("Imported recipe fails its stated profile", report)
        return Gradient(body, QualityReport(report), {}, reverse)
    return gradient
