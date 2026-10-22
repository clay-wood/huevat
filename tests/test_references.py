from dataclasses import FrozenInstanceError
import hashlib
import json

import pytest

import huevat as hv
from huevat._data import load_data
from huevat.references import interpolate
from huevat.vision import simulation_matrix


def test_exact_okabe_ito_and_attribution():
    ref = hv.reference("okabe-ito")
    assert tuple(map(hv.to_hex, ref.colors(8))) == (
        "#000000", "#e69f00", "#56b4e9", "#009e73", "#f0e442", "#0072b2", "#d55e00", "#cc79a7")
    assert "Okabe-Ito" in ref.label
    with pytest.raises(FrozenInstanceError):
        ref.rgb = ()
    with pytest.raises(TypeError):
        ref.rgb[0][0] = 1


def test_count_specific_brewer_values_and_spectral_family():
    ref = hv.reference("brewer-paired")
    assert len(ref.rgb) == 12
    assert len(ref.colors(6)) == 6
    with pytest.raises(ValueError, match="no native"):
        ref.colors(13)
    assert hv.reference("brewer-spectral").family == "spectral"
    assert hv.to_hex(hv.reference("brewer-blues").colors(5)[0]) == "#eff3ff"
    assert hv.reference("brewer-blues").colors(5) != hv.reference("brewer-blues").rgb[:5]


def test_corpus_hashes_and_source_coverage():
    corpus = load_data("references-v1.json")
    assert len(hv.references()) == 13
    assert set(corpus["sources"]) == {"okabe-ito-wong", "colorbrewer", "matplotlib", "colorcet", "colorspacious"}
    for ref in corpus["references"]:
        for key, fingerprint in (("rgb", "rgb_sha256"), ("native_tables", "native_tables_sha256")):
            raw = json.dumps(ref[key], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            assert hashlib.sha256(raw).hexdigest() == ref[fingerprint]
        assert all(hv.in_gamut(rgb, tolerance=0) for rgb in ref["rgb"])


@pytest.mark.parametrize("bad", [True, 1, 2.5, -1, None])
def test_invalid_counts(bad):
    with pytest.raises(ValueError):
        hv.reference("viridis").sample(bad)


def test_sampling_preserves_native_values_and_endpoints():
    ref = hv.reference("viridis")
    assert ref.sample(257)[0] == ref.rgb[0]
    assert ref.sample(257)[-1] == pytest.approx(ref.rgb[-1], abs=1e-15)
    assert interpolate(((0, 0, 0), (1, .5, 0)), .5) == (.5, .25, 0)
    with pytest.raises(ValueError):
        hv.reference("okabe-ito").sample()
    with pytest.raises(ValueError):
        hv.reference("unknown")


def test_four_profiles_are_independent_copies():
    ids = set()
    for context in ("data-marks", "filled-fields"):
        for bg in ("light", "dark"):
            profile = hv.load_profile(context, bg)
            ids.add(profile["id"])
            assert ("background_contrast_min" in profile["criteria"]) == (context == "data-marks")
    assert len(ids) == 4
    profile["ordered"]["speed_cv_max"] = 100
    assert hv.load_profile()["ordered"]["speed_cv_max"] == .35
    with pytest.raises(ValueError):
        hv.load_profile("unknown")


def test_machado_severity_reference_and_interpolation():
    expected = ((.547494, .607765, -.155259), (.181692, .781742, .036566), (-.010410, .027275, .983136))
    assert simulation_matrix("deutan", 50) == expected
    for row, lo, hi in zip(simulation_matrix("deutan", 53.1), simulation_matrix("deutan", 50), simulation_matrix("deutan", 60)):
        assert row == pytest.approx(tuple(.69*a + .31*b for a, b in zip(lo, hi)))
    assert hv.simulate((.2, .4, .6), "protan", severity=0) == pytest.approx((.2, .4, .6))


@pytest.mark.parametrize("severity", [True, -1, 101, float("nan"), "50"])
def test_invalid_severities(severity):
    with pytest.raises(ValueError):
        hv.simulate((1, 0, 0), "protan", severity=severity)
