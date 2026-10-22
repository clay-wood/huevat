import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("colorspacious")

import huevat as hv
from huevat.design import generate, validate_gradient
from huevat.gradients import fingerprint

pytestmark = pytest.mark.research


def test_completed_multistart_search_reproduces_and_reports_optimization():
    first = generate("sequential", ("#0066aa",), starts=2, max_seconds=60)
    second = generate("sequential", ("#0066aa",), starts=2, max_seconds=60)
    assert first.report.screen_pass and second.report.screen_pass
    assert fingerprint(first.to_recipe()["recipe"]) == fingerprint(second.to_recipe()["recipe"])
    assert len(first.report["search"]["optimizer_runs"]) == 2
    assert not first.report["search"]["deadline_reached"]
    assert first.report["preferred_changes"][0]["supplied"] == "#0066aa"


def test_deadline_is_search_exhaustion_not_infeasibility():
    with pytest.raises(hv.SearchExhaustedError) as error:
        generate("sequential", ("#0066aa",), max_seconds=1e-9, starts=2)
    assert error.value.report["outcome"] == "search-exhausted"
    assert error.value.report["deadline_reached"]
    assert not error.value.report["infeasibility_proven"]


def test_custom_background_is_separately_measured_and_recipe_can_be_revalidated():
    gradient = generate("diverging", ("#0072b2", "#d55e00"), background="#171d26", starts=2, max_seconds=60)
    assert gradient.report.screen_pass
    assert gradient.background == hv.from_hex("#171d26")
    assert gradient.report["background_status"].startswith("custom separately evaluated")
    loaded = hv.load_recipe(gradient.to_json())
    assert loaded.report.screen_pass
    assert loaded.at(.3) == gradient.at(.3)


def test_unprepared_but_passing_bin_count_receives_independent_audit():
    gradient = hv.sequential()
    # A new identity intentionally bypasses the prepared discrete evidence.
    envelope = gradient.to_recipe()
    envelope["recipe"]["identifier"] = "independently-audited-copy"
    envelope["sha256"] = fingerprint(envelope["recipe"])
    loaded = hv.load_recipe(envelope)
    palette = loaded.discrete(7)
    assert palette.report.screen_pass
    assert all("minimum_cam02_distance" in value for value in palette.report["measurements"].values())
