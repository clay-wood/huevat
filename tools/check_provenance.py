"""Verify extracted-file fingerprints; optionally verify the original checkout."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    # Git/Windows newline translation must not change a text fingerprint.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "docs/extraction.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        target = ROOT / entry["destination"]
        if digest(target) != entry["destination_sha256_lf"]:
            raise SystemExit(f"Extraction fingerprint mismatch: {target}")
        if args.source_root is not None:
            source = args.source_root / entry["source"]
            if digest(source) != entry["source_sha256_lf"]:
                raise SystemExit(f"Source snapshot mismatch: {source}")
    if args.source_root is not None:
        for entry in manifest["source_only_files"]:
            source = args.source_root / entry["source"]
            if digest(source) != entry["source_sha256_lf"]:
                raise SystemExit(f"Source snapshot mismatch: {source}")
    print(f"Verified {len(manifest['files'])} extraction fingerprints" +
          (" and source snapshot" if args.source_root else ""))


if __name__ == "__main__":
    main()
