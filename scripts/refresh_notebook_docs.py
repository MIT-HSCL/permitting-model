#!/usr/bin/env python3
"""Strip outputs and inject walkthrough markdown into project notebooks."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PATH_CELL_SOURCE = """import sys
from pathlib import Path

_repo = Path.cwd()
if not (_repo / "run_simulation.py").exists():
    _repo = _repo.parent
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))
"""


def _lines(text: str) -> list[str]:
    if not text.endswith("\n"):
        text += "\n"
    return [line if line.endswith("\n") else line + "\n" for line in text.splitlines(True)]


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def clean_cell(cell: dict) -> dict:
    if cell.get("cell_type") == "code":
        cell["outputs"] = []
        cell["execution_count"] = None
    return cell


def is_empty(cell: dict) -> bool:
    src = "".join(cell.get("source", [])).strip()
    return not src


def ensure_path_cell(cells: list[dict]) -> list[dict]:
    """First code cell should be repo path setup."""
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "_repo" in src and "run_simulation.py" in src:
            cell["source"] = _lines(PATH_CELL_SOURCE)
            return cells
        break
    return [clean_cell({"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None, "source": _lines(PATH_CELL_SOURCE)})] + cells


def insert_before(cells: list[dict], index: int, markdown: str) -> list[dict]:
    return cells[:index] + [md(markdown)] + cells[index:]


def insert_markdowns(cells: list[dict], items: list[tuple[str, str]]) -> list[dict]:
    """Insert markdown headings before code cells matching patterns (bottom-up)."""
    pending: list[tuple[int, str]] = []
    for pattern, heading in items:
        i = find_code(cells, pattern)
        if i is not None:
            pending.append((i, heading))
    for i, heading in sorted(pending, key=lambda x: x[0], reverse=True):
        if not any(heading.split("\n")[0] in "".join(c.get("source", [])) for c in cells[max(0, i - 2):i]):
            cells = insert_before(cells, i, heading)
def find_code(cells: list[dict], pattern: str, start: int = 0) -> int | None:
    rx = re.compile(pattern, re.M)
    for i, cell in enumerate(cells[start:], start):
        if cell.get("cell_type") != "code":
            continue
        if rx.search("".join(cell.get("source", []))):
            return i
    return None


def save(nb_path: Path, cells: list[dict]) -> None:
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cleaned = [clean_cell(c) for c in cells if not is_empty(c)]
    nb["cells"] = cleaned
    nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  saved {nb_path.relative_to(REPO)} ({len(cleaned)} cells)")


def refresh_run_simulation(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = insert_before(
        cells,
        0,
        """# Main simulation notebook

Monte Carlo runs of the post-disaster permitting model with diagnostics and visualizations.

**Workflow**
1. **Setup & run** — configure parameters and run `N_RUNS` simulations
2. **Aggregate metrics** — county vs applicant time, debris timing, staff utilization
3. **Visualizations** — Gantt charts and process-step breakdowns

Adjust `NUM_PERMITS` and `N_RUNS` in the first code cell. Heavy settings can take a long time.

Related: [`convergence_plot.ipynb`](convergence_plot.ipynb) for Monte Carlo convergence.""",
    )
    # skip intro we just added + path cell
    idx = find_code(cells, r"run_multiple_simulations")
    if idx is not None:
        cells = insert_before(cells, idx, "## 1. Setup and run Monte Carlo\n\nRuns the simulation `N_RUNS` times and stores results in `results_runs`, `all_permits`, and staff-utilization series.")
    for pattern, heading in [
        (r"County review vs applicant", "## 2. County review vs applicant time\n\nDistribution of county review days vs applicant-side days (plan prep + revisions) across Monte Carlo runs."),
        (r"Debris timing now comes", "## 3. Debris removal timing\n\nEPA phase completion and USACE wall-clock span (from the same Monte Carlo batch — no re-run needed)."),
        (r"Gantt chart for one random permit", "## 4. Gantt charts\n\nTimeline views for individual permits. The first chart samples from the pooled permit list; the second picks one full run then one permit."),
        (r"Gantt chart for 3 random", "### Three random permits"),
        (r"plot_average_waiting_and_service_by_step", "## 5. Waiting and service by process step\n\nAggregate time in queue vs in service for each major stage."),
        (r"plan_prep_end - p.debris_removal_end", "## 6. Gap: debris removal end → plan submission\n\nDays between debris completion and plan prep completion."),
        (r"Snapshot summaries for day 415", "## 7. Permit counts at fixed calendar days\n\nHow many permits have reached key milestones by day 415 and 474."),
        (r"Mean staff utilization", "## 8. Staff utilization\n\nMean planning / public works / fire utilization over time across runs."),
        (r"Peak mean utilization", "### Peak utilization"),
        (r"Day-474 average county-review", "### Day-474 county review vs applicant revisions"),
        (r"convergence", None),  # skip - handled by markdown cell about convergence
    ]:
        if heading is None:
            continue
        i = find_code(cells, pattern)
        if i is not None and not any(heading.split("\n")[0] in "".join(c.get("source", [])) for c in cells[max(0, i - 2):i]):
            cells = insert_before(cells, i, heading)
    # Remove stub comment-only cell if present
    cells = [c for c in cells if not (
        c.get("cell_type") == "code"
        and re.match(r"^#\s*`results`", "".join(c.get("source", [])).strip())
    )]
    return cells


def refresh_convergence(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    # Replace old intro if present
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and c.get("source", [""])[0].startswith("# Convergence")
    )]
    cells = insert_before(
        cells,
        1,
        """# Monte Carlo convergence

Shows whether the **mean total processing time** stabilizes as you add Monte Carlo runs.

**Two ways to get data**
- Re-run the simulation in the setup cell below (match parameters with `run_simulation.ipynb` for consistency)
- Or load a saved `convergence_data.npz` from a prior run""",
    )
    i = find_code(cells, r"Cumulative mean of per-run mean")
    if i:
        cells = insert_before(cells, i, "## Plot convergence curve\n\nCumulative mean with approximate 95% confidence band on the mean.")
    i = find_code(cells, r"DATA_NPZ|run_multiple_simulations")
    if i:
        cells = insert_before(cells, i, "## Setup\n\nConfigure `NUM_PERMITS`, `N_RUNS`, and scenario parameters — or set `DATA_NPZ` to skip re-running.")
    return cells


def refresh_usace(cells: list[dict]) -> list[dict]:
    return [
        md("""# USACE debris-removal staffing schedule

Visualizes the **time-varying USACE crew capacity** built into `PermitSimulation.USACE_CREW_SCHEDULE`. This is not a simulation run — it plots the model's assumed crew ramp-up after disaster."""),
        md("## Setup"),
        clean_cell({"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None, "source": _lines(PATH_CELL_SOURCE)}),
        md("## Plot crew capacity over time"),
        next(c for c in cells if "USACE_CREW_SCHEDULE" in "".join(c.get("source", []))),
    ]


def refresh_segments(cells: list[dict]) -> list[dict]:
    # Already structured; enhance intro
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and "Segment mix comparison" in "".join(c.get("source", []))
    )]
    cells = insert_before(
        cells,
        0,
        """# Segment mix comparison

Monte Carlo comparison of **default** (LA-style) vs **balanced** (more pre-approved / self-cert) permit mixes at **6,571 permits**.

1. **Setup** — parameters and helper functions
2. **Run and compare** — one multi-run cell per scenario, then segment box plots

For the staffing × volume grid under `lognormal_180`, see [`run_simulation_with_segments_cases.ipynb`](run_simulation_with_segments_cases.ipynb).""",
    )
    return ensure_path_cell(cells)


def refresh_segments_cases(cells: list[dict]) -> list[dict]:
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and "Segment case comparisons" in "".join(c.get("source", []))
    )]
    cells = ensure_path_cell(cells)
    cells = insert_before(
        cells,
        1,
        """# Six-case segment analysis

Thesis-style grid: **2 permit volumes × 3 staffing levels**, with `lognormal_180` pre-application timing.

| Section | What it produces |
|---------|------------------|
| 1. Disaster → construction | Segment box plots for all six cases |
| 2. Application → construction | Same grid, metric starts at planning request |
| 3. Expedited mix experiment | Homogeneous custom non-like vs balanced mix |
| 4. Summary figure | Pooled box plots via `plot_expedited_baseline_app_to_ready_boxplots` |
| 5. Significance check | Scenario-level t-tests vs custom non-like reference |

**Runtime:** 6 cases × `N_RUNS_CASES` each — start with `N_RUNS_CASES = 10` for testing.""",
    )
    for pattern, heading in [
        (r"Six-case segment boxplots: lognormal_180 only", "## 1. Disaster to construction by segment\n\nRuns all six staffing × volume cases and plots pooled segment box plots."),
        (r"application -> construction start", "## 2. Application to construction by segment\n\nUses `planning_request` as the start of county review."),
        (r"baseline vs balanced by scenario", "## 3. Expedited permit mix experiment\n\nFor each of the six cases, compares homogeneous custom non-like vs balanced segment mix."),
        (r"plot_expedited_baseline_app_to_ready", "## 4. Baseline vs expedited summary figure"),
        (r"Statistical check", "## 5. Are segment differences mostly noise?\n\nScenario-level means with t-tests against custom non-like."),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_parallel(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and "How to use this notebook" in "".join(c.get("source", []))
    )]
    cells = insert_before(
        cells,
        1,
        """# Process layout comparison (standard / sequential / parallel)

Compares three **process configurations** for how debris, plan prep, and county reviews are sequenced.

**Workflow**
1. **Single runs** — one simulation per layout (for Gantt charts)
2. **Multi-run comparison** — aggregate statistics across `N_RUNS`
3. **Full scenario grid** — staffing × volume × layout (heavy; saves CSVs under `results/`)

Run sections in order. Lower `N_RUNS` / `N_RUNS_GRID` while testing.""",
    )
    for pattern, heading in [
        (r"from run_simulation import run_simulation", "## 1. Setup\n\nShared parameters for single- and multi-run sections."),
        (r"Run all three simulations", "## 2. Single-run simulations\n\nOne run each for sequential, standard, and parallel layouts."),
        (r"Print statistics for each process", "### Print single-run statistics"),
        (r"Run multiple simulations for each process configuration", "## 3. Multi-run comparison\n\n`N_RUNS` repetitions per layout; feeds aggregate box plots."),
        (r"plot_median_total_time_by_process\(runs_by_process\)", "## 4. Aggregate plots\n\nMedian disaster-to-construction time by segment, compared across layouts."),
        (r"Gantt charts for one random Segment 4", "### Gantt charts (single-run permits)"),
        (r"visualize_all\(sim_sequential", "### Full visualization sets"),
        (r"like-for-like step-level timeline", "## 5. Like-for-like step summary table"),
        (r"Median total time by segment — full scenario grid|FIG_BASENAME_TEMPLATE", "## 6. Full scenario grid (optional)\n\nAll combinations of staffing, permit volume, and process layout. Outputs saved under `results/median_total_time_by_process/`."),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_ai(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and "How to use this notebook" in "".join(c.get("source", []))
    )]
    cells = insert_before(
        cells,
        1,
        """# AI-assisted review comparison

Compares **no AI**, **initial AI check**, and **full AI review** modes (standard process layout).

**Workflow**
1. **Single runs** — one simulation per AI mode
2. **Multi-run comparison** — aggregate box plots across `N_RUNS`
3. **Six-stratum panels** — staffing × volume grid (matches policy figures)

Homogeneous **custom non-like** permit mix by default in early cells; low staffing in single-run block.""",
    )
    for pattern, heading in [
        (r"from run_simulation import run_simulation", "## 1. Setup"),
        (r"Run all three simulations", "## 2. Single-run simulations\n\nStandard vs initial AI check vs full AI review."),
        (r"Print statistics for each process", "### Print single-run statistics"),
        (r"Run multiple simulations for each AI scenario", "## 3. Multi-run comparison"),
        (r"plot_median_total_time_by_process\(runs_by_process\)", "## 4. Aggregate segment plots"),
        (r"non-like-for-like step-level", "### Non-like-for-like step summary"),
        (r"application_to_ready=True", "### Application-to-construction by segment"),
        (r"N_RUNS_PANEL", "## 5. Six-stratum AI panels\n\n2,000 / 6,500 permits × low / medium / high staffing."),
        (r"Plot one selected panel", "### Plot selected panel"),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_policy(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and c.get("source", [""])[0].startswith("# Policy Lever")
    )]
    cells = insert_before(
        cells,
        1,
        """# Policy lever impact analysis

Monte Carlo experiment grid for **policy interventions** (AI review, process layout, expedited permit mix) across staffing and permit-volume strata.

**Workflow**
1. Define scenario grid and run experiments (`N_RUNS` × all combinations — slow)
2. Save CSVs to `results/` for reuse
3. Build comparison figures (box plots by intervention)

Re-run the save cell after experiments if you change parameters. Figure cells load from `results/policy_lever_impact_per_run.csv`.""",
    )
    for pattern, heading in [
        (r"import itertools", "## 1. Setup and scenario grid"),
        (r"Run experiments|run_multiple_simulations", "## 2. Run experiments\n\nThis is the longest step. Reduce `N_RUNS` or the scenario list while testing."),
        (r"Policy lever impacts", "## 3. Compute lever impacts\n\nPercent change vs baseline for parallel layout and AI modes."),
        (r"Plot average utilization", "## 4. Staff utilization plots"),
        (r"Save results|policy_lever_impact_results", "## 5. Save results\n\nWrites CSVs under `results/` — required before figure cells below."),
        (r"policy_intervention_comparison|app_to_ready_policy_comparison", "## 6. Policy comparison figures\n\nBox plots by permit volume (2,000 vs 6,500)."),
        (r"save_three_stratum_figures|policy_strata", "## 7. Six-stratum summary figures\n\nThree PNGs comparing AI, process layout, and expedited mix."),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_sensitivity(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and "Sensitivity Analysis" in "".join(c.get("source", []))
    )]
    cells = insert_before(
        cells,
        1,
        """# Sensitivity analysis

Sweeps **review-duration multipliers** and **pre-application distribution** choices to see which assumptions move outcomes most.

**Outputs:** per-run and summary CSVs under `results/`.

Start with small `N_RUNS` and a reduced parameter grid while testing.""",
    )
    for pattern, heading in [
        (r"import itertools", "## 1. Setup\n\nDefines the sensitivity runner function."),
        (r"def run_duration_level_sensitivity", "### Sensitivity runner"),
        (r"Experiment settings|PRE_APP_DISTRIBUTIONS", "## 2. Run sensitivity sweep"),
        (r"^summary = ", "## 3. Review summary table"),
        (r"Optional visualization", "## 4. Optional distribution overlay plot"),
        (r"Export CSV", "## 5. Export results"),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_preapp_curves(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and "Pre-Application Distribution" in "".join(c.get("source", []))
    )]
    cells = insert_before(
        cells,
        1,
        """# Pre-application duration distributions

Compares the **PDF/CDF** of pre-application timing options used in the simulation (`baseline`, `lognormal_180`, `lognormal_60`, `poisson_10`, etc.).

No simulation run — this is a distribution visualization notebook.""",
    )
    for pattern, heading in [
        (r"import numpy", "## 1. Setup"),
        (r"X range for comparing", "## 2. Compare PDF curves"),
        (r"CDF comparison", "## 3. Compare CDF curves (optional)"),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_preapp_volume(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = [c for c in cells if not (
        c.get("cell_type") == "markdown" and "Pre-application distribution" in "".join(c.get("source", []))
    )]
    cells = insert_before(
        cells,
        1,
        """# Pre-application distribution × permit volume

Compares pre-app timing assumptions at **2,000 vs 6,500** permits with fixed low/medium/high staffing.

**Focus:** `lognormal_180` staffing comparison and waiting vs service breakdown panels.""",
    )
    for pattern, heading in [
        (r"import importlib|run_multiple_simulations", "## 1. Setup and multi-run batch"),
        (r"def disaster_to_ready_days", "## 2. Summarize disaster-to-ready times"),
        (r"Optional: save metrics", "## 3. Optional — save metrics CSV"),
        (r"Focused staffing comparison", "## 4. Staffing comparison at 2,000 permits (`lognormal_180`)"),
        (r"Panel 1: waiting vs service", "## 5. Waiting vs service panels"),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_timeline(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = insert_before(
        cells,
        0,
        """# Cross-case recovery timelines

Plots **empirical recovery milestones** from `data/cross_case_recovery_timelines.csv` (Camp, Carr, Marshall, and other fires).

No simulation — reads CSV data only.""",
    )
    for pattern, heading in [
        (r"generate progress bar|Cross_case|cross_case_recovery", "## 1. Load data and progress-bar figures"),
        (r"Improved comparison plot", "## 2. Multi-fire milestone comparison"),
        (r"Marshall fire only", "## 3. Marshall fire only"),
        (r"Marshall, Camp, and Carr", "## 4. Marshall, Camp, and Carr"),
        (r"permit issue to construction complete", "## 5. Lag: permit issue → construction complete"),
    ]:
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
    return cells


def refresh_fit_data(cells: list[dict]) -> list[dict]:
    cells = ensure_path_cell(cells)
    cells = insert_before(
        cells,
        1,
        """# Fit pre-application timing to empirical data

Exploratory notebook for fitting **disaster → permit application** durations to case-study CSVs in this folder (`disaster_to_application_la.csv`, Louisville/Marshall, Paradise, Santa Rosa, Sonoma).

**Note:** Run from this directory or rely on the path setup cell. Cells are exploratory — run the sections you need rather than the entire notebook top-to-bottom.""",
    )
    # Add section headers at first occurrence of key patterns
    seen: set[str] = set()
    for pattern, heading in [
        (r"disaster_to_application_la", "## Los Angeles / Palisades data"),
        (r"disaster_to_application_louisville|Marshall", "## Marshall (Louisville) data"),
        (r"Paradise\.csv", "## Paradise data"),
        (r"SantaRosa\.csv", "## Santa Rosa data"),
        (r"Sonoma\.csv", "## Sonoma data"),
        (r"Forecast LA lognormal", "## Forecast cumulative applications (LA)"),
        (r"probplot", "## Distribution diagnostics (Q-Q plots)"),
    ]:
        if heading in seen:
            continue
        i = find_code(cells, pattern)
        if i is not None:
            cells = insert_before(cells, i, heading)
            seen.add(heading)
    return cells


REFRESHERS = {
    REPO / "notebooks/run_simulation.ipynb": refresh_run_simulation,
    REPO / "notebooks/convergence_plot.ipynb": refresh_convergence,
    REPO / "notebooks/usace_staffing.ipynb": refresh_usace,
    REPO / "notebooks/run_simulation_with_segments.ipynb": refresh_segments,
    REPO / "notebooks/run_simulation_with_segments_cases.ipynb": refresh_segments_cases,
    REPO / "notebooks/run_simulation_parallel.ipynb": refresh_parallel,
    REPO / "notebooks/run_simulation_with_ai.ipynb": refresh_ai,
    REPO / "notebooks/policy_lever_impact_analysis.ipynb": refresh_policy,
    REPO / "notebooks/sensitivity_analysis.ipynb": refresh_sensitivity,
    REPO / "notebooks/pre_application_distribution_curves.ipynb": refresh_preapp_curves,
    REPO / "notebooks/preapp_distribution_volume_comparison.ipynb": refresh_preapp_volume,
    REPO / "notebooks/timeline_data.ipynb": refresh_timeline,
    REPO / "data/pre_application/fit_data.ipynb": refresh_fit_data,
}


def main() -> None:
    for nb_path, refresher in REFRESHERS.items():
        if not nb_path.exists():
            print(f"skip missing {nb_path}")
            continue
        print(f"refresh {nb_path.relative_to(REPO)}")
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
        cells = refresher(list(nb["cells"]))
        save(nb_path, cells)


if __name__ == "__main__":
    main()
