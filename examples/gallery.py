"""Draw the README palette galleries from Huevat's shipped colors.

Run ``python examples/gallery.py`` with the matplotlib extra installed.
"""
import argparse
import os
from pathlib import Path

import huevat as hv

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))


def draw(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    height = 0.53 * len(rows) + 0.85
    fig = plt.figure(figsize=(12, height), facecolor="#ffffff")
    for column, background in enumerate(("light", "dark")):
        left = 0.015 + column * 0.5
        bg, fg = ("#ffffff", "#26323c") if background == "light" else ("#121212", "#ececec")
        panel = fig.add_axes((left, 0.02, 0.47, 0.96))
        panel.set_facecolor(bg)
        panel.set_xticks([])
        panel.set_yticks([])
        for spine in panel.spines.values():
            spine.set_visible(False)
        panel.text(0.035, 0.95, background.title() + " background",
                   color=fg, fontsize=13, weight="bold", va="top")
        for index, (label, factory, categorical) in enumerate(rows):
            y = 0.83 - index * (0.80 / len(rows))
            panel.text(0.035, y, label, color=fg, fontsize=10, va="center")
            ax = panel.inset_axes((0.30, y - 0.027, 0.665, 0.054))
            source = factory(background)
            colors = ([hv.from_hex(color) for color in source.colors] if categorical
                      else [source.at(i / 1024) for i in range(1025)])
            ax.imshow([colors], aspect="auto", interpolation="nearest")
            ax.set_axis_off()
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    defaults = [
        (f"Clearer · {n} colors", lambda bg, n=n: hv.categorical(n, background=bg), True)
        for n in (4, 6, 8)
    ]
    defaults.extend(
        (label, lambda bg, factory=factory: factory(background=bg), False)
        for label, factory in (("Sequential", hv.sequential), ("Diverging", hv.diverging),
                               ("Multi-hue", hv.multihue), ("Spectral", hv.spectral))
    )
    named = [(name, lambda bg, name=name: hv.gradient(name, background=bg), False)
             for name in hv.gradient_names()]
    draw(defaults, args.output / "palettes.png")
    draw(named, args.output / "gradients.png")
    print(f"Wrote palette galleries to {args.output}")


if __name__ == "__main__":
    main()
