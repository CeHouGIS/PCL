#!/usr/bin/env python3
"""Plot CI distributions by verified direct historical-tie status."""

from pathlib import Path
import re
import unicodedata

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "historical_ties_validation"
OUTPUT = WORK / "output"
CI_FILE = ROOT / "cultural_validation" / "output" / "city_pair_ci.csv"
HISTORICAL_FILE = ROOT / "historical_city_direct_ties_138x138.xlsx"

ALIASES = {
    "Beira": "Beria", "Brasília": "Brazilia", "City of Tshwane": "Tshwane",
    "Havana": "Habana", "Lisbon": "Lisboa", "Malacca": "Melaka",
    "Mexico City": "Mexico", "Milan": "Milano", "NCT of Delhi": "Delhi",
    "Nairobi": "Narobi", "New York City": "Newyork", "Quebec City": "Quebec",
    "Quezon City": "LungsodQuezon", "Saint Petersburg": "St.Petersburg",
    "Setúbal": "Setobal", "Seville": "Sevilla", "São Paulo": "SanPaulo",
    "The Hague": "Denhaag", "Turin": "Torino",
}

FONT_DIR = Path("/usr/share/fonts/truetype/liberation2")
font_files = sorted(FONT_DIR.glob("LiberationSans-*.ttf"))
if not font_files:
    raise RuntimeError("Install Liberation Sans first: apt install fonts-liberation2")
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


def main():
    ci = pd.read_csv(CI_FILE)
    city_list = pd.read_excel(HISTORICAL_FILE, sheet_name="City List")
    ci_cities = sorted(set(ci.city_1) | set(ci.city_2))
    normalize = lambda s: re.sub(
        r"[^a-z0-9]", "",
        unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower(),
    )
    normalized_ci = {normalize(name): name for name in ci_cities}
    pairs = []
    for name in city_list.city:
        ci_name = ALIASES.get(name, normalized_ci.get(normalize(name)))
        if ci_name is not None:
            pairs.append((name, ci_name))
    historical_names = [pair[0] for pair in pairs]
    ci_names = [pair[1] for pair in pairs]
    if len(ci_names) != 130 or len(set(ci_names)) != 130:
        raise RuntimeError("Expected 130 one-to-one historical/CI city matches")
    hist_to_ci = dict(zip(historical_names, ci_names))
    tie = pd.read_excel(HISTORICAL_FILE, sheet_name="Binary Matrix", index_col=0)
    tie = tie.loc[historical_names, historical_names]

    tie_lookup = {}
    for i, a in enumerate(historical_names):
        for b in historical_names[i + 1:]:
            key = tuple(sorted((hist_to_ci[a], hist_to_ci[b])))
            tie_lookup[key] = int(tie.loc[a, b])

    results = pd.read_csv(OUTPUT / "correlation_results.csv").set_index("k")
    colors = ["#4C78A8", "#E45756"]
    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.45), sharey=True)

    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        d = ci[ci.k == k].copy()
        d["direct_tie"] = [
            tie_lookup[tuple(sorted((a, b)))]
            for a, b in zip(d.city_1, d.city_2)
        ]
        groups = [
            d.loc[d.direct_tie == 0, "ci_symmetric"].to_numpy(),
            d.loc[d.direct_tie == 1, "ci_symmetric"].to_numpy(),
        ]

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

        box = ax.boxplot(
            groups, positions=[1, 2], widths=0.22, patch_artist=True,
            showfliers=False, whis=(5, 95),
            medianprops={"color": "white", "linewidth": 1.2},
            boxprops={"facecolor": "#333333", "edgecolor": "#333333", "linewidth": 0.7},
            whiskerprops={"color": "#333333", "linewidth": 0.7},
            capprops={"color": "#333333", "linewidth": 0.7},
        )
        ax.scatter(
            [1, 2], [g.mean() for g in groups], marker="D", s=11,
            facecolor="white", edgecolor="#111111", linewidth=0.6, zorder=4,
        )

        p = results.loc[k, "pearson_city_permutation_p_one_sided"]
        delta = results.loc[k, "mean_difference"]
        ax.text(-0.13, 1.055, chr(97 + panel), transform=ax.transAxes,
                fontsize=9, fontweight="bold", va="bottom", clip_on=False)
        ax.set_title(
            f"K = {k}    $P_{{perm}}$ = {p:.3f}    $\\Delta$CI = {delta:.4f}",
            loc="left", fontsize=7.3, pad=8,
        )
        ax.set_xticks([1, 2], ["No verified\ndirect tie", "Verified\ndirect tie"])
        ax.set_xlim(0.52, 2.48)
        ax.set_ylim(0.55, 0.97)
        ax.set_yticks([0.60, 0.70, 0.80, 0.90])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for tick_label in ax.get_xticklabels() + ax.get_yticklabels():
            tick_label.set_fontweight("bold")

    axes[0].set_ylabel("Morphological similarity (CI)")
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.24, top=0.87, wspace=0.18)
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(OUTPUT / f"historical_direct_ties_vs_ci.{suffix}", dpi=dpi, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
