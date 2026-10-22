"""Lightweight Clearer categorical lookup and versioned recipe dispatch."""
from functools import lru_cache
import json

from ._data import load_data
from .families import (CategoricalPalette, categorical as _legacy_categorical,
                       load_recipe as _legacy_load_recipe, check_recipe as _legacy_check, _count)
from .gradients import (QualityReport, QualityError, background_rgb, fingerprint,
                        _request_options, _finite)
from .space import from_hex, to_hex

VERSION = "h3-categorical-v2"
CLEARER_ANCHORS = ("#4379a3", "#348b83", "#ae883b", "#bd6c60", "#9274a3", "#5599b4",
                   "#9b586d", "#7e8750", "#bd803f", "#6c7b91", "#638759", "#b7758f")


@lru_cache(maxsize=1)
def _data():
    return load_data("categorical-v2.json")


def legacy_recipe(recipe):
    """Keep the original H3 auditor frozen; identical RGB receives its gates."""
    result = {k:v for k,v in recipe.items() if k not in ("style", "targets")}
    result["algorithm_version"] = "h3-families-v1"
    return result


def check_recipe(recipe):
    if not isinstance(recipe, dict) or recipe.get("algorithm_version") != VERSION or recipe.get("style") != "clearer":
        raise ValueError("Unsupported categorical version/style")
    if recipe.get("family") != "categorical" or set(recipe) != {
        "schema_version", "algorithm_version", "family", "background", "context", "rgb",
        "preferences", "identifier", "style", "targets"
    }:
        raise ValueError("Invalid Clearer recipe fields")
    _legacy_check(legacy_recipe(recipe))
    targets = recipe["targets"]
    if not isinstance(targets, (list, tuple)) or len(targets) != len(recipe["rgb"]):
        raise ValueError("Supply one Oklab target per category")
    for row in targets:
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ValueError("Targets must be Oklab triples")
        for value in row:
            if abs(_finite(value, "Target coordinate")) > 2:
                raise ValueError("Target coordinates must be bounded")


def categorical(n, colors=None, *, background="light", style="clearer", seed=14507, max_seconds=30., starts=3):
    """Count-specific Clearer colors; prepared counts 2–12 need no extras.

    Hard numerical gates come first, then closeness to coherent color targets.
    style='max-separation' explicitly selects the original H3 construction.
    """
    _count(n); background_rgb(background); _request_options("data-marks",seed,max_seconds,starts)
    if style not in ("clearer", "max-separation"):
        raise ValueError("style must be clearer or max-separation")
    if colors is not None:
        if not isinstance(colors, (list,tuple)) or len(colors) != n:
            raise ValueError("Supply one preferred #rrggbb color per category")
        for color in colors:
            from_hex(color)
        colors = tuple(c.lower() for c in colors)
    if style == "max-separation":
        # Preserve the original default search settings for explicit legacy use.
        original_defaults = (seed,max_seconds,starts) == (14507,30.,3)
        return _legacy_categorical(n,colors,background=background,seed=4403 if original_defaults else seed,
                                   max_seconds=max_seconds,starts=4 if original_defaults else starts)
    if colors is None and background in ("light", "dark") and n <= 12 and (seed,max_seconds,starts) == (14507,30.,3):
        entry = _data()["designs"][f"{background}/{n}"]
        return CategoricalPalette(tuple(entry["report"]["hex"]),QualityReport(entry["report"]))
    from .design_categorical import generate
    return generate(n,colors,background=background,seed=seed,max_seconds=max_seconds,starts=starts)


def load_recipe(value, *, validate=True):
    """Read Clearer and all earlier Huevat recipes without trusting claims."""
    if not isinstance(validate,bool):
        raise ValueError("validate must be boolean")
    if isinstance(value,str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError("Invalid recipe JSON") from None
    if not isinstance(value,dict) or set(value) != {"recipe","sha256","evidence"}:
        raise ValueError("Expected a Huevat recipe envelope")
    recipe = value["recipe"]
    if not isinstance(recipe,dict) or recipe.get("algorithm_version") != VERSION:
        return _legacy_load_recipe(value,validate=validate)
    try:
        matches = fingerprint(recipe) == value["sha256"]
    except (TypeError,ValueError):
        raise ValueError("Recipe must contain finite JSON data") from None
    if not matches:
        raise ValueError("Recipe hash mismatch")
    check_recipe(recipe)
    for entry in _data()["designs"].values():
        if fingerprint(entry["recipe"]) == fingerprint(recipe):
            return CategoricalPalette(tuple(entry["report"]["hex"]),QualityReport(entry["report"]))
    report = {"screen_pass":False,"outcome":"unvalidated-recipe","approved_default":False,"recipe":recipe}
    if validate:
        from .design_categorical import validate_categorical
        report = validate_categorical(recipe)
        if not report["screen_pass"]:
            raise QualityError("Imported Clearer recipe fails its numerical/aesthetic profile",report)
    return CategoricalPalette(tuple(map(to_hex,recipe["rgb"])),QualityReport(report))
