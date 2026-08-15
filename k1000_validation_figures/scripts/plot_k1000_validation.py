#!/usr/bin/env python3
"""Create standalone and combined Nature-style K=1,000 validation figures."""

from pathlib import Path
import json
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "k1000_validation_figures" / "output"
CULTURAL_OUTPUT = ROOT / "cultural_validation" / "output"
DIRECT_OUTPUT = ROOT / "direct_tie_layer_validation" / "output"
REGIME_OUTPUT = ROOT / "shared_regime_validation" / "output"
MORPH_OUTPUT = ROOT / "morphology_concordance_validation" / "output"
CI_FILE = CULTURAL_OUTPUT / "city_pair_ci.csv"
HISTORICAL = ROOT / "historical_city_connection_layers_138x138.xlsx"
K = 1000

sys.path.insert(0, str(ROOT / "direct_tie_layer_validation" / "scripts"))
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
    "axes.linewidth": 0.7,
    "xtick.labelsize": 7.0,
    "ytick.labelsize": 7.2,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.transparent": False,
})


def format_p(value):
    return "$P$ < 0.001" if value < 0.001 else f"$P$ = {value:.3f}"


def save_figure(fig, stem):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(OUTPUT / f"{stem}.{suffix}", dpi=dpi, facecolor="white")
    plt.close(fig)


def cultural_distance_figure():
    data = pd.read_csv(CULTURAL_OUTPUT / "analysis_dataset_all_pairs.csv")
    with open(CULTURAL_OUTPUT / "validation_results.json", encoding="utf-8") as stream:
        validation = json.load(stream)
    frame = data[(data.k == K) & (data.same_country == 0)].dropna(
        subset=["ci_symmetric", "cultdist", "dist"]
    )
    p_value = validation["scales"][str(K)]["country_label_permutation_p"]

    fig, ax = plt.subplots(figsize=(3.54, 2.78))
    cmap = mpl.colormaps["cividis"].copy()
    cmap.set_under("white")
    density = ax.hexbin(
        frame.cultdist,
        frame.ci_symmetric,
        gridsize=31,
        extent=(0.28, 0.42, 0.60, 0.95),
        mincnt=1,
        cmap=cmap,
        linewidths=0,
        vmin=1,
        vmax=60,
        rasterized=True,
    )

    x = frame.cultdist.to_numpy(dtype=float)
    y = frame.ci_symmetric.to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    x_grid = np.linspace(x.min(), x.max(), 200)
    grid_design = np.column_stack([np.ones(len(x_grid)), x_grid])
    y_fit = grid_design @ beta
    residual = y - design @ beta
    r_squared = 1.0 - (residual @ residual) / np.sum((y - y.mean()) ** 2)
    sigma_squared = residual @ residual / (len(x) - design.shape[1])
    covariance = sigma_squared * np.linalg.inv(design.T @ design)
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

    ax.text(
        0.0,
        1.075,
        f"$R^2$ = {r_squared:.3f}    {format_p(p_value)}",
        transform=ax.transAxes,
        fontsize=7.6,
        fontweight="bold",
        color="#30343A",
        va="bottom",
        clip_on=False,
    )
    ax.set_xlim(0.28, 0.42)
    ax.set_ylim(0.60, 0.95)
    ax.set_xticks([0.28, 0.32, 0.36, 0.40])
    ax.set_yticks([0.60, 0.70, 0.80, 0.90])
    ax.set_xlabel("Cultural distance")
    ax.set_ylabel("Covered Index")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")

    fig.subplots_adjust(left=0.18, right=0.86, bottom=0.19, top=0.86)
    color_axis = fig.add_axes([0.89, 0.20, 0.025, 0.65])
    colorbar = fig.colorbar(density, cax=color_axis, ticks=[1, 20, 40, 60])
    colorbar.set_label("City-pair count", labelpad=3, fontweight="bold")
    colorbar.ax.tick_params(labelsize=6.8, width=0.55, length=2.3)
    for label in colorbar.ax.get_yticklabels():
        label.set_fontweight("bold")
    colorbar.outline.set_linewidth(0.6)
    save_figure(fig, "ci_vs_cultural_distance_nature_k1000")


def historical_status_lookup(ci_cities, sheet_name):
    city_list = pd.read_excel(HISTORICAL, sheet_name="City List")
    matrix = pd.read_excel(HISTORICAL, sheet_name=sheet_name, index_col=0)
    normalized_ci = {normalize(city): city for city in ci_cities}
    matched = []
    for row in city_list.itertuples(index=False):
        ci_city = ALIASES.get(row.city, normalized_ci.get(normalize(row.city)))
        if ci_city is not None:
            matched.append((row.city, ci_city))
    if len(matched) != 130:
        raise RuntimeError(f"Expected 130 matched cities for {sheet_name}, got {len(matched)}")
    historical_names = [historical for historical, _ in matched]
    historical_to_ci = dict(matched)
    matrix = matrix.loc[historical_names, historical_names]
    lookup = {}
    for index, city_a in enumerate(historical_names):
        for city_b in historical_names[index + 1:]:
            ci_pair = tuple(sorted((historical_to_ci[city_a], historical_to_ci[city_b])))
            lookup[ci_pair] = int(matrix.loc[city_a, city_b])
    return lookup


def binary_groups(frame, lookup):
    status = np.asarray(
        [lookup[tuple(sorted((a, b)))] for a, b in zip(frame.city_1, frame.city_2)],
        dtype=int,
    )
    values = frame.ci_symmetric.to_numpy(dtype=float)
    return [values[status == 0], values[status == 1]]


def morphology_groups(frame):
    pairs = pd.read_csv(MORPH_OUTPUT / "moco_morphology_similarity_pairs.csv")
    lookup = {}
    for row in frame.itertuples(index=False):
        lookup[(row.city_1, row.city_2)] = row.ci_symmetric
        lookup[(row.city_2, row.city_1)] = row.ci_symmetric
    values = np.asarray(
        [lookup[(a, b)] for a, b in zip(pairs.city_1, pairs.city_2)], dtype=float
    )
    quintile = pairs.primary_similarity_quintile.to_numpy(dtype=int)
    return [values[quintile == group] for group in range(1, 6)]


def morphology_r_squared(frame):
    pairs = pd.read_csv(MORPH_OUTPUT / "moco_morphology_similarity_pairs.csv")
    lookup = {}
    for row in frame.itertuples(index=False):
        lookup[(row.city_1, row.city_2)] = row.ci_symmetric
        lookup[(row.city_2, row.city_1)] = row.ci_symmetric
    ci_values = np.asarray(
        [lookup[(a, b)] for a, b in zip(pairs.city_1, pairs.city_2)], dtype=float
    )
    correlation = stats.pearsonr(
        pairs.self_similarity.to_numpy(dtype=float), ci_values
    ).statistic
    return float(correlation ** 2)


def draw_boxplot(ax, groups, colors, positions):
    boxes = ax.boxplot(
        groups,
        positions=positions,
        widths=0.50,
        patch_artist=True,
        showfliers=False,
        whis=(5, 95),
        medianprops={"color": "white", "linewidth": 1.30},
        boxprops={"edgecolor": "#3B4147", "linewidth": 0.78},
        whiskerprops={"color": "#3B4147", "linewidth": 0.72},
        capprops={"color": "#3B4147", "linewidth": 0.72},
    )
    for box, color in zip(boxes["boxes"], colors):
        box.set_facecolor(color)
        box.set_alpha(0.78)


def style_box_axis(ax):
    ax.set_ylim(0.63, 0.92)
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


def panel_header(ax, panel, title, statistics):
    ax.text(
        -0.13,
        1.13,
        panel,
        transform=ax.transAxes,
        fontsize=9.2,
        fontweight="bold",
        va="bottom",
        clip_on=False,
    )
    ax.text(
        0.0,
        1.12,
        title,
        transform=ax.transAxes,
        fontsize=7.8,
        fontweight="bold",
        va="bottom",
        clip_on=False,
    )
    ax.text(
        0.0,
        1.02,
        statistics,
        transform=ax.transAxes,
        fontsize=6.6,
        fontweight="bold",
        color="#4A4F55",
        va="bottom",
        clip_on=False,
    )


def combined_figure():
    ci = pd.read_csv(CI_FILE)
    frame = ci[ci.k == K].copy()
    ci_cities = sorted(set(ci.city_1) | set(ci.city_2))
    direct_lookup = historical_status_lookup(ci_cities, "Direct Tie Matrix")
    direct_results = pd.read_csv(
        DIRECT_OUTPUT / "direct_tie_correlation_results.csv"
    ).set_index("k").loc[K]
    morphology_results = pd.read_csv(
        MORPH_OUTPUT / "morphology_concordance_results.csv"
    )
    morphology_result = morphology_results[
        morphology_results.primary_strategy.astype(bool)
        & (morphology_results.k == K)
    ].iloc[0]

    fig, axes = plt.subplots(1, 2, figsize=(7.09, 3.10), sharey=True)
    binary_colors = ["#527AA3", "#D76565"]
    sequential_colors = ["#C8D8E5", "#A5C0D3", "#7FA7C1", "#578BAA", "#2F6E91"]

    direct = binary_groups(frame, direct_lookup)
    draw_boxplot(axes[0], direct, binary_colors, [1, 2])
    axes[0].set_xlim(0.52, 2.48)
    axes[0].set_xticks([1, 2], ["No direct\ntie", "Direct\ntie"])
    panel_header(
        axes[0],
        "a",
        "Direct inter-city tie",
        f"{format_p(direct_results.pearson_city_permutation_p_one_sided)}"
        f"    $\\Delta$CI = {direct_results.mean_difference:.3f}",
    )

    morphology = morphology_groups(frame)
    morphology_r2 = morphology_r_squared(frame)
    draw_boxplot(axes[1], morphology, sequential_colors, np.arange(1, 6))
    axes[1].set_xlim(0.52, 5.48)
    axes[1].set_xticks(
        np.arange(1, 6), ["Q1\nLow", "Q2", "Q3", "Q4", "Q5\nHigh"]
    )
    panel_header(
        axes[1],
        "b",
        "Morphological concordance",
        f"$R^2$ = {morphology_r2:.3f}    "
        f"{format_p(morphology_result.spearman_qap_p_one_sided)}",
    )

    for ax in axes:
        style_box_axis(ax)
        ax.set_box_aspect(0.68)
    axes[0].set_ylabel("Covered Index")
    fig.subplots_adjust(left=0.080, right=0.99, bottom=0.20, top=0.80, wspace=0.22)
    save_figure(fig, "combined_validation_k1000")


def four_panel_figure():
    """Combine all four external CI validations in a single 2 x 2 figure."""
    cultural_data = pd.read_csv(CULTURAL_OUTPUT / "analysis_dataset_all_pairs.csv")
    with open(CULTURAL_OUTPUT / "validation_results.json", encoding="utf-8") as stream:
        cultural_validation = json.load(stream)
    cultural_frame = cultural_data[
        (cultural_data.k == K) & (cultural_data.same_country == 0)
    ].dropna(subset=["ci_symmetric", "cultdist", "dist"])
    cultural_rho = stats.spearmanr(
        cultural_frame.cultdist, cultural_frame.ci_symmetric
    ).statistic
    cultural_p = cultural_validation["scales"][str(K)][
        "country_label_permutation_p"
    ]

    ci = pd.read_csv(CI_FILE)
    frame = ci[ci.k == K].copy()
    ci_cities = sorted(set(ci.city_1) | set(ci.city_2))
    direct_lookup = historical_status_lookup(ci_cities, "Direct Tie Matrix")
    regime_lookup = historical_status_lookup(ci_cities, "Shared Regime Matrix")
    direct_results = pd.read_csv(
        DIRECT_OUTPUT / "direct_tie_correlation_results.csv"
    ).set_index("k").loc[K]
    regime_results = pd.read_csv(
        REGIME_OUTPUT / "shared_regime_correlation_results.csv"
    ).set_index("k").loc[K]
    morphology_results = pd.read_csv(
        MORPH_OUTPUT / "morphology_concordance_results.csv"
    )
    morphology_result = morphology_results[
        morphology_results.primary_strategy.astype(bool)
        & (morphology_results.k == K)
    ].iloc[0]

    # Keep each panel close to the aspect ratio of the original standalone
    # figures. A taller canvas prevents the 2 x 2 layout from flattening the
    # axes and visually stretching the plotted elements.
    fig, axes = plt.subplots(2, 2, figsize=(7.09, 6.10), sharey=True)
    ax_a, ax_b, ax_c, ax_d = axes.flat
    binary_colors = ["#527AA3", "#D76565"]
    sequential_colors = [
        "#C8D8E5", "#A5C0D3", "#7FA7C1", "#578BAA", "#2F6E91"
    ]

    # a, Cultural-distance validation.
    cmap = mpl.colormaps["cividis"].copy()
    cmap.set_under("white")
    density = ax_a.hexbin(
        cultural_frame.cultdist,
        cultural_frame.ci_symmetric,
        gridsize=31,
        extent=(0.28, 0.42, 0.60, 0.95),
        mincnt=1,
        cmap=cmap,
        linewidths=0,
        vmin=1,
        vmax=60,
        rasterized=True,
    )
    x = cultural_frame.cultdist.to_numpy(dtype=float)
    y = cultural_frame.ci_symmetric.to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    x_grid = np.linspace(x.min(), x.max(), 200)
    grid_design = np.column_stack([np.ones(len(x_grid)), x_grid])
    y_fit = grid_design @ beta
    residual = y - design @ beta
    sigma_squared = residual @ residual / (len(x) - design.shape[1])
    covariance = sigma_squared * np.linalg.inv(design.T @ design)
    mean_se = np.sqrt(
        np.einsum("ij,jk,ik->i", grid_design, covariance, grid_design)
    )
    critical = stats.t.ppf(0.975, df=len(x) - design.shape[1])
    ax_a.fill_between(
        x_grid,
        y_fit - critical * mean_se,
        y_fit + critical * mean_se,
        color="#C44E52",
        alpha=0.20,
        linewidth=0,
        zorder=3,
    )
    ax_a.plot(x_grid, y_fit, color="#C44E52", linewidth=1.3, zorder=4)
    ax_a.set_xlim(0.28, 0.42)
    ax_a.set_xticks([0.28, 0.32, 0.36, 0.40])
    ax_a.set_xlabel("Cultural distance")
    panel_header(
        ax_a,
        "a",
        "Cultural proximity",
        f"$r_s$ = {cultural_rho:.3f}    {format_p(cultural_p)}",
    )
    color_axis = ax_a.inset_axes([1.025, 0.08, 0.030, 0.76])
    colorbar = fig.colorbar(density, cax=color_axis, ticks=[1, 20, 40, 60])
    colorbar.set_label("City-pair count", labelpad=2, fontsize=6.6, fontweight="bold")
    colorbar.ax.tick_params(labelsize=6.2, width=0.5, length=2)
    for label in colorbar.ax.get_yticklabels():
        label.set_fontweight("bold")
    colorbar.outline.set_linewidth(0.55)

    # b, Direct historical ties.
    direct = binary_groups(frame, direct_lookup)
    draw_boxplot(ax_b, direct, binary_colors, [1, 2])
    ax_b.set_xlim(0.52, 2.48)
    ax_b.set_xticks([1, 2], ["No direct\ntie", "Direct\ntie"])
    panel_header(
        ax_b,
        "b",
        "Direct historical tie",
        f"{format_p(direct_results.pearson_city_permutation_p_one_sided)}"
        f"    $\\Delta$CI = {direct_results.mean_difference:.3f}",
    )

    # c, Shared historical regimes.
    regime = binary_groups(frame, regime_lookup)
    draw_boxplot(ax_c, regime, binary_colors, [1, 2])
    ax_c.set_xlim(0.52, 2.48)
    ax_c.set_xticks([1, 2], ["No shared\nregime", "Shared\nregime"])
    panel_header(
        ax_c,
        "c",
        "Shared historical regime",
        f"{format_p(regime_results.pearson_city_permutation_p_one_sided)}"
        f"    $\\Delta$CI = {regime_results.mean_difference:.3f}",
    )

    # d, Morphology-based concordance.
    morphology = morphology_groups(frame)
    draw_boxplot(ax_d, morphology, sequential_colors, np.arange(1, 6))
    ax_d.set_xlim(0.52, 5.48)
    ax_d.set_xticks(
        np.arange(1, 6), ["Q1\nLow", "Q2", "Q3", "Q4", "Q5\nHigh"]
    )
    panel_header(
        ax_d,
        "d",
        "Morphological concordance",
        f"$r_s$ = {morphology_result.spearman_rho:.3f}    "
        f"{format_p(morphology_result.spearman_qap_p_one_sided)}",
    )

    for ax in axes.flat:
        style_box_axis(ax)
        ax.set_box_aspect(0.76)
        ax.set_ylim(0.60, 0.95)
        ax.set_yticks([0.60, 0.70, 0.80, 0.90])
    ax_a.set_ylabel("Covered Index")
    ax_c.set_ylabel("Covered Index")
    fig.text(
        0.985,
        0.975,
        "K = 1,000",
        ha="right",
        va="top",
        fontsize=7.8,
        fontweight="bold",
        color="#30343A",
    )
    fig.subplots_adjust(
        left=0.085,
        right=0.985,
        bottom=0.085,
        top=0.925,
        hspace=0.40,
        wspace=0.34,
    )
    save_figure(fig, "combined_external_validation_k1000")


def main():
    cultural_distance_figure()
    combined_figure()
    four_panel_figure()


if __name__ == "__main__":
    main()
