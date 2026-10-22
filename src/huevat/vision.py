"""Machado et al. (2009), severity 0-100 simulation in linear sRGB.

Supplementary matrices: doi:10.1109/TVCG.2009.113; transcription checked against
colorspacious/cvd.py (Nathaniel Smith, MIT). This is simulation, not a diagnostic
or an accessibility guarantee. Displaying simulated results clips to sRGB.
"""
from types import MappingProxyType
from functools import lru_cache
import math

from .space import _triple, linearize, encode, in_gamut
from ._data import load_data

MATRICES = MappingProxyType({
    "protan": ((.152286, 1.052583, -.204868), (.114503, .786281, .099216), (-.003882, -.048116, 1.051998)),
    "deutan": ((.367322, .860646, -.227968), (.280085, .672501, .047413), (-.011820, .042940, .968881)),
    "tritan": ((1.255528, -.076749, -.178779), (-.078411, .930809, .147602), (.004733, .691367, .303900)),
})


@lru_cache(maxsize=1)
def _tables():
    data = load_data("machado-v1.json")["matrices"]
    return {condition: {int(s): tuple(map(tuple, matrix)) for s, matrix in tables.items()}
            for condition, tables in data.items()}


def simulation_matrix(condition, severity=100):
    """Immutable Machado matrix; interpolate coefficients between 10% levels."""
    if not isinstance(severity, (int, float)) or isinstance(severity, bool) or not math.isfinite(severity) or not 0 <= severity <= 100:
        raise ValueError("Severity must be a finite number in [0, 100]")
    if not isinstance(condition, str) or condition not in MATRICES:
        raise ValueError("Choose protan, deutan or tritan")
    if severity == 100:
        return MATRICES[condition]
    low = int(severity // 10) * 10
    fraction = (severity - low) / 10
    tables = _tables()[condition]
    return tuple(tuple(a + fraction * (b - a) for a, b in zip(row_low, row_high))
                 for row_low, row_high in zip(tables[low], tables[low + 10]))


def simulate(rgb, condition, *, severity=100):
    """Return display-clipped encoded sRGB; severity defaults to 100."""
    rgb = _triple(rgb)
    if not in_gamut(rgb):
        raise ValueError("Simulation requires in-gamut sRGB")
    matrix = simulation_matrix(condition, severity)
    linear = tuple(linearize(c) for c in rgb)
    return tuple(encode(min(1., max(0., sum(w * c for w, c in zip(row, linear))))) for row in matrix)
