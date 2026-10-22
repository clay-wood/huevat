"""Exact published reference tables and explicitly labeled study sampling.

These are comparison data, not Huevat defaults or approved gradient objects.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

from ._data import load_data


def _count(n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("Sample count must be an integer of at least two")
    return n


def interpolate(rgb, t):
    """Piecewise-linear encoded-sRGB study adaptation; no gamut repair."""
    if isinstance(t, bool) or not isinstance(t, (float, int)) or not math.isfinite(t) or not 0 <= t <= 1:
        raise ValueError("Sample parameter must be finite and in [0, 1]")
    if t in (0, 1):
        return tuple(rgb[0 if t == 0 else -1])
    position = t * (len(rgb) - 1)
    index = min(int(position), len(rgb) - 2)
    weight = position - index
    return tuple(a + weight * (b - a) for a, b in zip(rgb[index], rgb[index + 1]))


@dataclass(frozen=True)
class Reference:
    identifier: str
    label: str
    family: str
    source: str
    rgb: tuple
    native_tables: tuple
    selection: str
    path_adaptation: str
    rgb_sha256: str

    def colors(self, n):
        """Select a native count table or documented prefix/uniform samples."""
        _count(n)
        tables = dict(self.native_tables)
        if tables:
            if n not in tables:
                raise ValueError(f"{self.identifier} has no native {n}-color table")
            return tables[n]
        if self.family == "categorical":
            if n > len(self.rgb):
                raise ValueError(f"{self.identifier} has only {len(self.rgb)} source colors")
            return self.rgb[:n]
        return self.sample(n)

    def sample(self, n=257):
        """Sample an ordered study adaptation; this does not certify quality."""
        _count(n)
        if self.family == "categorical":
            raise ValueError("Categorical references have no ordered interpolation")
        return tuple(interpolate(self.rgb, i / (n - 1)) for i in range(n))


@lru_cache(maxsize=1)
def _corpus():
    result = []
    for entry in load_data("references-v1.json")["references"]:
        tables = tuple((int(n), tuple(map(tuple, table))) for n, table in entry["native_tables"].items())
        result.append(Reference(entry["id"], entry["label"], entry["family"], entry["source"],
                                tuple(map(tuple, entry["rgb"])), tables, entry["selection"],
                                entry.get("path_adaptation", "none"), entry["rgb_sha256"]))
    return tuple(result)


def references():
    """Return immutable reference identifiers, in fixed study order."""
    return tuple(item.identifier for item in _corpus())


def reference(identifier):
    for item in _corpus():
        if item.identifier == identifier:
            return item
    raise ValueError(f"Unknown reference {identifier!r}; choose from {references()}")


def load_profile(context="data-marks", background="light"):
    """Return an independent data-only copy of a versioned study profile."""
    data = load_data("profiles-v1.json")
    if not isinstance(context, str) or not isinstance(background, str) or context not in data["contexts"] or background not in data["backgrounds"]:
        raise ValueError("Choose data-marks/filled-fields and light/dark")
    return {**data, "id": f"{data['version']}/{context}/{background}",
            "context": context, "background": data["backgrounds"][background],
            "criteria": data["contexts"][context]}
