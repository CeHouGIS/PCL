#!/usr/bin/env python3
"""Create a compact Nature-style figure for the cultural validation."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7,
    "axes.labelsize": 8,
    "axes.linewidth": 0.7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.transparent": False,
})


def main():
    data = pd.read_csv(OUT / "analysis_dataset_all_pairs.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.35), sharex=True, sharey=True)
    cmap = mpl.colormaps["cividis"].copy()
    cmap.set_under("white")
    last = None

    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        d = data[(data.k == k) & (data.same_country == 0)].dropna(
            subset=["ci_symmetric", "cultdist", "dist"]
        )
        rho, _ = stats.spearmanr(d.cultdist, d.ci_symmetric)
        last = ax.hexbin(
            d.cultdist,
            d.ci_symmetric,
            gridsize=31,
            extent=(0.28, 0.42, 0.60, 0.95),
            mincnt=1,
            cmap=cmap,
            linewidths=0,
            vmin=1,
            vmax=60,
            rasterized=True,
        )

        # Display binned means and 95% confidence intervals to show the trend
        # without treating every dyad as statistically independent.
        edges = np.quantile(d.cultdist, np.linspace(0, 1, 9))
        edges = np.unique(edges)
        mids, means, cis = [], [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            subset = d[(d.cultdist >= lo) & (d.cultdist <= hi)].ci_symmetric
            if len(subset) < 2:
                continue
            mids.append((lo + hi) / 2)
            means.append(subset.mean())
            cis.append(1.96 * subset.std(ddof=1) / np.sqrt(len(subset)))
        ax.errorbar(
            mids,
            means,
            yerr=cis,
            color="#C44E52",
            marker="o",
            markersize=2.8,
            markeredgewidth=0,
            linewidth=1.0,
            capsize=1.5,
            zorder=4,
        )

        ax.text(-0.14, 1.04, chr(97 + panel), transform=ax.transAxes,
                fontsize=9, fontweight="bold", va="bottom")
        ax.text(0.04, 0.95, f"K = {k}", transform=ax.transAxes,
                fontsize=8, fontweight="bold", va="top")
        ax.text(0.04, 0.84, f"Spearman $r_s$ = {rho:.3f}\n$n$ = {len(d):,} pairs",
                transform=ax.transAxes, fontsize=7, va="top", linespacing=1.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlim(0.28, 0.42)
        ax.set_ylim(0.60, 0.95)
        ax.set_xticks([0.28, 0.32, 0.36, 0.40])
        ax.set_yticks([0.60, 0.70, 0.80, 0.90])
        ax.set_xlabel("Cultural distance")

    axes[0].set_ylabel("Morphological similarity (CI)")
    fig.subplots_adjust(left=0.085, right=0.92, bottom=0.22, top=0.94, wspace=0.14)
    cax = fig.add_axes([0.94, 0.25, 0.012, 0.62])
    cb = fig.colorbar(last, cax=cax, ticks=[1, 20, 40, 60])
    cb.set_label("City-pair count", labelpad=3)
    cb.outline.set_linewidth(0.6)

    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(
            OUT / f"ci_vs_cultural_distance_nature.{suffix}",
            dpi=dpi,
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
