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
    if stats['public_works_rechecks']:
        rc = stats['public_works_rechecks']
        print(f"  Average re-checks per permit: {rc['average']:.2f}")
        print(f"  Maximum re-checks: {rc['max']}")
        print(f"  Permits requiring re-checks: {rc['total_permits_with_rechecks']}")
    
    print("\n" + "="*80)



