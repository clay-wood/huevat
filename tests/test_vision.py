import pytest

from huevat import simulate
from huevat.vision import MATRICES


@pytest.mark.parametrize("condition, expected", [
    ("protan", (.42660847, .37265428, 0)),
    ("deutan", (.64005956, .56580694, 0)),
    ("tritan", (1, 0, .05838597)),
])
def test_severity_100_red_references(condition, expected):
    # Matrix first column (linear red), clipped and independently sRGB encoded.
    assert simulate((1, 0, 0), condition) == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("condition", ("protan", "deutan", "tritan"))
@pytest.mark.parametrize("gray", (0, .18, .5, 1))
def test_neutral_preservation(condition, gray):
    assert simulate((gray, gray, gray), condition) == pytest.approx((gray,) * 3, abs=1e-6)


@pytest.mark.parametrize("condition", ("normal", "unknown", None, []))
def test_invalid_condition(condition):
    with pytest.raises(ValueError, match="Choose"):
        simulate((0, 0, 0), condition)


def test_input_validation_and_immutable_matrices():
    with pytest.raises(ValueError):
        simulate((2, 0, 0), "protan")
    with pytest.raises(TypeError):
        MATRICES["protan"] = ()
