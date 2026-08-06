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
    "axes.labelsize": 8,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",
    "axes.linewidth": 0.7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def draw_distribution(ax, groups, colors):
    violin = ax.violinplot(
        groups, positions=[1, 2], widths=0.72,
        showmeans=False, showmedians=False, showextrema=False,
        bw_method=0.25,
    )
    for body, color in zip(violin["bodies"], colors):
        body.set_facecolor(color)
        body.set_edgecolor(color)
        body.set_alpha(0.68)
        body.set_linewidth(0.7)
    ax.boxplot(
        groups, positions=[1, 2], widths=0.22, patch_artist=True,
        showfliers=False, whis=(5, 95),
        medianprops={"color": "white", "linewidth": 1.2},
        boxprops={"facecolor": "#333333", "edgecolor": "#333333", "linewidth": 0.7},
        whiskerprops={"color": "#333333", "linewidth": 0.7},
        capprops={"color": "#333333", "linewidth": 0.7},
    )
    ax.scatter(
        [1, 2], [group.mean() for group in groups], marker="D", s=11,
        facecolor="white", edgecolor="#111111", linewidth=0.6, zorder=4,
    )


def format_p(value):
    return "$P_{perm}$ < 0.001" if value < 0.001 else f"$P_{{perm}}$ = {value:.3f}"


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
    ci_country = {row[1]: row[2] for row in pairs}
    tie = tie.loc[historical_names, historical_names]
    tie_lookup = {}
    for i, a in enumerate(historical_names):
        for b in historical_names[i + 1:]:
            tie_lookup[tuple(sorted((hist_to_ci[a], hist_to_ci[b])))] = int(tie.loc[a, b])

    colors = ["#4C78A8", "#E45756"]
    fig, axes = plt.subplots(2, 3, figsize=(7.09, 4.35), sharex=True, sharey=True)
    panel = 0
    for row_index, subset_name in enumerate(("All city pairs", "Cross-country pairs")):
        for col_index, k in enumerate((200, 500, 1000)):
            ax = axes[row_index, col_index]
            d = ci[ci.k == k].copy()
            d["direct_tie"] = [
                tie_lookup[tuple(sorted((a, b)))] for a, b in zip(d.city_1, d.city_2)
            ]
            if row_index == 1:
                d = d[[ci_country[a] != ci_country[b] for a, b in zip(d.city_1, d.city_2)]]
                p = results.loc[k, "cross_country_pearson_city_permutation_p_one_sided"]
                delta = results.loc[k, "cross_country_mean_difference"]
            else:
                p = results.loc[k, "pearson_city_permutation_p_one_sided"]
                delta = results.loc[k, "mean_difference"]
            groups = [
                d.loc[d.direct_tie == 0, "ci_symmetric"].to_numpy(),
                d.loc[d.direct_tie == 1, "ci_symmetric"].to_numpy(),
            ]
            draw_distribution(ax, groups, colors)
            ax.text(-0.13, 1.055, chr(97 + panel), transform=ax.transAxes,
                    fontsize=9, fontweight="bold", va="bottom", clip_on=False)
            ax.set_title(
                f"K = {k}    {format_p(p)}    $\\Delta$CI = {delta:.4f}",
                loc="left", fontsize=7.1, pad=7,
            )
            ax.set_xticks([1, 2], ["No combined\ndirect tie", "Combined\ndirect tie"])
            ax.set_xlim(0.52, 2.48)
            ax.set_ylim(0.55, 0.97)
            ax.set_yticks([0.60, 0.70, 0.80, 0.90])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontweight("bold")
            if col_index == 0:
                ax.set_ylabel(f"{subset_name}\nMorphological similarity (CI)")
            panel += 1

    fig.subplots_adjust(left=0.105, right=0.99, bottom=0.14, top=0.93, hspace=0.38, wspace=0.18)
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(OUTPUT / f"direct_tie_vs_ci.{suffix}", dpi=dpi, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
