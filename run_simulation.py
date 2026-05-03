"""
Main script to run the permit simulation and display results.
"""

import simpy
from permit_simulation import PermitSimulation
import json
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from typing import Any, Literal, Optional


def _env_clock(env) -> float:
    """Current simulation time. SimPy 4+ uses `env.now` (float); avoid `env.now()`."""
    t = env.now
    if callable(t):
        return float(t())
    return float(t)


def run_simulation(
    num_permits: int = 100,
    simulation_duration: float = None,
    random_seed: int = 42,
    sequential: str = "standard",
    ai_review: str = "none",
    permit_mix: Literal["all_custom_non_like_for_like", "la", "balanced"] = "la",
    pct_pre_approved: float | None = None,
    pct_custom: float | None = None,
    pct_self_cert: float | None = None,
    pct_like_for_like: float | None = None,
    review_duration_families: dict[str, str] | None = None,
    review_duration_multipliers: dict[str, float] | None = None,
    pre_application_distribution: str = "baseline",
    planning_staff_count: int = 25,
    planning_caseload_per_staff: float = 7,
    public_works_staff_count: int = 35,
    public_works_caseload_per_staff: float = 7,
    fire_staff_count: int = 10,
    fire_caseload_per_staff: float = 7,
):
    """
    Run the permit simulation.
    
    Args:
        num_permits: Number of permits to simulate (if simulation_duration is None)
        simulation_duration: Maximum simulation time in days (if None, runs until all permits complete)
        random_seed: Random seed for reproducibility
        sequential: Processing mode: \"standard\", \"parallel\", or \"sequential\".
        permit_mix: Preset permit mix. One of:
            all_custom_non_like_for_like, la, balanced.
        pct_pre_approved: Optional manual override for pre-approved plan share (0–1).
        pct_custom: Optional manual override for custom plan share (0–1).
        pct_self_cert: Optional manual override for self-certification share (0–1).
        pct_like_for_like: Optional manual override for like-for-like share (0–1).
        review_duration_families: Optional map for review stages (planning/public_works/fire)
            to sampling family (normal/lognormal/triangular/uniform).
        review_duration_multipliers: Optional map of duration multipliers by stage.
            Keys can include planning/public_works/fire/special_zoning/agency_referral.
        pre_application_distribution: Distribution choice for pre-application duration.
            Supported values: baseline, lognormal_180, lognormal_60, poisson_10.
        planning_staff_count: Planning staff headcount.
        planning_caseload_per_staff: Average concurrent planning caseload per staff.
        public_works_staff_count: Public works staff headcount.
        public_works_caseload_per_staff: Average concurrent public works caseload per
            staff.
        fire_staff_count: Fire review staff headcount.
        fire_caseload_per_staff: Average concurrent fire caseload per staff.
    """
    env = simpy.Environment()
    sim = PermitSimulation(
        env,
        random_seed=random_seed,
        ai_review=ai_review,
        permit_mix=permit_mix,
        pct_pre_approved=pct_pre_approved,
        pct_custom=pct_custom,
        pct_self_cert=pct_self_cert,
        pct_like_for_like=pct_like_for_like,
        review_duration_families=review_duration_families,
        review_duration_multipliers=review_duration_multipliers,
        pre_application_distribution=pre_application_distribution,
        planning_staff_count=planning_staff_count,
        planning_caseload_per_staff=planning_caseload_per_staff,
        public_works_staff_count=public_works_staff_count,
        public_works_caseload_per_staff=public_works_caseload_per_staff,
        fire_staff_count=fire_staff_count,
        fire_caseload_per_staff=fire_caseload_per_staff,
    )
    
    def permit_generator():
        """Generate permits at specified intervals."""
        count = 0
        while True:
            if simulation_duration is None:
                if count >= num_permits:
                    break
            else:
                if env.now >= simulation_duration:
                    break
            
            permit = sim.create_permit()
            # Use sequential or parallel processing based on parameter
            if sequential == "standard":
                env.process(sim.permit_process(permit))
            elif sequential == "parallel":
                env.process(sim.permit_process_parallel(permit))
            elif sequential == "sequential":
                env.process(sim.permit_process_sequential(permit))
            else:
                raise ValueError(f"Invalid sequential processing type: {sequential}")
            count += 1
            
            # Permits arrive immediately (no delay).
            yield env.timeout(0)
    
    # Start generating permits
    env.process(permit_generator())
    
    # Run simulation
    if simulation_duration is not None:
        env.run(until=simulation_duration)
    else:
        # Run until all permits are completed (with a timeout)
        max_time = 5000  # days (safety limit)
        env.run(until=max_time)
    
    return sim


def run_multiple_simulations(
    n_runs: int,
    num_permits: int = 100,
    simulation_duration: float | None = None,
    base_seed: int = 42,
    scenario_params_list: list[dict] | None = None,
    collect_permits: bool = False,
    collect_average_staff_utilization: bool = False,
    utilization_step: float = 0.05,
):
    """
    Run the simulation many times, optionally for multiple scenarios.

    Args:
        n_runs: Number of repetitions per scenario.
        num_permits: Number of permits per run (if simulation_duration is None).
        simulation_duration: Max simulation time in days (optional).
        base_seed: Base random seed; each run uses base_seed + run_index.
        scenario_params_list: List of dicts, each describing a scenario.
            Each dict can contain:
              - "name": scenario name (string, for labeling)
              - any extra keyword args for run_simulation
                (e.g. "sequential", "ai_review", pct_* parameters).
        collect_permits: If True, also return completed permits for each run.
        collect_average_staff_utilization: If True, also return the mean
            planning / public works / fire utilization time series across runs
            (one series per scenario group; see Returns).
        utilization_step: Day spacing when sampling utilization (smaller = finer).

    Example scenario list:
        [
            {"name": "standard_default", "sequential": "standard"},
            {"name": "parallel_default", "sequential": "parallel"},
            {
                "name": "balanced_segments",
                "sequential": "standard",
                "permit_mix": "balanced",
            },
        ]

    Returns:
        If collect_average_staff_utilization is False:
          List of result dicts, each with:
            {
              "run_index": int,
              "seed": int,
              "scenario": str,
              "params": dict,    # params passed into run_simulation
              "stats": dict,     # sim.get_statistics() output
              "permits": list,   # ONLY present if collect_permits=True;
                                 # list of completed Permit objects for this run
            }
        If collect_average_staff_utilization is True:
          Tuple (results, average_staff_utilization_by_scenario) where
          average_staff_utilization_by_scenario maps scenario name -> dict:
            {
              "days": list[float],
              "planning": list[float],
              "public_works": list[float],
              "fire": list[float],
              "n_runs": int,
              "max_day": int,
            }
    """
    if scenario_params_list is None:
        scenario_params_list = [{"name": "default"}]

    util_sims_by_scenario: dict[str, list[PermitSimulation]] = {}

    results: list[dict] = []
    for run_index in range(n_runs):
        seed = base_seed + run_index
        for scenario in scenario_params_list:
            scenario_name = scenario.get("name", f"scenario_{len(results)}")
            params = {k: v for k, v in scenario.items() if k != "name"}

            sim = run_simulation(
                num_permits=num_permits,
                simulation_duration=simulation_duration,
                random_seed=seed,
                **params,
            )
            stats = sim.get_statistics()
            entry: dict = {
                "run_index": run_index,
                "seed": seed,
                "scenario": scenario_name,
                "params": params,
                "stats": stats,
            }
            if collect_permits:
                entry["permits"] = list(sim.completed_permits)
            results.append(entry)
            if collect_average_staff_utilization:
                util_sims_by_scenario.setdefault(scenario_name, []).append(sim)

    if collect_average_staff_utilization:
        average_staff_utilization_by_scenario: dict[str, dict[str, Any]] = {}
        for scenario_name, sims in util_sims_by_scenario.items():
            if not sims:
                continue
            max_day = max(int(_env_clock(s.env)) for s in sims)
            series_list = [
                s.get_staff_utilization_over_time(days=max_day, step=utilization_step) for s in sims
            ]
            days = series_list[0]["days"]
            planning = np.mean([u["planning"] for u in series_list], axis=0)
            public_works = np.mean([u["public_works"] for u in series_list], axis=0)
            fire = np.mean([u["fire"] for u in series_list], axis=0)
            average_staff_utilization_by_scenario[scenario_name] = {
                "days": days,
                "planning": planning.tolist(),
                "public_works": public_works.tolist(),
                "fire": fire.tolist(),
                "n_runs": len(sims),
                "max_day": max_day,
            }
        return results, average_staff_utilization_by_scenario

    return results


def plot_staff_utilization_series(
    util: dict[str, Any],
    *,
    as_percent: bool = True,
    title: str = "Mean staff utilization over time (multi-run average)",
    xlim: Optional[tuple[float, float]] = None,
    ylim: Optional[tuple[float, float]] = None,
) -> None:
    """Plot planning / fire / public works utilization from a util dict (e.g. multi-run mean)."""
    title_fontsize = 18
    label_fontsize = 16
    tick_fontsize = 14
    legend_fontsize = 14

    days = util["days"]
    months = [d / 30.0 for d in days]
    scale = 100.0 if as_percent else 1.0
    ylabel = "Utilization (%)" if as_percent else "Utilization (load / capacity)"
    ymax = 105.0 if as_percent else 1.05
    plt.figure(figsize=(12, 6))
    plt.plot(months, [v * scale for v in util["planning"]], label="Planning", linewidth=2)
    plt.plot(months, [v * scale for v in util["fire"]], label="Fire", linewidth=2)
    plt.plot(months, [v * scale for v in util["public_works"]], label="Public Works", linewidth=2)
    if ylim is None:
        plt.ylim(0, ymax)
    else:
        plt.ylim(*ylim)
    if xlim is None:
        plt.xlim(0, max(months) if months else 0)
    else:
        # Backward-compatible: if caller passes day-scale limits, convert to months.
        x0, x1 = xlim
        if x1 > 120:  # heuristic: old day-scale limits are typically much larger.
            x0, x1 = x0 / 30.0, x1 / 30.0
        plt.xlim(x0, x1)
    plt.xlabel("Time since disaster (months)", fontsize=label_fontsize)
    plt.ylabel(ylabel, fontsize=label_fontsize)
    plt.title(title, fontsize=title_fontsize)
    plt.xticks(fontsize=tick_fontsize)
    plt.yticks(fontsize=tick_fontsize)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=legend_fontsize)
    plt.tight_layout()
    plt.show()


def plot_staff_utilization(
    sim: PermitSimulation,
    days: float,
    step: float = 1.0,
    as_percent: bool = True,
    xlim: Optional[tuple[float, float]] = None,
    ylim: Optional[tuple[float, float]] = None,
) -> None:
    """Plot planning, fire, and public works utilization for a single completed simulation."""
    u = sim.get_staff_utilization_over_time(days=days, step=step)
    plot_staff_utilization_series(u, as_percent=as_percent, title="Staff utilization over time", xlim=xlim, ylim=ylim)


def print_statistics(stats: dict):
    """Print simulation statistics in a readable format."""
    print("\n" + "="*80)
    print("SIMULATION STATISTICS")
    print("="*80)
    
    if "message" in stats:
        print(stats["message"])
        return
    
    print(f"\nTotal Completed Permits: {stats['total_completed']}")
    print(f"Total In Progress: {stats['total_in_progress']}")
    
    print("\n" + "-"*80)
    print("SEGMENT DISTRIBUTION")
    print("-"*80)
    total = sum(stats['segment_distribution'].values())
    for segment, count in sorted(stats['segment_distribution'].items()):
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {segment:30s}: {count:4d} ({percentage:5.2f}%)")
    
    print("\n" + "-"*80)
    print("OVERALL PROCESSING TIME STATISTICS")
    print("-"*80)
    if stats['average_total_time']:
        at = stats['average_total_time']
        print(f"  Mean:   {at['mean']:8.2f} days")
        print(f"  Median: {at['median']:8.2f} days")
        print(f"  Std Dev:{at['std']:8.2f} days")
        print(f"  Min:    {at['min']:8.2f} days")
        print(f"  Max:    {at['max']:8.2f} days")
    
    print("\n" + "-"*80)
    print("PROCESSING TIME BY SEGMENT")
    print("-"*80)
    for segment, seg_stats in sorted(stats['average_times_by_segment'].items()):
        print(f"\n  {segment}:")
        print(f"    Count:  {seg_stats['count']:4d}")
        print(f"    Mean:   {seg_stats['mean']:8.2f} days")
        print(f"    Median: {seg_stats['median']:8.2f} days")
        if "min" in seg_stats and "max" in seg_stats:
            print(f"    Min:    {seg_stats['min']:8.2f} days")
            print(f"    Max:    {seg_stats['max']:8.2f} days")
    
    if stats.get("county_review_vs_applicant"):
        print("\n" + "-"*80)
        print("COUNTY REVIEW VS. APPLICANT (mean days per permit, cumulative stage time)")
        print("-"*80)
        cv = stats["county_review_vs_applicant"]
        print(f"  County review — mean: {cv['county_review_mean']:8.2f} d, median: {cv['county_review_median']:.2f} d")
        print(f"  With applicant  — mean: {cv['applicant_mean']:8.2f} d, median: {cv['applicant_median']:.2f} d")
        print(f"  Debris (EPA/USACE only, not in sums above) — mean: {cv['debris_mean']:.2f} d")
        print("  Note: cumulative stage times; parallel reviews and unfinished debris in 'standard'")
        print("  flow can make county+applicant+debris exceed wall-clock days to construction.")

    if "total_waiting_time" in stats:
        print("\n" + "-"*80)
        print("TOTAL WAITING TIME (across all stages)")
        print("-"*80)
        tw = stats["total_waiting_time"]
        print(f"  Mean:   {tw['mean']:8.2f} days")
        print(f"  Median: {tw['median']:8.2f} days")
        print(f"  Std Dev:{tw['std']:8.2f} days")
        print(f"  Min:    {tw['min']:8.2f} days")
        print(f"  Max:    {tw['max']:8.2f} days")

    if "total_service_time" in stats:
        print("\n" + "-"*80)
        print("TOTAL SERVICE TIME (across all stages)")
        print("-"*80)
        ts = stats["total_service_time"]
        print(f"  Mean:   {ts['mean']:8.2f} days")
        print(f"  Median: {ts['median']:8.2f} days")
        print(f"  Std Dev:{ts['std']:8.2f} days")
        print(f"  Min:    {ts['min']:8.2f} days")
        print(f"  Max:    {ts['max']:8.2f} days")

    print("\n" + "-"*80)
    print("PUBLIC WORKS RE-CHECK STATISTICS")
    print("-"*80)
    if stats.get('public_works_rechecks'):
        rc = stats['public_works_rechecks']
        print(f"  Average re-checks per permit: {rc['average']:.2f}")
        print(f"  Maximum re-checks: {rc['max']}")
        print(f"  Permits requiring re-checks: {rc['total_permits_with_rechecks']}")

    if stats.get('applicant_revisions'):
        print("\n" + "-"*80)
        print("APPLICANT REVISIONS (when plan returned but not yet approved)")
        print("-"*80)
        ar = stats['applicant_revisions']
        print(f"  Mean total revision time per permit: {ar['total_time_mean']:.2f} days")
        print(f"  Median total revision time per permit: {ar['total_time_median']:.2f} days")
        print(f"  Mean revision count per permit: {ar['revision_count_mean']:.2f}")
        print(f"  Maximum revisions (any permit): {ar['revision_count_max']}")
        print(f"  Permits with at least one revision: {ar['permits_with_revisions']}")
        if stats.get('average_total_time') and stats['average_total_time'].get('mean', 0) > 0:
            pct = 100.0 * ar['total_time_mean'] / stats['average_total_time']['mean']
            print(f"  → Applicant revision time is {pct:.1f}% of mean total processing time (disaster to construction).")
    
    print("\n" + "="*80)



