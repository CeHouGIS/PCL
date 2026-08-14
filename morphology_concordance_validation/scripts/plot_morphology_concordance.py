#!/usr/bin/env python3
"""Nature-style quintile boxplots for internal morphology concordance."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "morphology_concordance_validation"
OUTPUT = WORK / "output"
CI_FILE = ROOT / "cultural_validation" / "output" / "city_pair_ci.csv"

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
    "xtick.labelsize": 7.0,
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


def draw_boxplot(ax, groups, colors):
    boxes = ax.boxplot(
        groups,
        positions=np.arange(1, 6),
        widths=0.54,
        patch_artist=True,
        showfliers=False,
        whis=(5, 95),
        medianprops={"color": "white", "linewidth": 1.25},
        boxprops={"edgecolor": "#3B4147", "linewidth": 0.75},
        whiskerprops={"color": "#3B4147", "linewidth": 0.70},
        capprops={"color": "#3B4147", "linewidth": 0.70},
    )
    for box, color in zip(boxes["boxes"], colors):
        box.set_facecolor(color)
        box.set_alpha(0.80)


def add_panel_header(ax, panel, k, rho, p_value, delta):
    ax.text(
        -0.13,
        1.125,
        chr(97 + panel),
        transform=ax.transAxes,
        fontsize=9.2,
        fontweight="bold",
        va="bottom",
        clip_on=False,
    )
    ax.text(
        0.0,
        1.115,
        f"K = {k}",
        transform=ax.transAxes,
        fontsize=8.2,
        fontweight="bold",
        va="bottom",
        clip_on=False,
    )
    ax.text(
        0.0,
        1.015,
        f"$r_s$ = {rho:.3f}    {format_p(p_value)}    $\\Delta$CI = {delta:.3f}",
        transform=ax.transAxes,
        fontsize=6.6,
        fontweight="bold",
        color="#4A4F55",
        va="bottom",
        clip_on=False,
    )


def aligned_ci_values(frame, pair_table):
    lookup = {}
    for row in frame.itertuples(index=False):
        lookup[(row.city_1, row.city_2)] = row.ci_symmetric
        lookup[(row.city_2, row.city_1)] = row.ci_symmetric
    return np.asarray(
        [lookup[(a, b)] for a, b in zip(pair_table.city_1, pair_table.city_2)],
        dtype=float,
    )


def main():
    ci = pd.read_csv(CI_FILE)
    pairs = pd.read_csv(OUTPUT / "moco_morphology_similarity_pairs.csv")
    results = pd.read_csv(OUTPUT / "morphology_concordance_results.csv")
    primary = results[results.primary_strategy.astype(bool)].set_index("k")
    quintile = pairs.primary_similarity_quintile.to_numpy(dtype=int)

    colors = ["#C8D8E5", "#A5C0D3", "#7FA7C1", "#578BAA", "#2F6E91"]
    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.45), sharex=True, sharey=True)
    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        values = aligned_ci_values(ci[ci.k == k], pairs)
        groups = [values[quintile == group] for group in range(1, 6)]
        draw_boxplot(ax, groups, colors)
        row = primary.loc[k]
        add_panel_header(
            ax,
            panel,
            k,
            row.spearman_rho,
            row.spearman_qap_p_one_sided,
            row.mean_ci_q5_minus_q1,
        )
        ax.set_xlim(0.52, 5.48)
        ax.set_ylim(0.63, 0.92)
        ax.set_xticks(
            np.arange(1, 6),
            ["Q1\nLowest", "Q2", "Q3", "Q4", "Q5\nHighest"],
        )
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

    fig.supxlabel(
        "Self-contrast MoCo morphology similarity quintile",
        x=0.50,
        y=0.030,
        fontsize=8.5,
        fontweight="bold",
    )
    fig.subplots_adjust(left=0.080, right=0.99, bottom=0.26, top=0.80, wspace=0.16)
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(
            OUTPUT / f"morphology_similarity_vs_ci.{suffix}",
            dpi=dpi,
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
