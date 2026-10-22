"""Read hash-checked, data-only resources without optional dependencies."""
import hashlib
from importlib.resources import files
import json


def load_data(name):
    root = files("huevat").joinpath("data")
    manifest = json.loads(root.joinpath("manifest-v1.json").read_text(encoding="utf-8"))
    if name not in manifest["sha256_lf"]:
        raise ValueError(f"Unknown frozen resource: {name}")
    raw = root.joinpath(name).read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != manifest["sha256_lf"][name]:
        raise ValueError(f"Frozen resource hash mismatch: {name}")
    return json.loads(raw)
