"""
Build three policy-comparison figures: each panel spans all six strata
(2 permit volumes × 3 staffing levels), with a small subset of levers as grouped boxes.
Uses the same Tukey-style box construction as ``policy_lever_impact_analysis``:
mean of per-run quantiles across Monte Carlo runs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib.pyplot as plt

from repo_paths import RESULTS_DIR
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

MIX_HOMOGENEOUS = "all_custom_non_like_for_like"
MIX_BALANCED = "balanced"

RUN_DIST_COLS = [
    "application_to_ready_run_q1_days",
    "application_to_ready_run_median_days",
    "application_to_ready_run_q3_days",
    "application_to_ready_run_whislo_days",
    "application_to_ready_run_whishi_days",
]


def _mean_box_stats(sub: pd.DataFrame, cols: Sequence[str]) -> dict[str, float]:
    mean_stats = sub[cols].apply(pd.to_numeric, errors="coerce").dropna(how="any").mean(axis=0)
    return {
        "med": float(mean_stats["application_to_ready_run_median_days"]),
        "q1": float(mean_stats["application_to_ready_run_q1_days"]),
        "q3": float(mean_stats["application_to_ready_run_q3_days"]),
        "whislo": float(mean_stats["application_to_ready_run_whislo_days"]),
        "whishi": float(mean_stats["application_to_ready_run_whishi_days"]),
    }


def _stratum_label(num_permits: int, staffing: str) -> str:
    return f"{num_permits:,} permits\n{staffing.capitalize()} staffing"


def _strata_order(df: pd.DataFrame) -> list[tuple[int, str]]:
    permit_levels = sorted(df["num_permits"].unique())
    staffing_levels = ["low", "medium", "high"]
    return [(n, s) for n in permit_levels for s in staffing_levels]


def _mask(
    df: pd.DataFrame,
    *,
    num_permits: int,
    staffing: str,
    sequential: str,
    ai_review: str,
    permit_mix: str,
    pre_apps: Iterable[str],
) -> pd.Series:
    m = (
        (df["num_permits"] == num_permits)
        & (df["staffing_scenario"] == staffing)
        & (df["sequential"] == sequential)
        & (df["ai_review"] == ai_review)
        & (df["pre_application_distribution"].isin(list(pre_apps)))
    )
    if "permit_mix" in df.columns:
        m &= df["permit_mix"].astype(str).eq(permit_mix)
    return m


def _bxp_stat_or_none(df: pd.DataFrame, mask: pd.Series, cols: Sequence[str]) -> dict | None:
    sub = df.loc[mask, list(cols)].apply(pd.to_numeric, errors="coerce").dropna(how="any")
    if sub.empty:
        return None
    ms = _mean_box_stats(sub, cols)
    return {**ms, "fliers": []}


def _draw_strata_grouped_bxp(
    ax: plt.Axes,
    df: pd.DataFrame,
    *,
    strata: Sequence[tuple[int, str]],
    pre_apps: Sequence[str],
    policies: Sequence[tuple[str, str, str, str]],
    colors: Sequence[str],
    ylabel: str,
    box_width: float = 0.68,
    group_gap: float = 0.88,
) -> list[Patch]:
    """
    ``policies`` entries: (sequential, ai_review, permit_mix, legend_label).

    Box centers within each stratum are spaced by ``box_width`` so adjacent boxes
    for the same stratum share an edge (no gap). ``group_gap`` separates strata.
    """
    n_pol = len(policies)
    intra = box_width
    group_stride = n_pol * intra + group_gap
    stats: list[dict] = []
    positions: list[float] = []
    facecolors: list[str] = []

    for j, (nperm, staff) in enumerate(strata):
        base = j * group_stride
        for i, (seq, ai, mix, _lab) in enumerate(policies):
            mask = _mask(
                df,
                num_permits=nperm,
                staffing=staff,
                sequential=seq,
                ai_review=ai,
                permit_mix=mix,
                pre_apps=pre_apps,
            )
            st = _bxp_stat_or_none(df, mask, RUN_DIST_COLS)
            if st is None:
                raise ValueError(
                    f"No per-run rows for stratum permits={nperm}, staffing={staff}, "
                    f"sequential={seq}, ai={ai}, permit_mix={mix}"
                )
            stats.append(st)
            positions.append(base + i * intra)
            facecolors.append(colors[i])

    bp = ax.bxp(
        stats,
        positions=positions,
        widths=box_width,
        patch_artist=True,
        showfliers=False,
        medianprops=dict(color="0.05", linewidth=1.5),
        whiskerprops=dict(color="0.35", linewidth=1.05),
        capprops=dict(color="0.35", linewidth=1.05),
    )
    for patch, fc in zip(bp["boxes"], facecolors):
        patch.set_facecolor(fc)
        patch.set_edgecolor("white")
        patch.set_linewidth(0.85)
        patch.set_alpha(0.92)

    xticks = [j * group_stride + (n_pol - 1) * intra / 2 for j in range(len(strata))]
    ax.set_xticks(xticks)
    ax.set_xticklabels([_stratum_label(n, s) for n, s in strata], fontsize=11)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.grid(axis="y", alpha=0.28, linestyle="-", linewidth=0.55)
    ax.tick_params(axis="y", labelsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    half_w = box_width * 0.5
    side_gap = 0.55
    if positions:
        ax.set_xlim(
            min(positions) - half_w - side_gap,
            max(positions) + half_w + side_gap,
        )

    handles = [
        Patch(facecolor=colors[i], edgecolor="white", linewidth=0.6)
        for i in range(n_pol)
    ]
    return handles


def save_three_stratum_figures(
    df_run: pd.DataFrame,
    results_dir: Path | str = RESULTS_DIR,
    *,
    pre_apps: Sequence[str] | None = None,
) -> list[Path]:
    """
    Write three PNGs under ``results_dir``:
    - ``policy_strata_ai_review_comparison.png``
    - ``policy_strata_process_layout_comparison.png``
    - ``policy_strata_baseline_vs_expedited_mix.png``
    """
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    missing = [c for c in RUN_DIST_COLS if c not in df_run.columns]
    if missing:
        raise ValueError(f"Missing columns in per-run data: {missing}")

    if pre_apps is None:
        pre_apps = sorted(df_run["pre_application_distribution"].unique())
    strata = _strata_order(df_run)

    ylabel = "Permitting time (days)"

    out_paths: list[Path] = []

    def _save_one(
        *,
        policies: Sequence[tuple[str, str, str, str]],
        colors: Sequence[str],
        suptitle: str,
        ncol: int,
        legend_fontsize: int,
        out_name: str,
        figsize: tuple[float, float] = (11.0, 6.9),
    ) -> Path:
        fig, ax = plt.subplots(figsize=figsize)
        # Room for figure title at top and legend below the axes (no overlap).
        fig.subplots_adjust(left=0.10, right=0.98, top=0.82, bottom=0.22)
        handles = _draw_strata_grouped_bxp(
            ax,
            df_run,
            strata=strata,
            pre_apps=pre_apps,
            policies=policies,
            colors=colors,
            ylabel=ylabel,
        )
        title_art = fig.suptitle(suptitle, fontsize=17, fontweight="bold", y=0.97)
        leg = fig.legend(
            handles,
            [p[3] for p in policies],
            title="Scenario",
            loc="lower center",
            bbox_to_anchor=(0.5, 0.02),
            bbox_transform=fig.transFigure,
            ncol=ncol,
            fontsize=legend_fontsize,
            title_fontsize=13,
            frameon=False,
        )
        out_path = results_dir / out_name
        # bbox_inches="tight" often drops suptitle unless included in bbox_extra_artists.
        extra = (leg, title_art) if title_art is not None else (leg,)
        fig.savefig(
            out_path,
            dpi=180,
            bbox_inches="tight",
            bbox_extra_artists=extra,
            pad_inches=0.2,
        )
        plt.close(fig)
        return out_path

    # --- 1) AI review (standard process only, homogeneous mix) ---
    policies_ai = [
        ("standard", "none", MIX_HOMOGENEOUS, "Baseline"),
        ("standard", "initial_check", MIX_HOMOGENEOUS, "Initial AI review"),
        ("standard", "full_review", MIX_HOMOGENEOUS, "Full AI review"),
    ]
    colors_ai = ["#4d4d4d", "#2171b5", "#9ecae1"]
    p1 = _save_one(
        policies=policies_ai,
        colors=colors_ai,
        suptitle="Comparison of AI Review Timeline Impact",
        ncol=3,
        legend_fontsize=12,
        out_name="policy_strata_ai_review_comparison.png",
    )
    out_paths.append(p1)

    # --- 2) Process layout (no AI, homogeneous): left → right = Sequential, Standard, Parallel ---
    policies_proc = [
        ("sequential", "none", MIX_HOMOGENEOUS, "Sequential"),
        ("standard", "none", MIX_HOMOGENEOUS, "Baseline"),
        ("parallel", "none", MIX_HOMOGENEOUS, "Parallel"),
    ]
    colors_proc = ["#238b45", "#4d4d4d", "#74c476"]
    p2 = _save_one(
        policies=policies_proc,
        colors=colors_proc,
        suptitle="Comparison of Process Configuration Timeline Impact",
        ncol=3,
        legend_fontsize=12,
        out_name="policy_strata_process_layout_comparison.png",
    )
    out_paths.append(p2)

    # --- 3) Baseline homogeneous vs balanced (expedited) mix, standard + no AI ---
    if "permit_mix" not in df_run.columns:
        return out_paths

    policies_exp = [
        ("standard", "none", MIX_HOMOGENEOUS, "Baseline"),
        ("standard", "none", MIX_BALANCED, "Expedited permit options (balanced mix)"),
    ]
    colors_exp = ["#4d4d4d", "#fd8d3c"]
    p3 = _save_one(
        policies=policies_exp,
        colors=colors_exp,
        suptitle="Comparison of Expedited Permit Type Timeline Impact",
        ncol=2,
        legend_fontsize=11,
        out_name="policy_strata_baseline_vs_expedited_mix.png",
        figsize=(10.5, 6.9),
    )
    out_paths.append(p3)

    return out_paths
