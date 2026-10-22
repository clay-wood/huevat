"""Record the H0 extraction once, from the selected sketchplot checkout.

This is an explicit maintenance operation, never part of builds/imports.
Existing manifests are preserved; intentional changes need explicit editing.
"""
import argparse
import json
from pathlib import Path

from check_provenance import ROOT, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    pairs = [
        ("src/sketchplot/colors/space.py", "src/huevat/space.py"),
        ("src/sketchplot/colors/vision.py", "src/huevat/vision.py"),
        ("LICENSE", "licenses/sketchplot-MIT.txt"),
    ]
    manifest = {
        "schema_version": 1,
        "extracted_on": "2026-10-22",
        "source_repository": "https://github.com/clay-wood/sketchplot",
        "source_base_commit": "84a0cb0d57cd161adffdcb17f6958b04d99033d6",
        "source_state": "Color modules and tests were untracked working-tree files, not part of the base commit.",
        "hash_encoding": "SHA-256 of bytes with CRLF normalized to LF",
        "files": [
            {"source": source, "destination": destination,
             "source_sha256_lf": digest(args.source_root / source),
             "destination_sha256_lf": digest(ROOT / destination)}
            for source, destination in pairs
        ],
        "source_only_files": [
            {"source": "tests/test_colors.py",
             "source_sha256_lf": digest(args.source_root / "tests/test_colors.py")}
        ],
    }
    with (ROOT / "docs/extraction.json").open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(manifest, indent=2) + "\n")
    print("Recorded H0 extraction manifest")


if __name__ == "__main__":
    main()
