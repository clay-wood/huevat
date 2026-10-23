"""Small release registry and cached immutable prepared designs (stdlib only)."""
from functools import lru_cache

from ._data import load_data
from .gradients import QualityReport, fingerprint
from .sampling import known_counts


@lru_cache(maxsize=1)
def _registry():
    data = load_data("release-v1.json")
    if data["version"] != "h4-release-v1": raise ValueError("Unsupported release registry")
    return data


def design_ids(*, family=None, background=None, role=None):
    """Immutable IDs; discovery reads only a small metadata resource.

    Roles: ``default`` (retained v0.1 choices), ``legacy`` (original categorical
    style), ``experimental`` (the new named collection). None means all roles.
    Release role does not replace the numerical reports' review/approval flags.
    """
    if family not in (None, "categorical", "sequential", "diverging", "multihue", "spectral"):
        raise ValueError("Unknown family")
    if background not in (None, "light", "dark"): raise ValueError("Choose light or dark")
    if role not in (None, "default", "legacy", "experimental"): raise ValueError("Unknown release role")
    return tuple(k for k, v in _registry()["designs"].items()
                 if (family is None or v["family"] == family)
                 and (background is None or v["background"] == background)
                 and (role is None or v["role"] == role))


def design_info(identifier):
    """Immutable identity, provenance and release policy; no large audit load."""
    if not isinstance(identifier, str): raise ValueError("Supply an immutable design ID")
    try: return QualityReport(_registry()["designs"][identifier])
    except KeyError: raise ValueError("Unknown design ID; use design_ids()") from None


@lru_cache(maxsize=16)
def get_design(identifier):
    """Load an exact prepared ID and verify its recipe hash; never optimize.

    Repeated lookups reuse immutable designs. Standard factories and old recipe
    loaders retain their original behavior and identifiers.
    """
    info = design_info(identifier)
    factory, background = info["factory"], info["background"]
    if factory == "categorical":
        from . import categorical
        result = categorical(info["count"], background=background, style=info["style"])
    elif factory in ("sequential", "diverging"):
        from . import sequential, diverging
        result = {"sequential": sequential, "diverging": diverging}[factory](background=background)
    elif factory in ("multihue", "spectral"):
        from . import multihue, spectral
        result = {"multihue": multihue, "spectral": spectral}[factory](background=background)
    elif factory == "gradient":
        from . import gradient
        result = gradient(info["name"], background=background)
    else: raise ValueError("Unsupported registry factory")
    body = result._recipe if hasattr(result, "_recipe") else result.report["recipe"]
    from .gradients import _thaw
    if body["identifier"] != identifier or fingerprint(_thaw(body)) != info["recipe_sha256"]:
        raise ValueError("Registered design identity/hash no longer matches the prepared source")
    view = _thaw(body)
    if hasattr(result, "_reverse"): view["reversed"] = result._reverse
    if fingerprint(view) != info["view_sha256"]:
        raise ValueError("Registered design orientation no longer matches the prepared view")
    return result


def nearby_counts(gradient, n, *, context=None):
    """Prepared passing uniform counts, nearest first; unlisted means unknown."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer of at least two")
    return tuple(sorted(known_counts(gradient, context=context), key=lambda count: (abs(count-n), count)))
