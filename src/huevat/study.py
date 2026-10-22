"""Deterministic H1 study assembly; no network, rendering or optimization."""
import hashlib
import importlib.metadata as md
from importlib.resources import files
import json

import numpy as np
from colorspacious import CIECAM02Space

from ._data import load_data
from .evaluation import ALGORITHM_VERSION, evaluate
from .references import reference, references


def negative_controls():
    """Deliberate defects constructed independently of reference measurements."""
    t = np.linspace(0, 1, 257)
    gray = lambda v: np.repeat(np.asarray(v)[:, None], 3, axis=1)
    reversal = .1 + .8 * t
    reversal[110:145] = reversal[110:145][::-1]
    flat = .1 + .8 * np.interp(t, [0, .3, .7, 1], [0, .5, .5, 1])
    spike = .1 + .8 * (.5 * t + .5 * (1 + np.tanh((t - .5) / .003)) / 2)
    return [
        ("repeated-colors", "categorical", np.array([[.2, .4, .6], [.2, .4, .6], [.8, .2, .1]]), False),
        ("rgb-red-green", "sequential", np.column_stack((1 - t, t, np.zeros_like(t))), False),
        ("lightness-reversal", "sequential", gray(reversal), False),
        ("broad-flat", "sequential", gray(flat), False),
        ("narrow-spike", "sequential", gray(spike), False),
        ("excessive-classes", "sequential", gray(np.linspace(.1, .9, 129)), True),
    ]


def build_study(protocol_sha256):
    profiles = load_data("profiles-v1.json")
    cases = []

    def add(identifier, ref, rgb, context, background, encoding, discrete, selection, control=False, family=None):
        cases.append({"id": identifier, "reference": ref.identifier if ref else identifier.split('/')[1],
                      "negative_control": control, "selection": selection,
                      "result": evaluate(rgb, ref.family if ref else family,
                                         context=context, background=background, encoding=encoding,
                                         discrete=discrete)})

    for identifier in references():
        ref = reference(identifier)
        for background in profiles["backgrounds"]:
            for encoding in ("float", "u8"):
                if ref.family == "categorical":
                    for n in profiles["study"]["categorical_counts"]:
                        add(f"{identifier}/{background}/{n}/{encoding}", ref, ref.colors(n), "data-marks",
                            background, encoding, False, ref.selection)
                else:
                    add(f"{identifier}/{background}/path/{encoding}", ref,
                        ref.sample(profiles["study"]["gradient_samples"]), "filled-fields",
                        background, encoding, False, ref.path_adaptation)
                    for n in profiles["study"]["discrete_counts"]:
                        for context in profiles["contexts"]:
                            add(f"{identifier}/{background}/{n}/{context}/{encoding}", ref, ref.colors(n),
                                context, background, encoding, True, ref.selection)
    controls = negative_controls()
    for identifier, family, rgb, discrete in controls:
        for background in profiles["backgrounds"]:
            add(f"control/{identifier}/{background}", None, rgb, "data-marks" if family == "categorical" else "filled-fields",
                background, "u8", discrete, "deliberately defective synthetic selection", control=True, family=family)
    viewing = CIECAM02Space.sRGB
    corpus = load_data("references-v1.json")
    return {
        "schema_version": 1, "study_version": "baseline-v1", "algorithm_version": ALGORITHM_VERSION,
        "protocol_sha256": protocol_sha256, "resources": load_resource_manifest(),
        "implementation_sha256_lf": {
            name: hashlib.sha256(files("huevat").joinpath(name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in ("_data.py", "space.py", "vision.py", "references.py", "evaluation.py", "study.py")
        },
        "runtime": {name: md.version(name) for name in ("numpy", "colorspacious", "matplotlib", "colorcet")},
        "viewing_conditions": {"white_XYZ100": viewing.XYZ100_w.tolist(), "Y_b": float(viewing.Y_b),
                               "L_A_cd_m2": float(viewing.L_A), "surround": "average", "background_adaptation": "fixed for both backgrounds"},
        "source_versions": corpus["sources"], "parameters": profiles["study"],
        "visual_review": {"status": "pending", "reviewer": None,
                          "meaning": "Artifacts support review; numerical screens do not establish human discrimination."},
        "cases": cases,
    }


def load_resource_manifest():
    # Read each resource through the verifier; canonical hashes are independent
    # of JSON formatting and platform line endings.
    return {name: hashlib.sha256(json.dumps(load_data(name), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            for name in ("profiles-v1.json", "references-v1.json", "machado-v1.json")}


def compare_studies(expected, actual, path="root"):
    """Compare numerical results with fixed 1e-8 tolerances, including decisions."""
    if path == "root":
        expected = {k: v for k, v in expected.items() if k != "runtime"}
        actual = {k: v for k, v in actual.items() if k != "runtime"}
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise ValueError(f"Study keys differ at {path}")
        for key in expected:
            compare_studies(expected[key], actual[key], path + "/" + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError(f"Study lengths differ at {path}")
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare_studies(left, right, path + f"/{index}")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not np.isclose(expected, actual, rtol=1e-8, atol=1e-8):
            raise ValueError(f"Study measurement differs at {path}: {expected} != {actual}")
    elif type(expected) is not type(actual) or expected != actual:
        raise ValueError(f"Study value differs at {path}")
