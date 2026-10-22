"""Rebuild frozen reference data offline from retained sources and installed versions.

Run with huevat[research]. Use --check for byte-for-byte corpus reproduction.
This tool never downloads or changes any upstream palette.
"""
import argparse
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import re

import colorcet
import colorspacious.cvd
import matplotlib
import matplotlib._cm_listed

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src/huevat/data"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build():
    brewer_path = ROOT / "tools/sources/colorbrewer.json"
    brewer = json.loads(brewer_path.read_text(encoding="utf-8"))
    sources = {
        "okabe-ito-wong": {
            "version": "Okabe-Ito 2002; Wong 2011; attribution correction 2023",
            "url": "https://jfly.uni-koeln.de/color/",
            "correction": "https://doi.org/10.1038/s41592-023-01974-0",
            "paper": "https://doi.org/10.1038/nmeth.1618",
            "license": "Numerical color specifications transcribed from Figure 2; article not redistributed",
        },
        "colorbrewer": {
            "version": "official export snapshot 2026-10-22 sha256:" + sha(brewer_path.read_bytes()),
            "url": "https://colorbrewer2.org/export/colorbrewer.json",
            "raw_sha256": sha(brewer_path.read_bytes()),
            "attribution": "Color specifications and designs by Cynthia A. Brewer, Mark Harrower and The Pennsylvania State University",
            "license": "Apache-2.0; licenses/colorbrewer-Apache-2.0.txt",
        },
    }
    for name, module, license_name in (
        ("matplotlib", matplotlib._cm_listed, "matplotlib-LICENSE.txt"),
        ("colorcet", colorcet, "colorcet-CC-BY-4.0.txt"),
        ("colorspacious", colorspacious.cvd, "colorspacious-MIT.txt"),
    ):
        sources[name] = {
            "version": md.version(name),
            "url": {"matplotlib": "https://matplotlib.org/stable/users/explain/colors/colormaps.html",
                    "colorcet": "https://colorcet.holoviz.org/",
                    "colorspacious": "https://github.com/njsmith/colorspacious/blob/v1.1.2/colorspacious/cvd.py"}[name],
            "raw_sha256": sha(Path(module.__file__).read_bytes().replace(b"\r\n", b"\n")),
            "license": "licenses/" + license_name,
        }
    entries = []

    def add(identifier, family, rgb, source, tables=None, **metadata):
        entry = {"id": identifier, "family": family, "source": source,
                 "rgb": rgb, "native_tables": tables or {}, **metadata}
        entry["rgb_sha256"] = sha(canonical(rgb))
        entry["native_tables_sha256"] = sha(canonical(entry["native_tables"]))
        entries.append(entry)

    exact = ["000000", "e69f00", "56b4e9", "009e73", "f0e442", "0072b2", "d55e00", "cc79a7"]
    rgb = [[int(c[i:i+2], 16) / 255 for i in (0, 2, 4)] for c in exact]
    add("okabe-ito", "categorical", rgb, "okabe-ito-wong",
        label="Okabe-Ito (Wong Figure 2)", selection="source-order prefix")
    for name, family in (("Set2", "categorical"), ("Dark2", "categorical"),
                         ("Paired", "categorical"), ("Blues", "sequential"),
                         ("YlGnBu", "sequential"), ("RdBu", "diverging"),
                         ("Spectral", "spectral")):
        tables = {n: [[int(v) / 255 for v in re.findall(r"\d+", color)] for color in table]
                  for n, table in brewer[name].items() if n.isdigit()}
        largest = str(max(map(int, tables)))
        add("brewer-" + name.lower(), family, tables[largest], "colorbrewer", tables,
            label="ColorBrewer " + name, selection="native count-specific table",
            path_adaptation="piecewise-linear encoded-sRGB study adaptation of largest native table")
    for name in ("viridis", "cividis"):
        add(name, "sequential", [list(map(float, row)) for row in matplotlib.colormaps[name].colors],
            "matplotlib", label=name, selection="uniform endpoint-inclusive sampling",
            path_adaptation="piecewise-linear encoded-sRGB study adaptation of native 256-entry LUT")
    for identifier, name, family, label in (
        ("cet-fire", "linear_kryw_0_100_c71", "sequential", "ColorCET fire (Kovesi)"),
        ("cet-coolwarm", "diverging_bwr_40_95_c42", "diverging", "ColorCET coolwarm (Kovesi)"),
        ("cet-glasbey", "glasbey_bw_minc_20", "categorical", "ColorCET Glasbey"),
    ):
        add(identifier, family, [list(map(float, row)) for row in getattr(colorcet, name)],
            "colorcet", label=label, native_name=name,
            selection="source-order prefix" if family == "categorical" else "uniform endpoint-inclusive sampling",
            path_adaptation="piecewise-linear encoded-sRGB study adaptation" if family != "categorical" else "none")
    corpus = {"schema_version": 1, "version": "references-v1", "sources": sources, "references": entries}
    matrices = {condition: {str(severity): colorspacious.cvd.machado_et_al_2009_matrix(name, severity).tolist()
                           for severity in range(0, 101, 10)}
                for condition, name in (("protan", "protanomaly"), ("deutan", "deuteranomaly"), ("tritan", "tritanomaly"))}
    return {"references-v1.json": corpus,
            "machado-v1.json": {"version": "machado-2009-colorspacious-1.1.2", "source": sources["colorspacious"], "matrices": matrices}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, value in build().items():
        data = json.dumps(value, indent=2, allow_nan=False).encode() + b"\n"
        path = DATA / name
        if args.check:
            if path.read_bytes() != data:
                raise SystemExit(f"Frozen data differs: {name}; use the recorded source versions")
        else:
            if path.exists():
                raise SystemExit(f"Refusing to replace frozen resource {name}")
            path.write_bytes(data)
    print("Frozen reference corpus and Machado tables " + ("reproduced" if args.check else "written"))


if __name__ == "__main__":
    main()
