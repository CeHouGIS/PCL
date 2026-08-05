#!/usr/bin/env python3
"""Plot each additional cultural validation in the main Nature-style layout."""

from pathlib import Path
import json
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_additional_cross_validation import (  # noqa: E402
    EXT, GROUPS, load_profiles, euclidean_distance,
)

for font_file in Path("/usr/share/fonts/truetype/liberation2").glob("LiberationSans-*.ttf"):
    font_manager.fontManager.addfont(font_file)
mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans"],
    "font.size": 7, "font.weight": "bold", "axes.labelsize": 8,
    "axes.labelweight": "bold", "axes.titleweight": "bold",
    "axes.linewidth": .7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})


def external_frame(data, dataset, profiles, cepii):
    d = data[data.same_country == 0].copy()
    if dataset == "CEPII common language":
        lookup = {tuple(sorted((r.iso_o, r.iso_d))): 1 - float(r.comlang_ethno) for r in cepii.itertuples(index=False)}
        keys = [tuple(sorted((a, b))) for a, b in zip(d.iso3_1, d.iso3_2)]
        d["external_distance"] = [lookup.get(k, np.nan) for k in keys]
    else:
        profile = profiles[dataset]
        d = d[d.iso3_1.isin(profile) & d.iso3_2.isin(profile)].copy()
        d["external_distance"] = [euclidean_distance(profile[a], profile[b]) for a, b in zip(d.iso3_1, d.iso3_2)]
    return d.dropna(subset=["external_distance", "ci_symmetric"])


def add_ols(ax, d):
    x = d.external_distance.to_numpy(float)
    y = d.ci_symmetric.to_numpy(float)
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    xx = np.linspace(x.min(), x.max(), 200)
    XX = np.column_stack([np.ones(len(xx)), xx])
    fit = XX @ beta
    resid = y - X @ beta
    cov = (resid @ resid / (len(x) - 2)) * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.einsum("ij,jk,ik->i", XX, cov, XX))
    tcrit = stats.t.ppf(.975, len(x) - 2)
    ax.fill_between(xx, fit - tcrit * se, fit + tcrit * se, color="#C44E52", alpha=.20, linewidth=0, zorder=3)
    ax.plot(xx, fit, color="#C44E52", linewidth=1.3, zorder=4)


def plot_one(dataset, data, results, profiles, cepii):
    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.35), sharex=False, sharey=True)
    cmap = mpl.colormaps["cividis"].copy(); cmap.set_under("white")
    for panel, (ax, k) in enumerate(zip(axes, (200, 500, 1000))):
        d = external_frame(data[data.k == k], dataset, profiles, cepii)
        rho = stats.spearmanr(d.external_distance, d.ci_symmetric).statistic
        row = results[(results.dataset == dataset) & (results.k == k)].iloc[0]
        x = d.external_distance.to_numpy(float)
        xmin, xmax = float(x.min()), float(x.max())
        if np.isclose(xmin, xmax): xmax = xmin + 1
        pad = (xmax - xmin) * .04
        last = ax.hexbin(x, d.ci_symmetric, gridsize=30 if xmax-xmin > .2 else 8,
                         extent=(xmin-pad, xmax+pad, .60, .95), mincnt=1,
                         cmap=cmap, linewidths=0, vmin=1, vmax=60, rasterized=True)
        add_ols(ax, d)
        ax.text(-.14, 1.055, chr(97 + panel), transform=ax.transAxes, fontsize=9,
                fontweight="bold", va="bottom", clip_on=False)
        ax.set_title(f"K = {k}    $r_s$ = {rho:.3f}    $P_{{Holm}}$ = {row.holm_p_across_all_tests:.3f}",
                     loc="left", fontsize=7.2, fontweight="bold", pad=8)
        ax.set_ylim(.60, .95)
        ax.set_yticks([.60, .70, .80, .90])
        ax.set_xlabel("Cultural distance")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        for tick in ax.get_xticklabels() + ax.get_yticklabels(): tick.set_fontweight("bold")
    axes[0].set_ylabel("Morphological similarity (CI)")
    fig.suptitle(dataset, x=.085, ha="left", y=.995, fontsize=9, fontweight="bold")
    fig.subplots_adjust(left=.085, right=.90, bottom=.22, top=.82, wspace=.18)
    cax = fig.add_axes([.92, .25, .012, .55])
    cb = fig.colorbar(last, cax=cax, ticks=[1, 20, 40, 60]); cb.set_label("City-pair count", labelpad=3)
    for tick in cb.ax.get_yticklabels(): tick.set_fontweight("bold")
    slug = dataset.lower().replace(" ", "_")
    for ext, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(OUT / f"additional_{slug}_nature.{ext}", dpi=dpi, facecolor="white")
    plt.close(fig)


def main():
    data = pd.read_csv(OUT / "analysis_dataset_all_pairs.csv")
    profiles = load_profiles()
    cepii = pd.read_stata(ROOT / "external" / "dist_cepii.dta")
    results = pd.read_csv(OUT / "additional_cross_validation_results.csv")
    for dataset in list(GROUPS) + ["CEPII common language"]:
        plot_one(dataset, data, results, profiles, cepii)
    print("Generated Nature-style three-panel figures for", len(list(GROUPS)) + 1, "external criteria")


if __name__ == "__main__":
    main()
