"""Compact, hashed JSON exchange and explicit hex/CSV/CSS exports.

All imports and normal prepared operations use the standard library. Detailed
audit evidence stays with the source, rather than being duplicated in exports.
"""
from dataclasses import dataclass
import csv
import hashlib
import io
import json
from pathlib import Path

from .gradients import (Gradient, Palette, QualityReport, QualityError, _thaw,
                        fingerprint, _finite)
from .sampling import SampledPalette
from .space import to_hex, from_hex

VERSION = "huevat-export-v1"


@dataclass(frozen=True)
class Export:
    text: str
    format: str
    report: QualityReport

    @property
    def sha256(self): return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def write(self, path):
        """Explicit UTF-8 file write with portable LF line endings."""
        path = Path(path)
        path.write_text(self.text, encoding="utf-8", newline="\n")
        return path

    def __str__(self): return self.text


@dataclass(frozen=True)
class LoadedExport:
    design: object
    source: object
    labels: tuple | None

    @property
    def color_map(self):
        if not isinstance(self.design, Palette) or self.labels is None:
            raise ValueError("A color map needs a palette with explicit labels")
        from types import MappingProxyType
        return MappingProxyType(dict(zip(self.labels, self.design.colors)))


def _recipe(design):
    """Avoid copying the large report merely to get a tiny recipe."""
    if isinstance(design, Gradient):
        body = _thaw(design._recipe); body["reversed"] = design._reverse
    elif isinstance(design, SampledPalette):
        # The nested source recipe is part of the sampling recipe's identity.
        # Preserve it exactly, including its already stripped evidence field.
        body = {"schema_version": 1, "algorithm_version": "h4-sampling-v1", "family": "sampled",
                "source": _thaw(design.source), "positions": list(design.positions),
                "context": design.report["context"]}
    elif isinstance(design, Palette) and "recipe" in design.report:
        body = _thaw(design.report["recipe"])
    else: raise ValueError("For JSON provenance use export(gradient, n=...) or export(palette, source=gradient)")
    return {"recipe": body, "sha256": fingerprint(body), "evidence": {}}


def _labels(labels, count):
    if labels is None: return None
    if count is None or not isinstance(labels, (tuple, list)) or len(labels) != count or any(not isinstance(v, str) for v in labels) or len(set(labels)) != count:
        raise ValueError("Supply one unique string label per palette color")
    return tuple(labels)


def _checked(design):
    if not isinstance(design, (Gradient, Palette)): raise ValueError("Expected a Huevat gradient or palette")
    report = design._report if isinstance(design, Gradient) else design.report
    if not report.screen_pass:
        raise QualityError("Export requires a screened source; revalidate unknown recipes first", report.to_dict())
    return report


def _selection(design, n, context, source):
    _checked(design)
    if source is not None:
        if not isinstance(source, Gradient) or not isinstance(design, Palette) or isinstance(design, SampledPalette):
            raise ValueError("source= requires an ordinary uniform palette and its original gradient")
        if n is not None: raise ValueError("n is supplied by the palette when source= is used")
        _checked(source)
        context = context or design.report.get("context", source._recipe["context"])
        expected = source.discrete(len(design), context=context)
        if expected.colors != design.colors: raise ValueError("Palette colors do not match this exact source/count/context")
        return source, design, {"method": "uniform", "count": len(design), "context": context}
    if isinstance(design, Gradient):
        if n is None:
            if context is not None: raise ValueError("context= applies to an explicit discrete selection")
            return design, None, None
        palette = design.discrete(n, context=context)
        return design, palette, {"method": "uniform", "count": n, "context": context or design._recipe["context"]}
    if n is not None or context is not None: raise ValueError("A palette already has its count and context")
    return design, design, None


def _positions(palette, selection):
    if isinstance(palette, SampledPalette): return tuple(palette.positions)
    if selection: return tuple(i/(len(palette)-1) for i in range(len(palette)))
    return (None,)*len(palette)


def _css(gradient, tolerance, max_stops):
    from .adapters._common import audit, interpolate, rgb_string
    if _finite(tolerance, "tolerance") <= 0: raise ValueError("tolerance must be positive")
    if isinstance(max_stops, bool) or not isinstance(max_stops, int) or not 3 <= max_stops <= 4097 or max_stops % 2 != 1:
        raise ValueError("max_stops must be an odd integer in [3, 4097]")
    count = min(33, max_stops)
    while True:
        positions = tuple(i/(count-1) for i in range(count))
        strings = tuple(rgb_string(gradient.at(t)) for t in positions)
        # Audit the formatted RGB values, including decimal serialization.
        colors = tuple(tuple(float(v)/255 for v in s[4:-1].split(',')) for s in strings)
        actual_positions = tuple(float(f"{100*t:.15g}")/100 for t in positions)
        report = audit(gradient, lambda t: interpolate(actual_positions, colors, t), "css-srgb", count, tolerance)
        if report["approximation_pass"]:
            stops = ", ".join(f"{color} {100*t:.15g}%" for t, color in zip(positions, strings))
            return "linear-gradient(90deg in srgb, "+stops+")", report
        if count == max_stops:
            raise QualityError("CSS export cannot meet the tolerance within max_stops", report.to_dict())
        count = min(max_stops, 2*count-1)


def export(design, format="json", *, n=None, context=None, labels=None, source=None,
           tolerance=.002, max_stops=1025):
    """Return an immutable Export with text, SHA256 and scoped evidence.

    JSON retains lossless recipe/selection provenance. CSV/hex require an
    explicit passing count for gradients. CSS uses a measured continuous
    approximation or exact equal-width categorical steps (no physical bins).
    """
    if format not in ("json", "hex", "csv", "css"): raise ValueError("Choose json, hex, csv or css")
    original, palette, selection = _selection(design, n, context, source)
    names = _labels(labels, None if palette is None else len(palette))
    from . import __version__
    report = {"algorithm_version": VERSION, "source_version": __version__, "format": format,
              "source_screen_pass": True, "approved_default": False, "visual_review": "not inferred",
              "physical_boundaries": "not supplied or inferred"}
    if format == "json":
        envelope = _recipe(original)
        body = {"version": VERSION, "created_with": __version__, "source": envelope,
                "selection": selection, "labels": None if names is None else list(names),
                "hex": None if palette is None else list(palette.colors)}
        text = json.dumps({"payload": body, "sha256": fingerprint(body)}, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)+"\n"
        report.update(source_sha256=envelope["sha256"], lossless=True, scope="recipe and exact selection; evidence reloaded/revalidated on import")
    elif format == "css" and palette is None:
        text, measured = _css(original, tolerance, max_stops)
        report.update(measured.to_dict()); text += "\n"
        report.update(lossless=False, interpolation="explicit encoded sRGB", browser_render_verified=False)
    else:
        if palette is None: raise ValueError("CSV/hex tables need an explicit passing sample count n=")
        positions = _positions(palette, selection)
        report.update(exported_colors_sha256=fingerprint(list(palette.colors)), lossless=False,
                      scope="exact hex table; no continuous path or physical boundaries implied")
        if format == "hex": text = "\n".join(palette.colors)+"\n"
        elif format == "csv":
            out = io.StringIO(newline=""); writer = csv.writer(out, lineterminator="\n")
            writer.writerow(("index", "label", "position", "hex", "r", "g", "b"))
            for i, (color, position) in enumerate(zip(palette.colors, positions)):
                writer.writerow((i, "" if names is None else names[i], "" if position is None else repr(position), color,
                                 *(round(v*255) for v in from_hex(color))))
            text = out.getvalue()
        else:
            stops = ", ".join(f"{color} {100*i/len(palette):.15g}% {100*(i+1)/len(palette):.15g}%"
                              for i, color in enumerate(palette.colors))
            text = "linear-gradient(90deg in srgb, "+stops+")\n"
            report.update(approximation_pass=True, scope="exact equal-width swatches; not a physical-data mapping",
                          interpolation="constant within each swatch", browser_render_verified=False)
    return Export(text, format, QualityReport(report))


def load_export(value, *, validate=True):
    """Load only hashed Huevat JSON. Supplied evidence cannot grant a pass."""
    if not isinstance(validate, bool): raise ValueError("validate must be boolean")
    if isinstance(value, Export): value = value.text
    if isinstance(value, str):
        try: value = json.loads(value)
        except (TypeError, ValueError): raise ValueError("Invalid export JSON") from None
    if not isinstance(value, dict) or set(value) != {"payload", "sha256"}: raise ValueError("Expected a hashed Huevat export")
    body = value["payload"]
    try: matches = fingerprint(body) == value["sha256"]
    except (TypeError, ValueError): raise ValueError("Export must contain finite JSON data") from None
    if not matches: raise ValueError("Export hash mismatch")
    if not isinstance(body, dict) or set(body) != {"version", "created_with", "source", "selection", "labels", "hex"} or body["version"] != VERSION:
        raise ValueError("Unsupported export schema/version")
    if not isinstance(body["created_with"], str) or not body["created_with"]: raise ValueError("Missing source version")
    from . import load_recipe
    source = load_recipe(body["source"], validate=validate)
    selection = body["selection"]
    design = source
    if selection is not None:
        if not isinstance(source, Gradient) or not isinstance(selection, dict) or set(selection) != {"method", "count", "context"} or selection["method"] != "uniform":
            raise ValueError("Invalid discrete selection schema")
        n, context = selection["count"], selection["context"]
        if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 1025 or context not in ("filled-fields", "data-marks"):
            raise ValueError("Invalid selection count/context")
        if validate: design = source.discrete(n, context=context)
        else:
            design = Palette(tuple(to_hex(source.at(i/(n-1))) for i in range(n)),
                QualityReport({"screen_pass": False, "outcome": "unvalidated-export-selection", "context": context,
                               "approved_default": False, "background": source.background}))
    if isinstance(design, Palette):
        if body["hex"] != list(design.colors): raise ValueError("Export colors do not match source recipe/selection")
        names = _labels(body["labels"], len(design))
    else:
        if body["hex"] is not None or body["labels"] is not None: raise ValueError("Continuous exports have no categorical labels/colors")
        names = None
    return LoadedExport(design, source, names)
