#!/usr/bin/env python3
"""Create a Nature-style plot of Covered Index versus geographic distance."""

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.ticker import MultipleLocator


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "geographic_baseline_validation" / "output"
CI_FILE = ROOT / "cultural_validation" / "output" / "city_pair_ci.csv"
CITY_FILE = ROOT / "cultural_validation" / "output" / "city_country_mapping.csv"

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
    return "$P_{QAP}$ < 0.001" if value < 0.001 else f"$P_{{QAP}}$ = {value:.3f}"


def add_panel_header(ax, panel, k, rho, p_value):
    ax.text(-0.13, 1.125, chr(97 + panel), transform=ax.transAxes,
            fontsize=9.2, fontweight="bold", va="bottom", clip_on=False)
    ax.text(0.0, 1.115, f"K = {k}", transform=ax.transAxes,
            fontsize=8.2, fontweight="bold", va="bottom", clip_on=False)
    ax.text(0.0, 1.015, f"$r_s$ = {rho:.3f}    {format_p(p_value)}",
            transform=ax.transAxes, fontsize=7.0, fontweight="bold",
            color="#4A4F55", va="bottom", clip_on=False)


def draw_grouped_boxplot(ax, groups, colors):
    boxes = ax.boxplot(
        groups, positions=[1, 2, 3, 4], widths=0.52, patch_artist=True,
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
    city_table = pd.read_csv(CITY_FILE)
    ci = pd.read_csv(CI_FILE)
    results = pd.read_csv(OUTPUT / "geographic_baseline_results.csv").set_index("k")
    cities = city_table.city.tolist()
    upper = np.triu_indices(len(cities), 1)
    distance_km = haversine_matrix(city_table.longitude, city_table.latitude)[upper]
    distance_group = np.digitize(distance_km, [1000, 5000, 10000])

    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.45), sharex=True, sharey=True)
    colors = ["#9DB5CA", "#7899B5", "#577E9E", "#365F7D"]
    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        ci_matrix = symmetric_ci_matrix(ci[ci.k == k], cities)
        ci_values = ci_matrix[upper]
        groups = [ci_values[distance_group == group] for group in range(4)]
        draw_grouped_boxplot(ax, groups, colors)

        row = results.loc[k]
        add_panel_header(
            ax, panel, k, row.spearman_rho, row.spearman_qap_p_one_sided
        )
        ax.set_xlim(0.52, 4.48)
        ax.set_ylim(0.60, 0.95)
        ax.set_xticks(
            [1, 2, 3, 4],
            ["<1,000", "1,000–\n5,000", "5,000–\n10,000", "$\\geq$10,000"],
        )
        ax.set_yticks([0.60, 0.70, 0.80, 0.90])
        ax.yaxis.set_minor_locator(MultipleLocator(0.025))
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, which="major", color="#DCE1E5", linewidth=0.48)
        ax.yaxis.grid(True, which="minor", color="#EEF0F2", linewidth=0.34)
        ax.xaxis.grid(True, which="major", color="#F0F2F4", linewidth=0.32)
        ax.tick_params(axis="y", which="minor", length=1.8, width=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#30343A")
            ax.spines[side].set_linewidth(0.75)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight("bold")
        if panel == 0:
            ax.set_ylabel("Covered Index")

    fig.supxlabel("Geographic distance group (km)",
                  x=0.495, y=0.035, fontsize=8.5, fontweight="bold")
    fig.subplots_adjust(left=0.080, right=0.99, bottom=0.25, top=0.80, wspace=0.16)

    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(
            OUTPUT / f"ci_vs_geographic_distance_nature.{suffix}",
            dpi=dpi, facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
