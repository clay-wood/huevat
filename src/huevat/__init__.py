"""Huevat's dependency-free numerical foundation and published reference data.

Palette constructors and reviewed defaults are scheduled for H2-H4.
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

__version__ = "0.1.0.dev0"

__all__ = [
    "contrast", "distance", "encode", "from_hex", "gamut_map", "in_gamut",
    "linearize", "oklab_to_oklch", "oklab_to_srgb", "oklch_to_oklab",
    "srgb_to_oklab", "to_hex", "simulate",
    "reference", "references", "load_profile",
]
