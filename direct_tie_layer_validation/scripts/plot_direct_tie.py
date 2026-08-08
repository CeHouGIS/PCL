#!/usr/bin/env python3
"""Nature-style plot of combined Direct Tie status versus symmetric CI."""

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "direct_tie_layer_validation"
OUTPUT = WORK / "output"
CI_FILE = ROOT / "cultural_validation" / "output" / "city_pair_ci.csv"
HISTORICAL = ROOT / "historical_city_connection_layers_138x138.xlsx"

sys.path.insert(0, str(SCRIPT_DIR))
from calculate_direct_tie_correlation import ALIASES, normalize  # noqa: E402

FONT_DIR = Path("/usr/share/fonts/truetype/liberation2")
font_files = sorted(FONT_DIR.glob("LiberationSans-*.ttf"))
if not font_files:
    raise RuntimeError("Install Liberation Sans: apt install fonts-liberation2")
for path in font_files:
    font_manager.fontManager.addfont(path)

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans"],
    "font.size": 7,
    "font.weight": "bold",
    "axes.labelsize": 8.5,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",
    "axes.linewidth": 0.7,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def draw_boxplot(ax, groups, colors):
    boxes = ax.boxplot(
        groups, positions=[1, 2], widths=0.40, patch_artist=True,
        showfliers=False, whis=(5, 95),
        medianprops={"color": "white", "linewidth": 1.35},
        boxprops={"edgecolor": "#3B4147", "linewidth": 0.8},
        whiskerprops={"color": "#3B4147", "linewidth": 0.75},
        capprops={"color": "#3B4147", "linewidth": 0.75},
    )
    for box, color in zip(boxes["boxes"], colors):
        box.set_facecolor(color)
        box.set_alpha(0.70)


def format_p(value):
    return "$P_{perm}$ < 0.001" if value < 0.001 else f"$P_{{perm}}$ = {value:.3f}"


def add_panel_header(ax, panel, k, p, delta):
    ax.text(-0.13, 1.125, chr(97 + panel), transform=ax.transAxes,
            fontsize=9.2, fontweight="bold", va="bottom", clip_on=False)
    ax.text(0.0, 1.115, f"K = {k}", transform=ax.transAxes,
            fontsize=8.2, fontweight="bold", va="bottom", clip_on=False)
    ax.text(0.0, 1.015, f"{format_p(p)}    $\\Delta$CI = {delta:.4f}",
            transform=ax.transAxes, fontsize=7.0, fontweight="bold",
            color="#4A4F55", va="bottom", clip_on=False)


def main():
    ci = pd.read_csv(CI_FILE)
    city_list = pd.read_excel(HISTORICAL, sheet_name="City List")
    tie = pd.read_excel(HISTORICAL, sheet_name="Direct Tie Matrix", index_col=0)
    results = pd.read_csv(OUTPUT / "direct_tie_correlation_results.csv").set_index("k")
    ci_cities = sorted(set(ci.city_1) | set(ci.city_2))
    normalized_ci = {normalize(city): city for city in ci_cities}
    pairs = []
    for row in city_list.itertuples(index=False):
        ci_city = ALIASES.get(row.city, normalized_ci.get(normalize(row.city)))
        if ci_city is not None:
            pairs.append((row.city, ci_city, row.country))
    if len(pairs) != 130:
        raise RuntimeError(f"Expected 130 matched cities, got {len(pairs)}")
    historical_names = [row[0] for row in pairs]
    hist_to_ci = {row[0]: row[1] for row in pairs}
    tie = tie.loc[historical_names, historical_names]
    tie_lookup = {}
    for i, a in enumerate(historical_names):
        for b in historical_names[i + 1:]:
            tie_lookup[tuple(sorted((hist_to_ci[a], hist_to_ci[b])))] = int(tie.loc[a, b])

    colors = ["#527AA3", "#D76565"]
    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.45), sharex=True, sharey=True)
    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        d = ci[ci.k == k].copy()
        d["direct_tie"] = [
            tie_lookup[tuple(sorted((a, b)))] for a, b in zip(d.city_1, d.city_2)
        ]
        p = results.loc[k, "pearson_city_permutation_p_one_sided"]
        delta = results.loc[k, "mean_difference"]
        groups = [
            d.loc[d.direct_tie == 0, "ci_symmetric"].to_numpy(),
            d.loc[d.direct_tie == 1, "ci_symmetric"].to_numpy(),
        ]
        draw_boxplot(ax, groups, colors)
        add_panel_header(ax, panel, k, p, delta)
        ax.set_xticks([1, 2], ["No combined\ndirect tie", "Combined\ndirect tie"])
        ax.set_xlim(0.52, 2.48)
        ax.set_ylim(0.64, 0.91)
        ax.set_yticks([0.65, 0.75, 0.85])
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#E6E9EC", linewidth=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#30343A")
            ax.spines[side].set_linewidth(0.75)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight("bold")
        if panel == 0:
            ax.set_ylabel("Covered Index")

    fig.subplots_adjust(left=0.080, right=0.99, bottom=0.24, top=0.80, wspace=0.16)
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(OUTPUT / f"direct_tie_vs_ci.{suffix}", dpi=dpi, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
