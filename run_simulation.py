"""
Main script to run the permit simulation and display results.
"""

import simpy
from permit_simulation import PermitSimulation
import json
from datetime import datetime


def run_simulation(
    num_permits: int = 100,
    simulation_duration: float = None,
    random_seed: int = 42,
    inter_arrival_time: float = 1.0,  # days between permit arrivals
    sequential: str = "standard",
    ai_review: str = "none",
    pct_pre_approved: float = 0.02,
    pct_custom: float = 0.90,
    pct_self_cert: float = 0.08,
    pct_like_for_like: float = 0.80,
    review_duration_families: dict[str, str] | None = None,
    review_duration_multipliers: dict[str, float] | None = None,
    pre_application_distribution: str = "baseline",
):
    """
    Run the permit simulation.
    
    Args:
        num_permits: Number of permits to simulate (if simulation_duration is None)
        simulation_duration: Maximum simulation time in days (if None, runs until all permits complete)
        random_seed: Random seed for reproducibility
        inter_arrival_time: Average time between permit arrivals (days)
        sequential: Processing mode: \"standard\", \"parallel\", or \"sequential\".
        pct_pre_approved: Fraction of permits that are pre-approved plans (0–1).
        pct_custom: Fraction of permits that are custom builds (0–1).
        pct_self_cert: Fraction of permits that are self-certification (0–1).
        pct_like_for_like: Fraction of permits that are like-for-like (0–1).
        review_duration_families: Optional map for review stages (planning/public_works/fire)
            to sampling family (normal/lognormal/triangular/uniform).
        review_duration_multipliers: Optional map of duration multipliers by stage.
            Keys can include planning/public_works/fire/special_zoning/agency_referral.
        pre_application_distribution: Distribution choice for pre-application duration.
            Supported values: baseline, lognormal_180, lognormal_60, poisson_10.
    """
    env = simpy.Environment()
    sim = PermitSimulation(
        env,
        random_seed=random_seed,
        ai_review=ai_review,
        pct_pre_approved=pct_pre_approved,
        pct_custom=pct_custom,
        pct_self_cert=pct_self_cert,
        pct_like_for_like=pct_like_for_like,
        review_duration_families=review_duration_families,
        review_duration_multipliers=review_duration_multipliers,
        pre_application_distribution=pre_application_distribution,
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
            
            # Exponential inter-arrival time
            yield env.timeout(inter_arrival_time)
    
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
    inter_arrival_time: float = 1.0,
    scenario_params_list: list[dict] | None = None,
    collect_permits: bool = False,
):
    """
    Run the simulation many times, optionally for multiple scenarios.

    Args:
        n_runs: Number of repetitions per scenario.
        num_permits: Number of permits per run (if simulation_duration is None).
        simulation_duration: Max simulation time in days (optional).
        base_seed: Base random seed; each run uses base_seed + run_index.
        inter_arrival_time: Average time between permit arrivals (days).
        scenario_params_list: List of dicts, each describing a scenario.
            Each dict can contain:
              - "name": scenario name (string, for labeling)
              - any extra keyword args for run_simulation
                (e.g. "sequential", "ai_review", pct_* parameters).
        collect_permits: If True, also return completed permits for each run.

    Example scenario list:
        [
            {"name": "standard_default", "sequential": "standard"},
            {"name": "parallel_default", "sequential": "parallel"},
            {
                "name": "balanced_segments",
                "sequential": "standard",
                "pct_pre_approved": 0.5,
                "pct_custom": 0.25,
                "pct_self_cert": 0.25,
                "pct_like_for_like": 0.8,
            },
        ]

    Returns:
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
    """
    if scenario_params_list is None:
        scenario_params_list = [{"name": "default"}]

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
                inter_arrival_time=inter_arrival_time,
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

    return results


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



