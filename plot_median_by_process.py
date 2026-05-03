"""
Run standard, sequential, and parallel simulations (same seed and permit count),
then plot median total time from disaster to construction start by segment
for each process.
"""

from run_simulation import run_simulation
from visualize_permits import plot_median_total_time_by_process


def main(num_permits: int = 2000, random_seed: int = 42, save_path: str = "median_total_time_by_process.png"):
    print("Running Standard process...")
    sim_standard = run_simulation(
        num_permits=num_permits,
        random_seed=random_seed,
        sequential="standard",
    )
    print("Running Sequential process...")
    sim_sequential = run_simulation(
        num_permits=num_permits,
        random_seed=random_seed,
        sequential="sequential",
    )
    print("Running Parallel process...")
    sim_parallel = run_simulation(
        num_permits=num_permits,
        random_seed=random_seed,
        sequential="parallel",
    )

    permits_by_process = {
        "Standard": sim_standard.completed_permits,
        "Sequential": sim_sequential.completed_permits,
        "Parallel": sim_parallel.completed_permits,
    }
    fig, ax = plot_median_total_time_by_process(permits_by_process)
    if fig is not None:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {save_path}")
        fig.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Plot median total time by segment for Standard, Sequential, Parallel.")
    parser.add_argument("--num-permits", type=int, default=2000, help="Number of permits per run (default 2000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default 42)")
    parser.add_argument("--output", "-o", default="median_total_time_by_process.png", help="Output image path")
    args = parser.parse_args()
    main(num_permits=args.num_permits, random_seed=args.seed, save_path=args.output)
