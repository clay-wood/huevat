"""Build/check H1's offline reference study and publication-size review gallery."""
import argparse
import gzip
import hashlib
import html
import json
import os
from pathlib import Path

# Keep Matplotlib state local even in restricted/offline environments.
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from huevat import load_profile, reference, references, to_hex
from huevat._data import load_data
from huevat.evaluation import condition_colors, gray_rgb, quantize, _lab
from huevat.study import build_study, compare_studies, negative_controls


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def style(fig, axes, background):
    fg = "#202020" if background == "#ffffff" else "#eeeeee"
    fig.set_facecolor(background)
    for ax in np.asarray(axes).ravel():
        ax.set_facecolor(background)
        ax.tick_params(colors=fg, labelsize=6)
        for spine in ax.spines.values():
            spine.set_color(fg)
        ax.title.set_color(fg)
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
    return fg


def save(fig, path):
    fig.savefig(path, dpi=300, facecolor=fig.get_facecolor(), metadata={"Software": "Huevat H1 baseline-v1"})
    plt.close(fig)


def categorical_panel(ref, n, background, path):
    profile = load_profile("data-marks", background)
    conditions = profile["conditions"] + ["grayscale"]
    rgb = quantize(ref.colors(n))
    fig, axes = plt.subplots(len(conditions), 5, figsize=(8.0, 7.4), layout="constrained",
                             gridspec_kw={"width_ratios": [1.5, 1, 1, .7, .7]})
    fg = style(fig, axes, profile["background"])
    titles = ["8-bit source selection", "0.75 pt lines", "1.5 pt lines", "3 pt marks", "5 pt marks"]
    for column, title in enumerate(titles):
        axes[0, column].set_title(title, fontsize=7, color=fg)
    x = np.linspace(0, 1, 180)
    for row, condition in enumerate(conditions):
        colors = gray_rgb(rgb) if condition == "grayscale" else condition_colors(rgb, condition)[0]
        for column in range(5):
            ax = axes[row, column]
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            if column == 0:
                ax.set_xlim(0, n)
                ax.set_ylim(0, 1)
                for index, color in enumerate(colors):
                    ax.add_patch(Rectangle((index, .15), 1, .65, color=color, linewidth=0))
                ax.set_ylabel(condition, rotation=0, ha="right", va="center", fontsize=6, color=fg)
            elif column in (1, 2):
                for index, color in enumerate(colors):
                    ax.plot(x, np.sin(2 * np.pi * (x + .12 * index)) + .08 * index,
                            color=color, linewidth=.75 if column == 1 else 1.5)
                ax.set_ylim(-1.1, 1.8)
            else:
                ax.scatter(np.arange(n), np.sin(np.arange(n)), c=colors,
                           s=(3 if column == 3 else 5)**2, edgecolors="none")
                ax.set_xlim(-.5, n - .5)
                ax.set_ylim(-1.5, 1.5)
    fig.suptitle(f"{ref.label} | n={n} | {background} background", fontsize=10, color=fg)
    fig.supxlabel("Matched geometry; Machado display simulation; no automatic human-review pass", fontsize=7, color=fg)
    save(fig, path)


def map_field(rgb, field):
    x = np.linspace(0, 1, len(rgb))
    mapped = np.stack([np.interp(field, x, rgb[:, channel]) for channel in range(3)], axis=-1)
    return np.rint(mapped * 255).astype(np.uint8)


def display_field(rgb, field, condition="normal"):
    pixels = map_field(rgb, field)
    flat = pixels.reshape(-1, 3) / 255
    transformed = gray_rgb(flat) if condition == "grayscale" else condition_colors(flat, condition)[0]
    return np.rint(transformed.reshape(pixels.shape) * 255).astype(np.uint8)


def fields(family):
    x = np.linspace(0, 1, 257)[None, :]
    y = np.linspace(0, 1, 96)[:, None]
    ripple = np.clip(x + .025 * (1 - y) * np.sin(2 * np.pi * 12 * x), 0, 1)
    if family in ("diverging", "spectral"):
        xx, yy = 2*x - 1, 2*y - 1
        signed = xx * np.exp(-2*(xx*xx + yy*yy))
        feature = .5 + .5 * signed / max(abs(signed.min()), abs(signed.max()))
    else:
        feature = np.clip(.15 + .35*x + .45*np.exp(-((x-.35)**2 + (y-.45)**2)/.006)
                          - .12*np.exp(-((x-.7)**2 + (y-.55)**2)/.003), 0, 1)
    return ripple, feature


def ordered_panel(ref, background, path):
    profile = load_profile("filled-fields", background)
    rgb = quantize(ref.sample(257))
    fig = plt.figure(figsize=(8.0, 8.0), layout="constrained")
    grid = fig.add_gridspec(11, 3, width_ratios=[.9, 1.2, 1.2])
    ramps = [fig.add_subplot(grid[i, 0]) for i in range(8)]
    legends = [fig.add_subplot(grid[i, 0]) for i in range(8, 11)]
    panels = [fig.add_subplot(grid[0:4, 1]), fig.add_subplot(grid[0:4, 2]),
              fig.add_subplot(grid[4:8, 1]), fig.add_subplot(grid[4:8, 2]),
              fig.add_subplot(grid[8:11, 1]), fig.add_subplot(grid[8:11, 2])]
    fg = style(fig, ramps + legends + panels, profile["background"])
    for ax, condition in zip(ramps, profile["conditions"]):
        colors, _ = condition_colors(rgb, condition)
        ax.imshow(np.repeat(colors[None, :, :], 8, axis=0), aspect="auto", interpolation="nearest")
        ax.set_title(condition, fontsize=6, color=fg)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax, n in zip(legends, (5, 7, 9)):
        ax.imshow(quantize(ref.colors(n))[None, :, :], aspect="auto", interpolation="nearest")
        ax.set_title(f"{n} bins: " + ("native" if ref.native_tables else "sampled"), fontsize=6, color=fg)
        ax.set_xticks([])
        ax.set_yticks([])
    ripple, feature = fields(ref.family)
    panels[0].imshow(display_field(rgb, ripple), aspect="auto", interpolation="nearest")
    panels[0].set_title("Decreasing-amplitude oscillating ramp", fontsize=7, color=fg)
    panels[1].imshow(display_field(rgb, ripple, "grayscale"), aspect="auto", interpolation="nearest")
    panels[1].set_title("Relative-luminance grayscale", fontsize=7, color=fg)
    panels[2].imshow(display_field(rgb, feature), aspect="auto", interpolation="nearest")
    panels[2].set_title("Signed field; zero at center" if ref.family in ("diverging", "spectral") else "Known Gaussian features", fontsize=7, color=fg)
    panels[3].imshow(display_field(rgb, feature, "deutan-100"), aspect="auto", interpolation="nearest")
    panels[3].set_title("Same field: deutan-100 display", fontsize=7, color=fg)
    for ax in panels[:4]:
        ax.set_xticks([])
        ax.set_yticks([])
    x = np.linspace(0, 1, len(rgb))
    for condition, linestyle in (("normal", "-"), ("protan-100", "--"), ("deutan-100", ":"), ("tritan-100", "-.")):
        colors, _ = condition_colors(rgb, condition)
        lab = _lab(colors)
        panels[4].plot(x, lab[:, 0], linestyle, label=condition, linewidth=.8)
        steps = np.linalg.norm(np.diff(lab, axis=0), axis=1)
        panels[5].plot(x[1:], steps, linestyle, linewidth=.8)
    panels[4].set_title("Oklab lightness", fontsize=7, color=fg)
    panels[5].set_title("Adjacent Oklab step (257 samples)", fontsize=7, color=fg)
    panels[4].legend(fontsize=5, loc="best", facecolor=profile["background"], labelcolor=fg)
    for ax in panels[4:]:
        ax.set_xlabel("Parameter t", fontsize=6)
    fig.suptitle(f"{ref.label} | {background} background | 8-bit study adaptation", fontsize=10, color=fg)
    fig.supxlabel("Native tables retained; encoded-sRGB interpolation is a study adaptation; human review pending", fontsize=7, color=fg)
    save(fig, path)


def controls_panel(background, path):
    profile = load_profile("filled-fields", background)
    controls = negative_controls()
    fig, axes = plt.subplots(6, 2, figsize=(7.2, 7), layout="constrained")
    fg = style(fig, axes, profile["background"])
    for row, (identifier, family, rgb, discrete) in enumerate(controls):
        rgb = quantize(rgb)
        axes[row, 0].imshow(rgb[None, :, :], aspect="auto", interpolation="nearest")
        axes[row, 0].set_title(identifier, fontsize=7, color=fg)
        axes[row, 0].set_xticks([])
        axes[row, 0].set_yticks([])
        axes[row, 1].plot(np.linspace(0, 1, len(rgb)), _lab(rgb)[:, 0], linewidth=.8)
        axes[row, 1].set_title("Oklab lightness" + ("; 129 bins" if discrete else ""), fontsize=7, color=fg)
    fig.suptitle(f"Deliberately defective controls | {background}", fontsize=10, color=fg)
    save(fig, path)


def render(report, output):
    images = output / "images"
    images.mkdir(exist_ok=True)
    for identifier in references():
        ref = reference(identifier)
        for background in ("light", "dark"):
            if ref.family == "categorical":
                for n in (4, 6, 8):
                    categorical_panel(ref, n, background, images / f"{identifier}-{background}-{n}.png")
            else:
                ordered_panel(ref, background, images / f"{identifier}-{background}.png")
    for background in ("light", "dark"):
        controls_panel(background, images / f"controls-{background}.png")
    summary = [{"id": case["id"], "reference": case["reference"], "negative_control": case["negative_control"],
                "profile": case["result"]["profile"], "count": case["result"]["count"],
                "mathematical_pass": case["result"]["mathematical_pass"], "screen_pass": case["result"]["screen_pass"],
                "failures": [{"name": c["name"], "condition": c["condition"], "level": c["level"]}
                             for c in case["result"]["criteria"] if not c["passed"]]}
               for case in report["cases"]]
    write_json(output / "summary.json", {"visual_review": "pending", "cases": summary})
    write_json(output / "corpus.json", load_data("references-v1.json"))
    review = {"status": "pending", "reviewer": None, "date": None,
              "checklist": ["thin lines and small markers", "overlap and legends", "grayscale",
                            "oscillating ramp and known features", "signed zero and arm balance", "light and dark backgrounds"],
              "panels": [{"file": str(p.relative_to(output)).replace('\\', '/'), "status": "pending", "notes": ""}
                         for p in sorted(images.glob("*.png"))]}
    write_json(output / "review.json", review)
    methods = (ROOT / "docs/METHODS_H1.md").read_text(encoding="utf-8")
    methods += f"\n## Baseline execution\n\n{len(references())} references; {len(report['cases'])} explicit evaluation cases.\n"
    methods += "All six deliberate defects fail their screening profiles on both backgrounds.\n"
    methods += "Published-reference failures are retained in summary.json and the full report; thresholds were not adjusted.\n"
    methods += "Runtime versions: " + json.dumps(report["runtime"], sort_keys=True) + ".\n"
    (output / "methods.md").write_text(methods, encoding="utf-8", newline="\n")
    sections = []
    for identifier in references():
        ref = reference(identifier)
        cards = []
        for background in ("light", "dark"):
            if ref.family == "categorical":
                image = f"images/{identifier}-{background}-8.png"
                extra = "".join(f'<details><summary>Matched n={n}</summary><img loading="lazy" src="images/{identifier}-{background}-{n}.png" alt="{identifier}, {background}, n={n}"></details>' for n in (4, 6))
            else:
                image, extra = f"images/{identifier}-{background}.png", ""
            cases = [c for c in summary if c["reference"] == identifier and c["profile"].endswith('/' + background)]
            rows = []
            for case in cases:
                failure_names = sorted({c["name"] + " (" + c["condition"] + ")" for c in case["failures"]})
                rows.append('<tr><td>' + html.escape(case['id']) + '</td><td>' +
                            ('pass' if case['mathematical_pass'] else 'fail') + '</td><td>' +
                            ('pass' if case['screen_pass'] else 'fail') + '</td><td>' +
                            html.escape('; '.join(failure_names) or 'none') + '</td></tr>')
            table = '<details><summary>Individual criteria and failures</summary><div class="scroll"><table><thead><tr><th>Case</th><th>Mathematical</th><th>Screen</th><th>Failed criteria</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div></details>'
            cards.append(f'<article><h3>{background.capitalize()} background</h3><img loading="lazy" src="{image}" alt="{html.escape(ref.label)}, {background} background">{extra}{table}</article>')
        shown = ref.colors(8) if ref.family == "categorical" else (ref.rgb[0], ref.rgb[len(ref.rgb)//2], ref.rgb[-1])
        color_values = ' '.join(map(to_hex, shown))
        sections.append(f'<section id="{identifier}"><h2>{html.escape(ref.label)}</h2><p>{ref.family}; {html.escape(ref.selection)}. <strong>Human review pending.</strong></p><p>8-bit source values (n=8 or endpoint/middle/endpoint): <code>{color_values}</code></p>' + ''.join(cards) + '</section>')
    links = ' | '.join(f'<a href="#{identifier}">{html.escape(reference(identifier).label)}</a>' for identifier in references())
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Huevat H1 reference study</title>
<style>body{font:16px/1.5 system-ui,sans-serif;margin:auto;padding:24px;max-width:1100px;background:#f4f4f4;color:#202020}article{background:white;padding:16px;margin:16px 0;border:1px solid #aaa}img{width:100%;height:auto}table{border-collapse:collapse;font-size:12px}td,th{padding:7px;border:1px solid #aaa;vertical-align:top}summary{cursor:pointer;font-weight:600}.scroll{overflow:auto}section{margin:45px 0}a{color:#175582}</style>
<h1>Huevat H1 reference study</h1><p>Published references under fixed models, thresholds and matched conditions. <strong>No reference is certified as universally accessible or approved as a Huevat default.</strong> All screens retain failures; no combined ranking is used.</p>
<p><a href="summary.json">Summary JSON</a> · <a href="report.json.gz">Full machine report (gzip JSON)</a> · <a href="corpus.json">Exact reference corpus and source provenance</a> · <a href="methods.md">Methods report</a> · <a href="review.json">Pending visual-review checklist</a> · <a href="manifest.json">Artifact hashes</a></p>
<p>Figures are 300-DPI PNGs. Categorical panels show 4/6/8 classes at fixed physical line and marker sizes. Ordered panels use 257 samples. Left-column ramps include all stated CVD severities. Interpolated paths are explicitly labeled study adaptations; native values remain unchanged.</p>
<nav>''' + links + '</nav>' + ''.join(sections)
    page += '<section><h2>Deliberately defective controls</h2><p>Every control must fail; these are tests of the screening code, not references.</p><img src="images/controls-light.png" alt="Defective controls on light background"><img src="images/controls-dark.png" alt="Defective controls on dark background"></section>'
    page += '<footer>Okabe-Ito (2002), reproduced by Wong (2011), attribution corrected 2023. ColorBrewer: Cynthia Brewer, Mark Harrower and Penn State, Apache-2.0. ColorCET: Peter Kovesi / HoloViz, CC-BY-4.0; Glasbey method attributed in ColorCET. viridis/cividis: Matplotlib source tables and retained license. Machado model via colorspacious, MIT. Source versions, hashes and adaptation rules are in the full report and repository notices. This gallery has no external image, script or font dependencies.</footer></html>'
    (output / "index.html").write_text(page, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "research/baseline-v1")
    parser.add_argument("--check", action="store_true", help="Reevaluate, compare numerical results and verify retained asset hashes")
    parser.add_argument("--numeric-only", action="store_true", help="Write report without rendering; use a separate output directory")
    args = parser.parse_args()
    output = args.output.resolve()
    protocol_sha = hashlib.sha256((ROOT / "docs/METHODS_H1.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    report = build_study(protocol_sha)
    controls = [case for case in report["cases"] if case["negative_control"]]
    if not controls or any(case["result"]["screen_pass"] for case in controls):
        raise SystemExit("A deliberately defective control passed unexpectedly")
    if args.check:
        with gzip.open(output / "report.json.gz", "rt", encoding="utf-8") as stream:
            compare_studies(json.load(stream), report)
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        tool_hash = hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if manifest["render_tool_sha256_lf"] != tool_hash:
            raise SystemExit("Gallery tool differs from its recorded version; regenerate intentionally")
        for name, expected in manifest["files"].items():
            if sha(output / name) != expected:
                raise SystemExit(f"Artifact hash mismatch: {name}")
        print(f"Reproduced {len(report['cases'])} study cases within 1e-8 and verified artifact hashes")
        return
    output.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    (output / "report.json.gz").write_bytes(gzip.compress(raw, mtime=0))
    if not args.numeric_only:
        render(report, output)
    write_json(output / "manifest.json", {
        "study_version": report["study_version"], "protocol_sha256": protocol_sha,
        "render_tool_sha256_lf": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "files": {str(p.relative_to(output)).replace('\\', '/'): sha(p)
                  for p in sorted(output.rglob('*')) if p.is_file() and p.name != "manifest.json"},
    })
    print(f"Built {len(report['cases'])} cases ({len(controls)} negative controls) in {output}")


if __name__ == "__main__":
    main()
