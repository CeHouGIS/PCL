#!/usr/bin/env python3
"""Create a Nature-style plot of Covered Index versus geographic distance."""

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
DATA_OUTPUT = ROOT / "data" / "results" / "geographic_baseline_validation"
IMAGE_OUTPUT = ROOT / "images" / "geographic_baseline_validation"
CI_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_pair_ci.csv"
CITY_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_country_mapping.csv"
K = 1000

sys.path.insert(0, str(SCRIPT_DIR))
from calculate_geographic_baseline import haversine_matrix, symmetric_ci_matrix  # noqa: E402

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


def format_p(value):
    return "$P$ < 0.001" if value < 0.001 else f"$P$ = {value:.3f}"


def add_statistics(ax, rho, p_value):
    ax.text(0.0, 1.025, f"$r_s$ = {rho:.3f}    {format_p(p_value)}",
            transform=ax.transAxes, fontsize=7.6, fontweight="bold",
            color="#4A4F55", va="bottom", clip_on=False)


def draw_grouped_boxplot(ax, groups, colors):
    positions = np.arange(1, len(groups) + 1)
    boxes = ax.boxplot(
        groups, positions=positions, widths=0.58, patch_artist=True,
        showfliers=False, whis=(5, 95),
        medianprops={"color": "white", "linewidth": 1.25},
        boxprops={"edgecolor": "#3B4147", "linewidth": 0.75},
        whiskerprops={"color": "#3B4147", "linewidth": 0.70},
        capprops={"color": "#3B4147", "linewidth": 0.70},
    )
    for box, color in zip(boxes["boxes"], colors):
        box.set_facecolor(color)
        box.set_alpha(0.78)


def main():
    IMAGE_OUTPUT.mkdir(parents=True, exist_ok=True)
    city_table = pd.read_csv(CITY_FILE)
    ci = pd.read_csv(CI_FILE)
    results = pd.read_csv(DATA_OUTPUT / "geographic_baseline_results.csv").set_index("k")
    cities = city_table.city.tolist()
    upper = np.triu_indices(len(cities), 1)
    distance_km = haversine_matrix(city_table.longitude, city_table.latitude)[upper]
    distance_breaks = [1000, 2500, 5000, 7500, 10000, 15000]
    distance_group = np.digitize(distance_km, distance_breaks)

    fig, ax = plt.subplots(figsize=(3.54, 2.78))
    colors = [
        "#B8C9D8", "#9FB7CB", "#86A5BE", "#6E93B0",
        "#587F9E", "#456D8B", "#335A77",
    ]
    ci_matrix = symmetric_ci_matrix(ci[ci.k == K], cities)
    ci_values = ci_matrix[upper]
    groups = [ci_values[distance_group == group] for group in range(7)]
    draw_grouped_boxplot(ax, groups, colors)

    row = results.loc[K]
    add_statistics(ax, row.spearman_rho, row.spearman_qap_p_one_sided)
    ax.set_xlim(0.48, 7.52)
    ax.set_ylim(0.60, 0.95)
    ax.set_xticks(
        np.arange(1, 8),
        ["<1", "1–\n2.5", "2.5–\n5", "5–\n7.5", "7.5–\n10", "10–\n15", "$\\geq$15"],
    )
    ax.set_yticks([0.60, 0.70, 0.80, 0.90])
    ax.set_xlabel("Geographic distance group ($10^3$ km)")
    ax.set_ylabel("Covered Index")
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color="#E6E9EC", linewidth=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#30343A")
        ax.spines[side].set_linewidth(0.75)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")

    fig.subplots_adjust(left=0.18, right=0.98, bottom=0.25, top=0.88)

    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(
            IMAGE_OUTPUT / f"ci_vs_geographic_distance_nature.{suffix}",
            dpi=dpi, facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
