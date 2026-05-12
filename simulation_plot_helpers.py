"""
Helpers for Monte Carlo visualization: within-run aggregates, then boxplots across runs.

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
