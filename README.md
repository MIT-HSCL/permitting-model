# Post-Disaster Permitting Process Simulation

A discrete event simulation using SimPy that models the post-disaster permitting process from fire event to construction readiness.

## Overview

This simulation models the complete workflow of permit processing after a disaster event, including:

1. **Pre-Planning Phase**:
   - Debris removal (EPA Phase 1 → USACE Phase 2)
   - Securing authorization & funding
   - Plan preparation and submission

2. **Planning Department**:
   - Processing based on permit segment type
   - Segments 5 & 6 (self-certification) skip this step

3. **Public Works (Building & Safety)**:
   - Initial check (segments 3-6 only)
   - Approval/re-check loop
   - Parallel reviews by Fire and Public Health departments

## Permit Segments

The simulation models 6 different permit segments:

| Segment | Plan Type | Likeness | Description |
|---------|-----------|----------|-------------|
| 1 | Pre-approved plan | Like-for-like | ~80% of permits |
| 2 | Pre-approved plan | Non-like-for-like | ~20% of permits |
| 3 | Custom build | Like-for-like | Requires initial check |
| 4 | Custom build | Non-like-for-like | Requires initial check |
| 5 | Custom build w/ self-certification | Like-for-like | Skips planning dept |
| 6 | Custom build w/ self-certification | Non-like-for-like | Skips planning dept |

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the simulation:
```bash
python run_simulation.py
```

### Simulation Parameters

You can modify the simulation parameters in `run_simulation.py`:

- `NUM_PERMITS`: Number of permits to simulate (default: 100)
- `RANDOM_SEED`: Random seed for reproducibility (default: 42)
- `INTER_ARRIVAL_TIME`: Average time between permit arrivals in days (default: 1.0)

### Customizing the Simulation

To customize the simulation behavior, edit `permit_simulation.py`:

- **Segment distribution**: Modify the `sample_segment()` method
- **Processing times**: Adjust the distribution parameters in each process method
- **Resource capacities**: Change the `capacity` parameter when creating resources
- **Approval rates**: Modify the probability thresholds in `public_works_initial_check()` and `public_works_recheck()`

## Process Flow

### Initial Phase (Parallel Paths)

**Path 1: Debris Removal**
- EPA Debris Removal (Phase 1): Uniform distribution (2-3 days)
- USACE Debris Removal (Phase 2): Uniform distribution (2-3 days)

**Path 2: Authorization & Plans**
- Securing authorization: Normal distribution N(42, 20) days
- Prepare & submit plans:
  - Segments 1-2: Normal distribution N(10, 2) days
  - Segments 3-6: Lognormal distribution (median 150 days, σ=0.6)

### Planning Department

- **Segments 1 & 3** (like-for-like): Normal distribution N(3, 1) days
- **Segments 2 & 4** (non-like-for-like): Normal distribution N(33, 10) days
- **Segments 5 & 6** (self-certification): **SKIPPED**

### Public Works (Building & Safety)

- **Initial Check** (segments 3-6 only):
  - Processing time: Normal distribution N(11.6, 2) days
  - Approval rate: 75% approved, 25% require re-check
  
- **Re-check Loop** (if not approved):
  - Processing time: Normal distribution N(8.3, 2) days
  - Approval rate: 75% approved, 25% require another re-check

### Parallel Reviews (After Approval)

- **Fire Department Review**:
  - 30% of permits
  - Processing time: Normal distribution N(13, 2) days

- **Public Health Review**:
  - 1.3% of permits
  - Processing time: Normal distribution N(10, 2) days

## Output

The simulation provides:

1. **Console Statistics**:
   - Total completed and in-progress permits
   - Segment distribution
   - Overall processing time statistics (mean, median, std dev, min, max)
   - Processing time by segment
   - Public Works re-check statistics

2. **Optional JSON Export**:
   - Detailed permit-level data
   - Timestamps for each process stage
   - Complete statistics

## Resource Capacities

- EPA Debris Removal: 140 servers (1400 people in 5-person crews)
- USACE Debris Removal: 140 servers (1400 people in 5-person crews)
- Planning Department: 125 capacity (25 servers × 5 permits caseload each)
- Public Works: 25 servers
- Fire Department: 25 servers
- Public Health: 25 servers

## Notes

- All time distributions and simulation times are in days
- The simulation uses SimPy's discrete event simulation engine
- Random seed can be set for reproducible results
- The model assumes permits arrive according to an exponential inter-arrival distribution

## License

This simulation is created for academic research purposes.
