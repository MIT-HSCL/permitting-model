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
    inter_arrival_time: float = 1.0  # hours between permit arrivals
):
    """
    Run the permit simulation.
    
    Args:
        num_permits: Number of permits to simulate (if simulation_duration is None)
        simulation_duration: Maximum simulation time in hours (if None, runs until all permits complete)
        random_seed: Random seed for reproducibility
        inter_arrival_time: Average time between permit arrivals (hours)
    """
    env = simpy.Environment()
    sim = PermitSimulation(env, random_seed=random_seed)
    
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
            env.process(sim.permit_process(permit))
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
        max_time = 100000  # hours (safety limit)
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
        print(f"  Mean:   {at['mean']:8.2f} hours ({at['mean']/24:6.2f} days)")
        print(f"  Median: {at['median']:8.2f} hours ({at['median']/24:6.2f} days)")
        print(f"  Std Dev:{at['std']:8.2f} hours ({at['std']/24:6.2f} days)")
        print(f"  Min:    {at['min']:8.2f} hours ({at['min']/24:6.2f} days)")
        print(f"  Max:    {at['max']:8.2f} hours ({at['max']/24:6.2f} days)")
    
    print("\n" + "-"*80)
    print("PROCESSING TIME BY SEGMENT")
    print("-"*80)
    for segment, seg_stats in sorted(stats['average_times_by_segment'].items()):
        print(f"\n  {segment}:")
        print(f"    Count:  {seg_stats['count']:4d}")
        print(f"    Mean:   {seg_stats['mean']:8.2f} hours ({seg_stats['mean']/24:6.2f} days)")
        print(f"    Median: {seg_stats['median']:8.2f} hours ({seg_stats['median']/24:6.2f} days)")
    
    print("\n" + "-"*80)
    print("PUBLIC WORKS RE-CHECK STATISTICS")
    print("-"*80)
    if stats['public_works_rechecks']:
        rc = stats['public_works_rechecks']
        print(f"  Average re-checks per permit: {rc['average']:.2f}")
        print(f"  Maximum re-checks: {rc['max']}")
        print(f"  Permits requiring re-checks: {rc['total_permits_with_rechecks']}")
    
    print("\n" + "="*80)


def main():
    """Main execution function."""
    print("Starting Permit Simulation...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Simulation parameters
    NUM_PERMITS = 100
    RANDOM_SEED = 42
    INTER_ARRIVAL_TIME = 24.0  # 1 day between arrivals
    
    sim = run_simulation(
        num_permits=NUM_PERMITS,
        random_seed=RANDOM_SEED,
        inter_arrival_time=INTER_ARRIVAL_TIME
    )
    
    # Get and print statistics
    stats = sim.get_statistics()
    print_statistics(stats)
    
    # Optionally save detailed results to JSON
    save_results = input("\nSave detailed results to JSON? (y/n): ").lower().strip()
    if save_results == 'y':
        filename = f"simulation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert permits to serializable format
        results = {
            "simulation_parameters": {
                "num_permits": NUM_PERMITS,
                "random_seed": RANDOM_SEED,
                "inter_arrival_time": INTER_ARRIVAL_TIME,
            },
            "statistics": stats,
            "completed_permits": []
        }
        
        for permit in sim.completed_permits:
            permit_data = {
                "permit_id": permit.permit_id,
                "segment": permit.segment.name,
                "created_at": permit.created_at,
                "ready_for_construction": permit.ready_for_construction,
                "total_time": permit.ready_for_construction - permit.created_at if permit.ready_for_construction else None,
                "public_works_rechecks": permit.public_works_rechecks,
                "timestamps": {
                    "debris_removal_start": permit.debris_removal_start,
                    "debris_removal_end": permit.debris_removal_end,
                    "authorization_start": permit.authorization_start,
                    "authorization_end": permit.authorization_end,
                    "plan_prep_start": permit.plan_prep_start,
                    "plan_prep_end": permit.plan_prep_end,
                    "planning_start": permit.planning_start,
                    "planning_end": permit.planning_end,
                    "public_works_start": permit.public_works_start,
                    "public_works_end": permit.public_works_end,
                    "fire_review_start": permit.fire_review_start,
                    "fire_review_end": permit.fire_review_end,
                    "public_health_start": permit.public_health_start,
                    "public_health_end": permit.public_health_end,
                }
            }
            results["completed_permits"].append(permit_data)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {filename}")


if __name__ == "__main__":
    main()

