"""Artifact coverage and offline-gallery structure, independent of metric code."""
from html.parser import HTMLParser
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "research/baseline-v1"
pytestmark = [pytest.mark.research, pytest.mark.skipif(not BASELINE.exists(), reason="Gallery is a repository artifact, not a base-wheel asset")]


def test_case_coverage_and_no_default_approval():
    summary = json.loads((BASELINE / "summary.json").read_text(encoding="utf-8"))
    cases = summary["cases"]
    assert len(cases) == 296
    assert len({case["id"] for case in cases}) == len(cases)
    assert summary["visual_review"] == "pending"
    controls = [case for case in cases if case["negative_control"]]
    assert len(controls) == 12 and not any(case["screen_pass"] for case in controls)
    for background in ("light", "dark"):
        background_cases = [c for c in cases if c["profile"].endswith('/' + background)]
        assert len(background_cases) == 148
        assert len({c["reference"] for c in background_cases if not c["negative_control"]}) == 13
        assert {c["count"] for c in background_cases if '/path/' in c["id"]} == {257}


class LocalAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attributes):
        if tag in ("img", "script", "link"):
            attrs = dict(attributes)
            self.assets.extend([value for name, value in attrs.items() if name in ("src", "href")])


def test_gallery_uses_existing_local_assets_and_all_panels_have_review_entries():
    parser = LocalAssets()
    parser.feed((BASELINE / "index.html").read_text(encoding="utf-8"))
    assert len(parser.assets) == 48
    for asset in parser.assets:
        assert not asset.startswith(("http:", "https:", "//"))
        assert (BASELINE / asset).is_file()
    review = json.loads((BASELINE / "review.json").read_text(encoding="utf-8"))
    assert {entry["file"] for entry in review["panels"]} == set(parser.assets)
    assert all(entry["status"] == "pending" for entry in review["panels"])


def test_publication_png_dimensions_and_resolution():
    image_module = pytest.importorskip("PIL.Image")
    for path in (BASELINE / "images").glob("*.png"):
        with image_module.open(path) as image:
            assert image.size[0] >= 2100 and image.size[1] >= 2000
            assert image.info["dpi"][0] == pytest.approx(300, abs=.1)
