"""Huevat's dependency-free numerical foundation and published reference data.

All construction families and immutable sampling are available.
v0.1 retains the current defaults; the expanded named collection is experimental.
Importing this package never loads a renderer or runs optimization.
"""

from .space import (
    contrast,
    distance,
    encode,
    from_hex,
    gamut_map,
    in_gamut,
    linearize,
    oklab_to_oklch,
    oklab_to_srgb,
    oklch_to_oklab,
    srgb_to_oklab,
    to_hex,
)
from .vision import simulate
from .references import reference, references, load_profile
from .gradients import (Gradient, Palette, QualityReport, QualityError,
                        SearchExhaustedError, ConstraintConflictError,
                        sequential, diverging)
from .families import multihue, spectral
from .categorical import categorical
from .sampling import SampledPalette, optimized_discrete, known_counts, summarize
from .catalog import gradient, gradient_names, gradient_info, load_recipe
from .library import design_ids, design_info, get_design, nearby_counts
from .exports import Export, LoadedExport, export, load_export
from ._prepared import prepared as _prepared, loader as _loader

# Fast immutable runtime views; the original construction/audit modules remain
# independently reproducible and unchanged.
categorical = _prepared(categorical)
sequential = _prepared(sequential)
diverging = _prepared(diverging)
multihue = _prepared(multihue)
spectral = _prepared(spectral)
gradient = _prepared(gradient)
load_recipe = _loader(load_recipe)

__version__ = "0.1.0"

__all__ = [
    "contrast", "distance", "encode", "from_hex", "gamut_map", "in_gamut",
    "linearize", "oklab_to_oklch", "oklab_to_srgb", "oklch_to_oklab",
    "srgb_to_oklab", "to_hex", "simulate",
    "reference", "references", "load_profile",
    "Gradient", "Palette", "QualityReport", "QualityError", "SearchExhaustedError",
    "ConstraintConflictError", "sequential", "diverging", "categorical", "multihue",
    "spectral", "load_recipe",
    "SampledPalette", "optimized_discrete", "known_counts", "summarize",
    "gradient", "gradient_names", "gradient_info",
    "design_ids", "design_info", "get_design", "nearby_counts",
    "Export", "LoadedExport", "export", "load_export",
]
