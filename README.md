# Post-Disaster Housing Permitting Simulation

A [SimPy](https://simpy.readthedocs.io/) discrete-event simulation of the post-disaster permitting workflow—from debris removal and plan preparation through county review to construction readiness. The model supports Monte Carlo experiments, policy lever comparisons, AI-assisted review scenarios, and thesis-style visualizations.

**Repository:** [github.com/mfinn36/permitting-model](https://github.com/mfinn36/permitting-model)

## Quick start

Requires **Python 3.10+**.

```bash
git clone https://github.com/mfinn36/permitting-model.git
cd permitting-model

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[notebooks]"
```

Run a small simulation from the command line:

```bash
python run_simulation.py --num-permits 100 --seed 42
```

Open Jupyter (from the repo root or from `notebooks/`):

```bash
jupyter lab
```

Each notebook’s **first cell** adds the repo root to `sys.path`, so imports work even if you skip the editable install above.

Start with [`notebooks/run_simulation.ipynb`](notebooks/run_simulation.ipynb) for interactive exploration, or [`notebooks/run_simulation_with_segments.ipynb`](notebooks/run_simulation_with_segments.ipynb) for segment-level workflows.

## Repository layout

| Path | Description |
|------|-------------|
| `permit_simulation.py` | Core SimPy model (permit segments, resources, process logic) |
| `run_simulation.py` | Run single or multiple simulations; CLI entry point |
| `visualize_permits.py` | Gantt charts, box plots, utilization, and summary figures |
| `simulation_plot_helpers.py` | Shared statistics helpers for Monte Carlo plots |
| `policy_intervention_stratum_figures.py` | Policy-comparison figure builder (used by policy notebook) |
| `plot_median_by_process.py` | CLI: compare standard / sequential / parallel layouts |
| `repo_paths.py` | `DATA_DIR`, `RESULTS_DIR`, and other standard paths |
| `data/` | Empirical inputs (cross-case timelines, pre-application duration CSVs) |
| `data/pre_application/` | Disaster-to-application timing data and `fit_data.ipynb` |
| `notebooks/` | Analysis and thesis figure notebooks |
| `results/` | Generated CSVs and PNGs (created at runtime; not committed) |

## Permit segments

The model uses six permit segments (plan type × likeness × self-certification):

| Segment | Plan type | Likeness | Notes |
|---------|-----------|----------|-------|
| 1 | Pre-approved | Like-for-like | |
| 2 | Pre-approved | Non-like-for-like | |
| 3 | Custom | Like-for-like | Initial public works check |
| 4 | Custom | Non-like-for-like | Initial public works check |
| 5 | Custom + self-cert | Like-for-like | Skips planning department |
| 6 | Custom + self-cert | Non-like-for-like | Skips planning department |

Mix presets (`permit_mix`): `la` (Los Angeles–style default), `balanced`, or `all_custom_non_like_for_like`.

## Notebooks

Run from the repo root. Outputs are written under `results/` unless noted.

| Notebook | Purpose |
|----------|---------|
| `run_simulation.ipynb` | Main interactive runs, utilization, and visualizations |
| `run_simulation_with_segments.ipynb` | Core segment workflow (default vs balanced mix) |
| `run_simulation_with_segments_cases.ipynb` | Six-case staffing × permit volume grid (`lognormal_180`) |
| `run_simulation_with_ai.ipynb` | AI review modes (`initial_check`, `full_review`) |
| `run_simulation_parallel.ipynb` | Standard / sequential / parallel process layouts across scenarios |
| `policy_lever_impact_analysis.ipynb` | Policy lever Monte Carlo and comparison figures |
| `sensitivity_analysis.ipynb` | Parameter sensitivity sweeps |
| `convergence_plot.ipynb` | Monte Carlo convergence checks |
| `timeline_data.ipynb` | Cross-case recovery timeline plots |
| `pre_application_distribution_curves.ipynb` | Pre-application duration distributions |
| `preapp_distribution_volume_comparison.ipynb` | Pre-app distribution vs permit volume |
| `data/pre_application/fit_data.ipynb` | Fit pre-application timing to empirical CSVs |

Heavy notebooks may take minutes to hours depending on `NUM_PERMITS` and `N_RUNS`. Clear saved outputs with:

```bash
pip install nbstripout
nbstripout notebooks/*.ipynb data/pre_application/fit_data.ipynb
```

## Python API

```python
from run_simulation import run_simulation, run_multiple_simulations, print_statistics

sim = run_simulation(
    num_permits=500,
    random_seed=42,
    sequential="standard",       # "standard" | "parallel" | "sequential"
    ai_review="none",            # "none" | "initial_check" | "full_review"
    permit_mix="la",
    pre_application_distribution="baseline",  # baseline, lognormal_180, lognormal_60, poisson_10
)
print_statistics(sim.get_statistics())
```

```python
from visualize_permits import visualize_all

visualize_all(sim.completed_permits, save_prefix="results/my_run")
```

## Command-line utilities

```bash
# Median time by segment for three process layouts
python plot_median_by_process.py --num-permits 500 --output results/median_by_process.png

# Example visualizations after a short run
python visualize_permits.py
```

## Model overview

**Pre-application (parallel paths):** EPA/USACE debris removal; authorization and plan preparation (timing depends on segment and `pre_application_distribution`).

**County review:** Planning department (skipped for self-cert segments 5–6); public works initial check and re-check loop (segments 3–6); parallel fire and occasional public health review.

**Staffing:** Planning, public works, and fire use caseload-limited staff pools (`StaffCaseloadPool`).

All durations are in **days**. See docstrings in `permit_simulation.py` for distribution parameters and resource capacities.

## Data

- `data/cross_case_recovery_timelines.csv` — cross-jurisdiction recovery milestones for `timeline_data.ipynb`
- `data/pre_application/*.csv` — empirical disaster-to-application durations (LA, Louisville/Marshall, Paradise, Santa Rosa, Sonoma)

## Citation

If you use this code in research, please cite your copy of the repository and the associated thesis. A formal citation block can be added once the thesis is published.

## License

[MIT License](LICENSE) — Copyright (c) 2026 Megan Finnigan
