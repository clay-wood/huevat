"""Machado et al. (2009), severity 100 simulation in linear sRGB.

Supplementary matrices: doi:10.1109/TVCG.2009.113; transcription checked against
colorspacious/cvd.py (Nathaniel Smith, MIT). This is simulation, not a diagnostic
or an accessibility guarantee. Displaying simulated results clips to sRGB.
"""
from types import MappingProxyType

from .space import _triple, linearize, encode, in_gamut

MATRICES = MappingProxyType({
    "protan": ((.152286, 1.052583, -.204868), (.114503, .786281, .099216), (-.003882, -.048116, 1.051998)),
    "deutan": ((.367322, .860646, -.227968), (.280085, .672501, .047413), (-.011820, .042940, .968881)),
    "tritan": ((1.255528, -.076749, -.178779), (-.078411, .930809, .147602), (.004733, .691367, .303900)),
})


def simulate(rgb, condition):
    """Return display-clipped encoded sRGB for a severity-100 simulation."""
    rgb = _triple(rgb)
    if not in_gamut(rgb):
        raise ValueError("Simulation requires in-gamut sRGB")
    try:
        matrix = MATRICES[condition]
    except (KeyError, TypeError):
        raise ValueError("Choose protan, deutan or tritan") from None
    linear = tuple(linearize(c) for c in rgb)
    return tuple(encode(min(1., max(0., sum(w * c for w, c in zip(row, linear))))) for row in matrix)
