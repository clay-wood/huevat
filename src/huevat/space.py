"""Small dependency-free sRGB/Oklab/Oklch calculations (D65 white).

Matrices: Björn Ottosson, https://bottosson.github.io/posts/oklab/ (2021 update).
RGB inputs/outputs are gamma-encoded floats, unless explicitly called linear.
"""
import math
import re

GAMUT_TOLERANCE = 1e-7


def _triple(values):
    if isinstance(values, (str, bytes)):
        raise ValueError("Color coordinates must be three finite numbers")
    try:
        result = tuple(float(v) for v in values)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Color coordinates must be three finite numbers") from None
    if len(result) != 3 or not all(math.isfinite(v) for v in result):
        raise ValueError("Color coordinates must be three finite numbers")
    return result


def linearize(value):
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055)**2.4


def encode(value):
    return 12.92 * value if value <= .0031308 else 1.055 * value**(1 / 2.4) - .055


def srgb_to_oklab(rgb):
    """Convert encoded sRGB in [0, 1] to D65 Oklab (L on a 0-1 scale)."""
    r, g, b = (linearize(v) for v in _triple(rgb))
    if not all(0 <= v <= 1 for v in (r, g, b)):
        raise ValueError("sRGB channels must be in [0, 1]")
    l = (.4122214708 * r + .5363325363 * g + .0514459929 * b)**(1 / 3)
    m = (.2119034982 * r + .6806995451 * g + .1073969566 * b)**(1 / 3)
    s = (.0883024619 * r + .2817188376 * g + .6299787005 * b)**(1 / 3)
    return (.2104542553*l + .793617785*m - .0040720468*s,
            1.9779984951*l - 2.428592205*m + .4505937099*s,
            .0259040371*l + .7827717662*m - .808675766*s)


def oklab_to_srgb(lab):
    """Convert without clipping. Out-of-gamut values remain detectable."""
    L, a, b = _triple(lab)
    l = (L + .3963377774*a + .2158037573*b)**3
    m = (L - .1055613458*a - .0638541728*b)**3
    s = (L - .0894841775*a - 1.291485548*b)**3
    return tuple(encode(v) for v in
        (4.0767416621*l - 3.3077115913*m + .2309699292*s,
         -1.2684380046*l + 2.6097574011*m - .3413193965*s,
         -.0041960863*l - .7034186147*m + 1.707614701*s))


def oklch_to_oklab(lch):
    L, C, h = _triple(lch)
    if C < 0:
        raise ValueError("Oklch chroma must be nonnegative")
    return L, C * math.cos(math.radians(h % 360)), C * math.sin(math.radians(h % 360))


def oklab_to_oklch(lab):
    L, a, b = _triple(lab)
    C = math.hypot(a, b)
    return L, C, math.degrees(math.atan2(b, a)) % 360 if C > 1e-12 else 0.


def in_gamut(rgb, *, tolerance=GAMUT_TOLERANCE):
    """Test encoded sRGB bounds, allowing documented conversion roundoff."""
    if not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Gamut tolerance must be finite and nonnegative")
    return all(-tolerance <= v <= 1 + tolerance for v in _triple(rgb))


def gamut_map(lch):
    """Reduce chroma at constant L/h to fit sRGB; not CSS local-MINDE mapping.

    Uses 32 deterministic bisections. Tiny conversion-roundoff excursions are
    snapped only after an in-gamut result has been found; there is no RGB clipping
    substitute for chroma reduction.
    """
    L, C, h = _triple(lch)
    if not 0 <= L <= 1 or C < 0:
        raise ValueError("Oklch requires lightness in [0, 1] and nonnegative chroma")
    if L in (0, 1):
        return (L, L, L)
    def convert(c):
        return oklab_to_srgb(oklch_to_oklab((L, c, h)))
    rgb = convert(C)
    if not in_gamut(rgb):
        lo, hi = 0., C
        for _ in range(32):
            mid = (lo + hi) / 2
            if in_gamut(convert(mid)):
                lo = mid
            else:
                hi = mid
        rgb = convert(lo)
    return tuple(min(1., max(0., v)) for v in rgb)


def to_hex(rgb):
    """Quantize encoded sRGB using Python's nearest, ties-to-even rounding."""
    rgb = _triple(rgb)
    if not in_gamut(rgb):
        raise ValueError("Cannot export out-of-gamut sRGB; gamut-map first")
    return "#" + "".join(f"{round(min(1., max(0., v))*255):02x}" for v in rgb)


def from_hex(value):
    if not isinstance(value, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
        raise ValueError("Expected a six-digit hexadecimal color")
    try:
        return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))
    except ValueError:
        raise ValueError("Expected a six-digit hexadecimal color") from None


def distance(first, second):
    """Euclidean Oklab distance; not a categorical accessibility guarantee."""
    return math.dist(_triple(first), _triple(second))


def contrast(first, second):
    """WCAG relative-luminance contrast ratio for two encoded sRGB triples."""
    def luminance(rgb):
        rgb = _triple(rgb)
        if not in_gamut(rgb):
            raise ValueError("Contrast requires in-gamut sRGB")
        return sum(w * linearize(c) for w, c in zip((.2126, .7152, .0722), rgb))
    a, b = sorted((luminance(first), luminance(second)))
    return (b + .05) / (a + .05)
