from dataclasses import FrozenInstanceError
import json
import math

import pytest

import huevat as hv
from huevat._certify import certify
from huevat.gradients import fingerprint


@pytest.mark.parametrize("constructor", [hv.sequential, hv.diverging])
@pytest.mark.parametrize("background", ["light", "dark"])
def test_prepared_paths_are_immutable_and_pass_all_stated_gates(constructor, background):
    gradient = constructor(background=background)
    assert gradient.report.screen_pass
    assert gradient.report["certificate"]["passed"]
    assert gradient.report["dense_audit"]["cvd_order_pass"]
    assert all(check["passed"] for check in gradient.report["checks"])
    assert not gradient.report["approved_default"]
    with pytest.raises(FrozenInstanceError):
        gradient._reverse = True
    with pytest.raises(TypeError):
        gradient.report["checks"][0]["passed"] = False
    assert hv.in_gamut(gradient.at(.35), tolerance=0)


def test_reversal_samples_and_reports_are_consistent():
    gradient = hv.diverging()
    reverse = gradient.reversed()
    for t in (0, .01, .25, .5, .77, 1):
        assert reverse.at(t) == gradient.at(1-t)
    assert reverse.reversed().to_recipe() == gradient.to_recipe()
    assert tuple(reverse.discrete(7)) == tuple(gradient.discrete(7))[::-1]
    assert tuple(reverse.discrete(7).report["hex"]) == tuple(reverse.discrete(7))
    changes = gradient.report["preferred_changes"]
    reversed_changes = reverse.report["preferred_changes"]
    assert reversed_changes[0]["parameter"] == 1-changes[0]["parameter"]


def test_discrete_bins_are_exactly_requested_including_even_counts():
    for gradient in (hv.sequential(), hv.diverging(), hv.diverging(background="dark")):
        for n in (2, 4, 5, 7):
            palette = gradient.discrete(n)
            assert len(palette) == n
            assert tuple(palette) == tuple(hv.to_hex(gradient.at(i/(n-1))) for i in range(n))
            assert palette.report.screen_pass
            assert len(set(palette)) == n
            assert isinstance(palette[:2], tuple)
    with pytest.raises(hv.QualityError) as error:
        hv.diverging().discrete(8)
    assert not error.value.report.screen_pass
    # A different requested selection is evaluated separately; no colors drop.
    assert len(hv.diverging().discrete(9)) == 9


def test_excessive_count_has_a_real_bound_for_this_path():
    with pytest.raises(hv.ConstraintConflictError) as error:
        hv.sequential().discrete(129)
    report = error.value.report
    assert report["required_total_distance"] > report["path_length_upper_bound"]
    assert report["scope"].startswith("this fixed gradient")


def test_data_marks_and_filled_fields_have_separate_gates():
    assert hv.sequential().discrete(7).report.screen_pass
    with pytest.raises(hv.QualityError) as error:
        hv.sequential().discrete(7, context="data-marks")
    assert any(check["name"].endswith("background_contrast") and not check["passed"] for check in error.value.report["checks"])


@pytest.mark.parametrize("t", [True, -.01, 1.01, None, "0.5", math.nan, math.inf])
def test_invalid_sample_parameters(t):
    with pytest.raises(ValueError):
        hv.sequential().at(t)


@pytest.mark.parametrize("count", [True, 0, 1, 2.5, None])
def test_invalid_counts(count):
    with pytest.raises(ValueError):
        hv.sequential().discrete(count)


def test_input_errors_precede_optional_generation():
    for kwargs in ({"color":"#bad"}, {"background":"nonsense"}, {"seed":True},
                   {"starts":0}, {"max_seconds":0}, {"context":"unknown"}):
        with pytest.raises(ValueError):
            hv.sequential(**kwargs)
    with pytest.raises(ValueError):
        hv.diverging(colors=("#0072b2",))


def test_recipe_roundtrip_ignores_forged_claims_and_rejects_tampering():
    gradient = hv.diverging(background="dark").reversed()
    envelope = gradient.to_recipe()
    envelope["evidence"] = {"screen_pass": False, "made_up": True}
    loaded = hv.load_recipe(envelope)
    assert loaded.report.screen_pass
    assert loaded.at(.3) == gradient.at(.3)
    envelope["recipe"]["segments"][0][0][0] += .1
    with pytest.raises(ValueError, match="hash"):
        hv.load_recipe(envelope)


def test_unknown_recipe_is_explicitly_unvalidated_without_optional_audit():
    envelope = hv.sequential().to_recipe()
    envelope["recipe"]["identifier"] = "a-custom-data-only-recipe"
    envelope["sha256"] = fingerprint(envelope["recipe"])
    loaded = hv.load_recipe(envelope, validate=False)
    assert loaded.at(.4) == hv.sequential().at(.4)
    assert not loaded.report.screen_pass
    assert loaded.report["outcome"] == "unvalidated-recipe"


def test_full_segment_gamut_and_order_checks_catch_between_endpoint_defects():
    recipe = hv.sequential().to_recipe()["recipe"]
    recipe.pop("reversed")
    recipe["knots"] = [0., 1.]
    # Both endpoint grays are in gamut; the interior chroma bulge is not.
    recipe["segments"] = [[[.5,.1,0,0],[0,2.,-2.,0],[0,0,0,0]]]
    assert hv.in_gamut(hv.oklab_to_srgb((.5,0,0)))
    assert hv.in_gamut(hv.oklab_to_srgb((.6,0,0)))
    assert not certify(recipe)["gamut_pass"]
    recipe["segments"] = [[[.5,1.,-1.,0],[0,0,0,0],[0,0,0,0]]]
    assert not certify(recipe)["monotone_lightness"]


@pytest.mark.parametrize("background", ["light", "dark"])
def test_neutral_center_is_continuous_and_differentiable(background):
    gradient = hv.diverging(background=background)
    center = hv.srgb_to_oklab(gradient.at(.5))
    assert math.hypot(center[1],center[2]) < 1e-7
    epsilon = 1e-6
    left = hv.srgb_to_oklab(gradient.at(.5-epsilon))
    right = hv.srgb_to_oklab(gradient.at(.5+epsilon))
    assert max(abs(a-b) for a,b in zip(left,right)) < 1e-8
    left_slope = tuple((b-a)/epsilon for a,b in zip(left,center))
    right_slope = tuple((b-a)/epsilon for a,b in zip(center,right))
    assert max(abs(a-b) for a,b in zip(left_slope,right_slope)) < .001
