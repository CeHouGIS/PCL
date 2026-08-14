#!/usr/bin/env python3
"""Plot K=1,000 diagnostics and controlled MRQAP results in Nature style."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "dyadic_dependence_validation" / "output"
PAIR_FILE = OUTPUT / "dyadic_pair_audit_table.csv"
K = 1000

FONT_DIR = Path("/usr/share/fonts/truetype/liberation2")
font_files = sorted(FONT_DIR.glob("LiberationSans-*.ttf"))
if not font_files:
    raise RuntimeError("Install Liberation Sans: apt install fonts-liberation2")
for font_path in font_files:
    font_manager.fontManager.addfont(font_path)

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans"],
    "font.size": 7.2,
    "font.weight": "bold",
    "axes.labelsize": 8.3,
    "axes.labelweight": "bold",
    "axes.linewidth": 0.75,
    "xtick.labelsize": 7.0,
    "ytick.labelsize": 7.0,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


BLUE = "#456F91"
LIGHT_BLUE = "#AFC5D6"
GOLD = "#D8A343"
SLATE = "#657786"
INK = "#30343A"
GRID = "#E4E8EB"


def p_text(value, label="P_{\mathrm{perm}}"):
    if value < 0.001:
        return f"${label}<0.001$"
    return f"${label}={value:.3f}$"


def style_axis(ax, grid=True):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK)
        ax.spines[side].set_linewidth(0.75)
    ax.tick_params(colors=INK)
    if grid:
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, linewidth=0.48)
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontweight("bold")


def panel_label(ax, label):
    ax.text(
        -0.13, 1.06, label, transform=ax.transAxes,
        fontsize=10.2, fontweight="bold", va="bottom", clip_on=False,
    )


def draw_boxplot(ax, groups, positions, colors, widths=0.58):
    artists = ax.boxplot(
        groups,
        positions=positions,
        widths=widths,
        patch_artist=True,
        showfliers=False,
        whis=(5, 95),
        medianprops={"color": "white", "linewidth": 1.35},
        boxprops={"edgecolor": INK, "linewidth": 0.75},
        whiskerprops={"color": INK, "linewidth": 0.70},
        capprops={"color": INK, "linewidth": 0.70},
    )
    for box, color in zip(artists["boxes"], colors):
        box.set_facecolor(color)
        box.set_alpha(0.88)


def main():
    pairs = pd.read_csv(PAIR_FILE)
    diagnostics = pd.read_csv(
        OUTPUT / "dependence_diagnostics_results.csv"
    ).set_index("k").loc[K]
    fixed_effects = pd.read_csv(
        OUTPUT / "shared_city_fixed_effects_results.csv"
    )
    fixed_effects = fixed_effects[fixed_effects.k == K].set_index("model")
    controlled = pd.read_csv(
        OUTPUT / "controlled_historical_mrqap_results.csv"
    )
    controlled = controlled[controlled.k == K].set_index("historical_predictor")

    ci = pairs[f"ci_symmetric_k{K}"].to_numpy()
    distance_breaks = [1000, 2500, 5000, 7500, 10000, 15000]
    distance_group = np.digitize(pairs.distance_km.to_numpy(), distance_breaks)

    fig, axes = plt.subplots(2, 2, figsize=(7.09, 5.0))
    ax_a, ax_b, ax_c, ax_d = axes.flat

    # a, Geographic dependence.
    distance_colors = [
        "#C5D4DF", "#AEC4D4", "#95B3C8", "#7DA2BB",
        "#668FAB", "#517C9A", "#3E6886",
    ]
    distance_groups = [ci[distance_group == group] for group in range(7)]
    draw_boxplot(ax_a, distance_groups, np.arange(1, 8), distance_colors, 0.56)
    ax_a.set_xticks(
        np.arange(1, 8),
        ["<1", "1–\n2.5", "2.5–\n5", "5–\n7.5", "7.5–\n10", "10–\n15", "$\\geq$15"],
    )
    ax_a.set_xlabel("Geographic distance ($10^3$ km)")
    ax_a.set_ylabel("Covered Index")
    ax_a.set_ylim(0.60, 0.95)
    ax_a.set_yticks([0.60, 0.70, 0.80, 0.90])
    ax_a.text(
        0.02, 0.96,
        f"$r_s={diagnostics.spearman_ci_vs_log_distance:.3f}$; "
        + p_text(diagnostics.geographic_qap_p_one_sided),
        transform=ax_a.transAxes, ha="left", va="top", color=INK,
    )
    panel_label(ax_a, "a")
    style_axis(ax_a)

    # b, Same-country dependence.
    same_country = pairs.same_country.to_numpy(dtype=bool)
    draw_boxplot(
        ax_b,
        [ci[~same_country], ci[same_country]],
        [1, 2],
        [LIGHT_BLUE, GOLD],
        0.55,
    )
    ax_b.set_xticks([1, 2], ["Cross-country", "Same-country"])
    ax_b.set_ylabel("Covered Index")
    ax_b.set_ylim(0.60, 0.95)
    ax_b.set_yticks([0.60, 0.70, 0.80, 0.90])
    ax_b.text(
        0.02, 0.96,
        f"$\\Delta\\mathrm{{CI}}={diagnostics.same_country_mean_difference:.3f}$; "
        + p_text(diagnostics.same_country_qap_p_one_sided),
        transform=ax_b.transAxes, ha="left", va="top", color=INK,
    )
    panel_label(ax_b, "b")
    style_axis(ax_b)

    # c, Shared-city dependence in asymmetric CI.
    fe_models = ["source_city", "target_city", "source_and_target_city"]
    fe_values = fixed_effects.loc[fe_models, "r_squared"].to_numpy()
    x_positions = np.arange(3)
    bars = ax_c.bar(
        x_positions,
        fe_values,
        width=0.62,
        color=["#91ADBF", "#658BA4", BLUE],
        edgecolor=INK,
        linewidth=0.75,
        zorder=3,
    )
    for bar, value in zip(bars, fe_values):
        ax_c.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.018,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            color=INK,
        )
    ax_c.set_xticks(x_positions, ["Source city", "Target city", "Source +\ntarget city"])
    ax_c.set_ylabel("Explained variance ($R^2$)")
    ax_c.set_ylim(0, 0.56)
    ax_c.set_yticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
    panel_label(ax_c, "c")
    style_axis(ax_c)

    # d, Historical associations after geographic and national controls.
    predictors = ["direct_tie", "shared_regime"]
    beta_values = controlled.loc[predictors, "standardized_beta"].to_numpy()
    p_values = controlled.loc[predictors, "mrqap_p_one_sided"].to_numpy()
    bars = ax_d.bar(
        [0, 1],
        beta_values,
        width=0.56,
        color=[SLATE, GOLD],
        edgecolor=INK,
        linewidth=0.75,
        zorder=3,
    )
    for bar, value, p_value in zip(bars, beta_values, p_values):
        ax_d.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.004,
            f"$\\beta={value:.3f}$\n" + p_text(p_value, "P_{\\mathrm{MRQAP}}"),
            ha="center",
            va="bottom",
            linespacing=1.15,
            color=INK,
        )
    ax_d.axhline(0, color=INK, linewidth=0.75)
    ax_d.set_xticks([0, 1], ["Direct tie", "Shared regime"])
    ax_d.set_ylabel("Standardized coefficient")
    ax_d.set_ylim(0, 0.102)
    ax_d.set_yticks([0, 0.02, 0.04, 0.06, 0.08, 0.10])
    panel_label(ax_d, "d")
    style_axis(ax_d)

    fig.subplots_adjust(
        left=0.085, right=0.985, bottom=0.105, top=0.955,
        hspace=0.47, wspace=0.30,
    )
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(
            OUTPUT / f"dyadic_dependence_diagnostics_k1000.{suffix}",
            dpi=dpi,
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
