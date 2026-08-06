#!/usr/bin/env python3
"""Create a compact Nature-style figure for the cultural validation."""

from pathlib import Path
import json

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"

# Register the open, Arial-compatible font explicitly. Matplotlib can retain a
# stale system-font cache in containers, so relying on family-name discovery is
# not sufficiently reproducible for publication output.
LIBERATION_DIR = Path("/usr/share/fonts/truetype/liberation2")
liberation_fonts = sorted(LIBERATION_DIR.glob("LiberationSans-*.ttf"))
if not liberation_fonts:
    raise RuntimeError("Liberation Sans is required (Debian/Ubuntu: apt install fonts-liberation2).")
for font_file in liberation_fonts:
    font_manager.fontManager.addfont(font_file)

mpl.rcParams.update({
    "font.family": "sans-serif",
    # Liberation Sans is metrically compatible with Arial and is available
    # under an open font licence, making it a reproducible journal-safe proxy.
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
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.transparent": False,
})


def main():
    data = pd.read_csv(OUT / "analysis_dataset_all_pairs.csv")
    with open(OUT / "validation_results.json", encoding="utf-8") as stream:
        validation = json.load(stream)
    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.35), sharex=True, sharey=True)
    cmap = mpl.colormaps["cividis"].copy()
    cmap.set_under("white")
    last = None

    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        d = data[(data.k == k) & (data.same_country == 0)].dropna(
            subset=["ci_symmetric", "cultdist", "dist"]
        )
        rho, _ = stats.spearmanr(d.cultdist, d.ci_symmetric)
        perm_p = validation["scales"][str(k)]["country_label_permutation_p"]
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

        # Straight ordinary-least-squares trend with a 95% confidence band for
        # the fitted mean. Dependence-aware inference is reported separately
        # in the panel header using the country-label permutation P value.
        x = d.cultdist.to_numpy(dtype=float)
        y = d.ci_symmetric.to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(x)), x])
        beta = np.linalg.lstsq(design, y, rcond=None)[0]
        x_grid = np.linspace(x.min(), x.max(), 200)
        grid_design = np.column_stack([np.ones(len(x_grid)), x_grid])
        y_fit = grid_design @ beta
        residual = y - design @ beta
        sigma2 = residual @ residual / (len(x) - design.shape[1])
        covariance = sigma2 * np.linalg.inv(design.T @ design)
        mean_se = np.sqrt(np.einsum("ij,jk,ik->i", grid_design, covariance, grid_design))
        critical = stats.t.ppf(0.975, df=len(x) - design.shape[1])
        ax.fill_between(
            x_grid,
            y_fit - critical * mean_se,
            y_fit + critical * mean_se,
            color="#C44E52",
            alpha=0.20,
            linewidth=0,
            zorder=3,
        )
        ax.plot(x_grid, y_fit, color="#C44E52", linewidth=1.3, zorder=4)

        # Keep every annotation outside the plotting field so no observation
        # is obscured. This header remains legible after double-column scaling.
        ax.text(-0.14, 1.055, chr(97 + panel), transform=ax.transAxes,
                fontsize=9, fontweight="bold", va="bottom", clip_on=False)
        ax.set_title(
            f"K = {k}    $r_s$ = {rho:.3f}    $P$ = {perm_p:.3f}",
            loc="left", fontsize=7.5, fontweight="bold", pad=8,
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlim(0.28, 0.42)
        ax.set_ylim(0.60, 0.95)
        ax.set_xticks([0.28, 0.32, 0.36, 0.40])
        ax.set_yticks([0.60, 0.70, 0.80, 0.90])
        ax.set_xlabel("Cultural distance")
        for tick in ax.get_xticklabels() + ax.get_yticklabels():
            tick.set_fontweight("bold")

    axes[0].set_ylabel("Covered Index")
    fig.subplots_adjust(left=0.085, right=0.92, bottom=0.22, top=0.88, wspace=0.14)
    cax = fig.add_axes([0.94, 0.25, 0.012, 0.62])
    cb = fig.colorbar(last, cax=cax, ticks=[1, 20, 40, 60])
    cb.set_label("City-pair count", labelpad=3)
    cb.ax.yaxis.label.set_fontweight("bold")
    for tick in cb.ax.get_yticklabels():
        tick.set_fontweight("bold")
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
