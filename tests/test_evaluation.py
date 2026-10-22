import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("colorspacious")

from huevat import reference
from huevat.evaluation import evaluate, _spaces, condition_colors
from huevat.study import compare_studies, negative_controls
from huevat.vision import simulation_matrix

pytestmark = pytest.mark.research


@pytest.mark.parametrize("name,criterion", [
    ("repeated-colors", "unique_exported_colors"),
    ("rgb-red-green", "arm_0/lightness_order"),
    ("lightness-reversal", "arm_0/lightness_order"),
    ("broad-flat", "arm_0/flat_run_fraction"),
    ("narrow-spike", "arm_0/spike_ratio"),
    ("excessive-classes", "oklab_minimum_adjacent"),
])
def test_deliberate_defects_fail_the_intended_test(name, criterion):
    _, family, rgb, discrete = next(c for c in negative_controls() if c[0] == name)
    result = evaluate(rgb, family, context="data-marks" if family == "categorical" else "filled-fields",
                      encoding="u8", discrete=discrete)
    assert not result["screen_pass"]
    assert any(c["name"] == criterion and not c["passed"] and c["condition"] == "normal" for c in result["criteria"])
    assert result["approved_default"] is False


def test_smooth_ordered_gray_passes_float_screens_and_no_cell_contrast_gate():
    # A constructed constant-speed Oklab-neutral path is a positive control.
    from huevat import oklab_to_srgb
    rgb = np.array([oklab_to_srgb((L, 0, 0)) for L in np.linspace(.2, .8, 257)])
    result = evaluate(rgb, "sequential")
    assert result["screen_pass"]
    assert not any(c["name"] == "background_contrast" for c in result["criteria"])
    assert result["visual_review"] == "pending"
    assert not result["approved_default"]


def test_invalid_input_is_an_error_not_a_search_or_quality_result():
    for rgb in ([[0, 0, 0]], [[2, 0, 0], [0, 0, 0]], [[np.nan, 0, 0], [0, 0, 0]]):
        with pytest.raises(ValueError):
            evaluate(rgb, "categorical", context="data-marks")
    with pytest.raises(ValueError, match="odd"):
        evaluate(np.full((4, 3), .5), "diverging")


def test_pair_matrices_and_quantization_are_reported_separately():
    rgb = reference("okabe-ito").colors(4)
    result = evaluate(rgb, "categorical", context="data-marks", encoding="u8", background="dark")
    for condition in result["conditions"].values():
        for name in ("oklab", "cam02_ucs"):
            matrix = np.asarray(condition[name]["distance_matrix"])
            assert matrix.shape == (4, 4)
            np.testing.assert_allclose(matrix, matrix.T, atol=1e-12)
            np.testing.assert_allclose(matrix.diagonal(), 0)
    assert len(result["conditions"]) == 8
    assert result["encoding"] == "u8"


def test_independent_cam02_reference_and_default_matrices():
    from colorspacious import cspace_convert
    from colorspacious.cvd import machado_et_al_2009_matrix
    rgb = np.array([[.25, .5, .75], [.75, .25, .5]])
    lab, cam = _spaces(rgb)
    np.testing.assert_allclose(cspace_convert(cam, "CAM02-UCS", "sRGB1"), rgb, atol=1e-10)
    assert not np.allclose(cam / 100, lab, atol=.01)
    for condition, name in (("protan", "protanomaly"), ("deutan", "deuteranomaly"), ("tritan", "tritanomaly")):
        for severity in (0, 50, 53.1, 80, 100):
            np.testing.assert_allclose(simulation_matrix(condition, severity), machado_et_al_2009_matrix(name, severity), atol=1e-12)
    _, clip = condition_colors(np.array([[1., 0, 0]]), "protan-100")
    assert clip["clipped_channels"] == 1


def test_spectral_uses_two_arms_with_shared_center():
    result = evaluate(reference("brewer-spectral").sample(257), "spectral")
    path = result["conditions"]["normal"]["oklab_path"]
    assert len(path["arms"]) == 2
    assert path["center"]["shared_center"]
    assert len(path["arms"][0]["lightness"]) == 129
    assert any(c["name"] == "center_chroma" for c in result["criteria"])


def test_reproducibility_tolerances_and_decisions():
    compare_studies({"runtime": {"x": "old"}, "value": [1.]}, {"runtime": {"x": "new"}, "value": [1. + 1e-10]})
    with pytest.raises(ValueError):
        compare_studies({"value": 1.}, {"value": 1.01})
    with pytest.raises(ValueError):
        compare_studies({"passed": True}, {"passed": False})
