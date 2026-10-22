"""References and regression tests extracted from sketchplot's color tests."""
import math

import pytest

import huevat as hv


@pytest.mark.parametrize("rgb, expected", [
    ((0, 0, 0), (0, 0, 0)),
    ((1, 1, 1), (1, 0, 0)),
    ((1, 0, 0), (.6279553606, .2248630611, .1258462985)),
    ((0, 1, 0), (.8664396115, -.2338875742, .1794984799)),
    ((0, 0, 1), (.4520137184, -.0324569842, -.3115281477)),
])
def test_published_oklab_references(rgb, expected):
    # Ottosson's 2021 matrices, D65. Rounded coefficients limit inverse accuracy.
    assert hv.srgb_to_oklab(rgb) == pytest.approx(expected, abs=4e-8)
    assert hv.oklab_to_srgb(expected) == pytest.approx(rgb, abs=2e-6)


def test_grid_roundtrips():
    for r in (0, .2, .5, 1):
        for g in (0, .2, .5, 1):
            for b in (0, .2, .5, 1):
                lab = hv.srgb_to_oklab((r, g, b))
                recovered = hv.oklab_to_srgb(hv.oklch_to_oklab(hv.oklab_to_oklch(lab)))
                assert recovered == pytest.approx((r, g, b), abs=2e-6)


@pytest.mark.parametrize("value", (0, .0031308, .01, .18, 1))
def test_srgb_transfer(value):
    assert hv.linearize(hv.encode(value)) == pytest.approx(value, abs=3e-9)


def test_neutral_and_hue_wrap():
    assert hv.oklab_to_oklch((.5, 0, 0)) == (.5, 0, 0)
    assert hv.oklch_to_oklab((.5, .1, -30)) == pytest.approx(hv.oklch_to_oklab((.5, .1, 330)))
    assert hv.oklch_to_oklab((.5, .1, 390)) == pytest.approx(hv.oklch_to_oklab((.5, .1, 30)))


@pytest.mark.parametrize("hue", range(0, 360, 30))
@pytest.mark.parametrize("lightness", (.15, .5, .85))
def test_gamut_mapping_preserves_lightness_and_hue(lightness, hue):
    mapped = hv.gamut_map((lightness, .4, hue))
    assert hv.in_gamut(mapped, tolerance=0)
    actual_l, actual_c, actual_h = hv.oklab_to_oklch(hv.srgb_to_oklab(mapped))
    assert actual_l == pytest.approx(lightness, abs=1e-7)
    assert 0 < actual_c < .4
    angular_error = (actual_h - hue + 180) % 360 - 180
    assert abs(angular_error) < .001


def test_gamut_mapping_is_chroma_reduction():
    raw = hv.oklab_to_srgb(hv.oklch_to_oklab((.65, .4, 30)))
    assert not hv.in_gamut(raw)
    mapped = hv.gamut_map((.65, .4, 30))
    assert mapped != pytest.approx(tuple(min(1, max(0, c)) for c in raw), abs=.01)
    assert hv.gamut_map((0, .3, 250)) == (0, 0, 0)
    assert hv.gamut_map((1, .3, 250)) == (1, 1, 1)
    rgb = (.2, .4, .6)
    assert hv.gamut_map(hv.oklab_to_oklch(hv.srgb_to_oklab(rgb))) == pytest.approx(rgb, abs=2e-6)


@pytest.mark.parametrize("bad", [None, "123", (1, 2), (1, 2, 3, 4), (0, math.nan, 0), (0, math.inf, 0)])
def test_invalid_coordinates(bad):
    for function in (hv.srgb_to_oklab, hv.oklab_to_srgb, hv.oklch_to_oklab,
                     hv.oklab_to_oklch, hv.in_gamut, hv.gamut_map, hv.to_hex):
        with pytest.raises(ValueError):
            function(bad)


@pytest.mark.parametrize("bad", [(-.1, .2, 0), (1.1, .2, 0), (.5, -.2, 0)])
def test_invalid_gamut_coordinates(bad):
    with pytest.raises(ValueError):
        hv.gamut_map(bad)


@pytest.mark.parametrize("tolerance", [-1, math.nan, math.inf, "bad"])
def test_invalid_tolerance(tolerance):
    with pytest.raises(ValueError):
        hv.in_gamut((0, 0, 0), tolerance=tolerance)


@pytest.mark.parametrize("bad", [(-.01, 0, 0), (1.01, 0, 0)])
def test_outside_srgb_rejected(bad):
    for function in (hv.srgb_to_oklab, hv.to_hex):
        with pytest.raises(ValueError):
            function(bad)
    with pytest.raises(ValueError):
        hv.contrast(bad, (0, 0, 0))


def test_quantization_and_hex_roundtrip():
    assert hv.to_hex(hv.from_hex("#ABCDEF")) == "#abcdef"
    for byte in range(256):
        value = f"#{byte:02x}{byte:02x}{byte:02x}"
        assert hv.to_hex(hv.from_hex(value)) == value
    assert hv.to_hex((.5, 0, 1)) == "#8000ff"
    assert hv.to_hex((-5e-8, 1 + 5e-8, 0)) == "#00ff00"


@pytest.mark.parametrize("bad", [None, "#abc", "#12345678", "123456", "#gg0000", "#-10000", "# 10000", "#000000\n"])
def test_invalid_hex(bad):
    with pytest.raises(ValueError):
        hv.from_hex(bad)


def test_distance_and_contrast():
    assert hv.distance((0, 0, 0), (0, 0, 0)) == 0
    assert hv.distance((0, 0, 0), (1, 2, 2)) == 3
    assert hv.contrast((0, 0, 0), (1, 1, 1)) == pytest.approx(21)
    assert hv.contrast((.5, .5, .5), (.5, .5, .5)) == 1
    assert hv.contrast((1, 0, 0), (1, 1, 1)) == pytest.approx(3.99847677)
    assert hv.contrast((1, 1, 1), (1, 0, 0)) == pytest.approx(3.99847677)
