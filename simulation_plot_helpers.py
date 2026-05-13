"""
Helpers for Monte Carlo visualization.

**Monte Carlo permit plots:** you can either pool **all permit-level observations across
runs** and take one Tukey box (``pooled_tukey_boxplot_stats``), or (for policy levers)
compute a Tukey box per run and **average** those endpoints across runs
(``mean_bxp_stats_across_runs`` — see ``policy_lever_impact_analysis``).

Gantt-style horizontal bars (durations on a timeline) are not statistical summaries and
should stay as ``barh`` — use these helpers only for outcome distributions across runs.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence, TypeVar

import numpy as np

T = TypeVar("T")

# Lazy import for table output (optional dependency in some environments)
_pd = None


def _pandas():
    global _pd
    if _pd is None:
        import pandas as pd

        _pd = pd
    return _pd


def distribution_stats_row(series_name: str, values: Sequence[float]) -> dict[str, Any]:
    """
    Summary statistics for one box-and-whisker series (same quantities as a standard box plot).
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n == 0:
        return {
            "series": series_name,
            "n": 0,
            "mean": np.nan,
            "std": np.nan,
            "min": np.nan,
            "q1": np.nan,
            "median": np.nan,
            "q3": np.nan,
            "max": np.nan,
        }
    return {
        "series": series_name,
        "n": n,
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if n > 1 else 0.0,
        "min": float(np.min(arr)),
        "q1": float(np.quantile(arr, 0.25)),
        "median": float(np.median(arr)),
        "q3": float(np.quantile(arr, 0.75)),
        "max": float(np.max(arr)),
    }


def boxplot_stats_dataframe(
    labeled_series: Sequence[tuple[str, Sequence[float]]],
) -> Any:
    """Build a DataFrame of ``distribution_stats_row`` for each labeled series (drops series with n=0)."""
    pd = _pandas()
    cols = ["series", "n", "mean", "std", "min", "q1", "median", "q3", "max"]
    rows = []
    for lab, vals in labeled_series:
        row = distribution_stats_row(lab, vals)
        if row["n"] > 0:
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows)


def show_boxplot_stats_table(
    labeled_series: Sequence[tuple[str, Sequence[float]]],
    *,
    heading: Optional[str] = None,
) -> Any:
    """
    Display a stats table for the same values shown in box plots (Jupyter ``display`` if available).

    Returns the DataFrame (possibly empty) for assignment or CSV export.
    """
    df = boxplot_stats_dataframe(labeled_series)
    if df.empty:
        if heading:
            print(heading)
        print("(No finite values for boxplot stats table.)")
        return df

    if heading:
        try:
            from IPython.display import Markdown, display

            display(Markdown(f"**{heading}**"))
        except Exception:
            print(heading)

    try:
        from IPython.display import display

        display(df)
    except Exception:
        # noqa: T201 — intentional fallback when IPython is not available
        print(df.to_string(index=False))
    return df


def tukey_boxplot_stats_from_values(
    values: Sequence[float],
    *,
    whis: float = 1.5,
) -> dict[str, float]:
    """
    Tukey box endpoints for one sample (e.g. one run's permit-level durations).

    Uses the same IQR whisker rule as ``policy_lever_impact_analysis`` (1.5×IQR, whiskers
    at the most extreme points inside the fences).
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"q1": float("nan"), "med": float("nan"), "q3": float("nan"), "whislo": float("nan"), "whishi": float("nan")}
    q1 = float(np.percentile(arr, 25))
    med = float(np.median(arr))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1
    lower_bound = q1 - whis * iqr
    upper_bound = q3 + whis * iqr
    whislo = float(arr[arr >= lower_bound].min())
    whishi = float(arr[arr <= upper_bound].max())
    return {"q1": q1, "med": med, "q3": q3, "whislo": whislo, "whishi": whishi}


def mean_bxp_stats_across_runs(
    run_observations: Sequence[Sequence[float]],
    *,
    whis: float = 1.5,
) -> dict[str, float]:
    """
    For each inner sequence (one run's observations), compute Tukey box stats, then take
    the **arithmetic mean** of Q1, median, Q3, and whisker endpoints across runs — matching
    the policy intervention comparison aggregation.

    Returns keys ``q1``, ``med``, ``q3``, ``whislo``, ``whishi``, and ``n_runs`` (number of
    runs that contributed a finite box).
    """
    per_run: list[dict[str, float]] = []
    for vals in run_observations:
        st = tukey_boxplot_stats_from_values(vals, whis=whis)
        if all(np.isfinite(float(st[k])) for k in ("q1", "med", "q3", "whislo", "whishi")):
            per_run.append(st)
    if not per_run:
        return {
            "q1": float("nan"),
            "med": float("nan"),
            "q3": float("nan"),
            "whislo": float("nan"),
            "whishi": float("nan"),
            "n_runs": 0.0,
        }
    keys = ("q1", "med", "q3", "whislo", "whishi")
    out = {k: float(np.nanmean([s[k] for s in per_run])) for k in keys}
    out["n_runs"] = float(len(per_run))
    return out


def pooled_tukey_boxplot_stats(
    run_observations: Sequence[Sequence[float]],
    *,
    whis: float = 1.5,
) -> dict[str, Any]:
    """
    Concatenate all inner sequences (e.g. one list per Monte Carlo run) and compute a
    single Tukey box on the **pooled** sample. Typical size is (runs × permits) when each
    run contributes one value per permit.

    Returns ``q1``, ``med``, ``q3``, ``whislo``, ``whishi`` like ``tukey_boxplot_stats_from_values``,
    plus ``n`` = number of pooled values.
    """
    pooled: list[float] = [float(x) for seq in run_observations for x in seq]
    st = tukey_boxplot_stats_from_values(pooled, whis=whis)
    return {**st, "n": int(len(pooled))}


def aggregate_bxp_stats_dataframe(rows: Sequence[Mapping[str, Any]]) -> Any:
    """DataFrame for tables of Tukey box endpoints (one row per box): ``n`` = pooled count, ``n_runs`` = run count."""
    pd = _pandas()
    cols = ["series", "n", "n_runs", "q1", "median", "q3", "whisker_low", "whisker_high"]
    if not rows:
        return pd.DataFrame(columns=cols)
    norm: list[dict[str, Any]] = []
    for r in rows:
        norm.append(
            {
                "series": r.get("series", ""),
                "n": int(r.get("n", 0)),
                "n_runs": int(r.get("n_runs", 0)),
                "q1": r.get("q1"),
                "median": r.get("median"),
                "q3": r.get("q3"),
                "whisker_low": r.get("whisker_low"),
                "whisker_high": r.get("whisker_high"),
            }
        )
    return pd.DataFrame(norm)


def show_aggregate_bxp_stats_table(
    rows: Sequence[Mapping[str, Any]],
    *,
    heading: Optional[str] = None,
) -> Any:
    """Display a table of Tukey box endpoints (pooled or mean-aggregated)."""
    df = aggregate_bxp_stats_dataframe(list(rows))
    if df.empty:
        if heading:
            print(heading)
        print("(No aggregate box rows to display.)")
        return df
    if heading:
        try:
            from IPython.display import Markdown, display

            display(Markdown(f"**{heading}**"))
        except Exception:
            print(heading)
    try:
        from IPython.display import display

        display(df)
    except Exception:
        print(df.to_string(index=False))
    return df


def permits_partitioned_by_run(
    multi_results: Iterable[Mapping[str, Any]],
    scenario_name: str,
) -> List[List[Any]]:
    """
    From ``run_multiple_simulations`` entries, return ``[permits_run0, permits_run1, ...]``
    for a single scenario name.
    """
    by_run: MutableMapping[int, List[Any]] = {}
    for res in multi_results:
        if res.get("scenario") != scenario_name:
            continue
        idx = int(res.get("run_index", 0))
        by_run[idx] = list(res.get("permits") or [])
    return [by_run[i] for i in sorted(by_run)]


def permits_by_scenario_partitioned_by_run(
    multi_results: Iterable[Mapping[str, Any]],
) -> dict[str, List[List[Any]]]:
    """Partition permits for every scenario name appearing in ``multi_results``."""
    names: set[str] = set()
    for res in multi_results:
        n = res.get("scenario")
        if isinstance(n, str):
            names.add(n)
    return {n: permits_partitioned_by_run(multi_results, n) for n in sorted(names)}


def within_run_median(values: Sequence[float]) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    return float(np.median(arr))


def run_medians_for_segment(
    runs: Sequence[Sequence[Any]],
    *,
    segment: Any,
    value_days_fn,
) -> List[float]:
    """For each run, median of ``value_days_fn(permit)`` over permits in ``segment``."""
    out: List[float] = []
    for run_ps in runs:
        vals = []
        for p in run_ps:
            if getattr(p, "segment", None) != segment:
                continue
            v = value_days_fn(p)
            if v is not None and np.isfinite(v):
                vals.append(float(v))
        m = within_run_median(vals)
        if np.isfinite(m):
            out.append(m)
    return out


def values_are_run_lists(permits_by_process: Mapping[str, Any]) -> bool:
    """True if dict values look like ``list[list[Permit]]`` (non-empty first bucket)."""
    for v in permits_by_process.values():
        if not v:
            continue
        return isinstance(v[0], list)
    return False
