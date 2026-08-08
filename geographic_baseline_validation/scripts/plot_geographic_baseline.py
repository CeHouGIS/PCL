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


def main():
    city_table = pd.read_csv(CITY_FILE)
    ci = pd.read_csv(CI_FILE)
    results = pd.read_csv(OUTPUT / "geographic_baseline_results.csv").set_index("k")
    cities = city_table.city.tolist()
    upper = np.triu_indices(len(cities), 1)
    distance_km = haversine_matrix(city_table.longitude, city_table.latitude)[upper]
    log10_distance = np.log10(distance_km)

    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.45), sharex=True, sharey=True)
    cmap = mpl.colormaps["cividis"].copy()
    cmap.set_under("white")
    last = None
    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        ci_matrix = symmetric_ci_matrix(ci[ci.k == k], cities)
        ci_values = ci_matrix[upper]
        last = ax.hexbin(
            log10_distance, ci_values, gridsize=34,
            extent=(1.45, 4.35, 0.60, 0.95), mincnt=1,
            cmap=cmap, linewidths=0, vmin=1, vmax=75, rasterized=True,
        )
        design = np.column_stack([np.ones(len(log10_distance)), log10_distance])
        beta = np.linalg.lstsq(design, ci_values, rcond=None)[0]
        x_grid = np.linspace(log10_distance.min(), log10_distance.max(), 200)
        ax.plot(x_grid, beta[0] + beta[1] * x_grid,
                color="#C44E52", linewidth=1.35, zorder=4)

        row = results.loc[k]
        add_panel_header(
            ax, panel, k, row.spearman_rho, row.spearman_qap_p_one_sided
        )
        ax.set_xlim(1.45, 4.35)
        ax.set_ylim(0.60, 0.95)
        ax.set_xticks([2, 3, 4], ["100", "1,000", "10,000"])
        ax.set_yticks([0.60, 0.70, 0.80, 0.90])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#30343A")
            ax.spines[side].set_linewidth(0.75)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight("bold")
        if panel == 0:
            ax.set_ylabel("Covered Index")

    fig.supxlabel("Geographic distance (km; log scale)",
                  x=0.495, y=0.035, fontsize=8.5, fontweight="bold")
    fig.subplots_adjust(left=0.080, right=0.91, bottom=0.20, top=0.80, wspace=0.16)
    color_axis = fig.add_axes([0.93, 0.20, 0.012, 0.60])
    colorbar = fig.colorbar(last, cax=color_axis, ticks=[1, 25, 50, 75])
    colorbar.set_label("City-pair count", labelpad=3)
    colorbar.ax.yaxis.label.set_fontweight("bold")
    for label in colorbar.ax.get_yticklabels():
        label.set_fontweight("bold")
    colorbar.outline.set_linewidth(0.6)

    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(
            OUTPUT / f"ci_vs_geographic_distance_nature.{suffix}",
            dpi=dpi, facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
