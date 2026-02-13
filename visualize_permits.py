"""
Visualization script for permit processing times.
Creates various charts showing time spent in each stage of the process.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import List, Optional
from permit_simulation import Permit


def calculate_stage_times(permit: Permit) -> dict:
    """
    Calculate time spent in each stage for a permit.
    Returns a dictionary with stage names and durations in days.
    """
    stages = {}
    
    # Debris removal - EPA (separate waiting and service)
    if (
        permit.epa_debris_request is not None
        and permit.epa_debris_service_start is not None
        and permit.epa_debris_end is not None
    ):
        stages["EPA Debris (Waiting)"] = permit.epa_debris_service_start - permit.epa_debris_request
        stages["EPA Debris (Service)"] = permit.epa_debris_end - permit.epa_debris_service_start

    # Debris removal - USACE (separate waiting and service)
    if (
        permit.usace_debris_request is not None
        and permit.usace_debris_service_start is not None
        and permit.usace_debris_end is not None
    ):
        stages["USACE Debris (Waiting)"] = permit.usace_debris_service_start - permit.usace_debris_request
        stages["USACE Debris (Service)"] = permit.usace_debris_end - permit.usace_debris_service_start
    
    # Authorization (no waiting, just service time)
    if permit.authorization_start is not None and permit.authorization_end is not None:
        stages['Authorization'] = permit.authorization_end - permit.authorization_start
    
    # Plan preparation (no waiting, just service time)
    if permit.plan_prep_start is not None and permit.plan_prep_end is not None:
        stages['Plan Preparation'] = permit.plan_prep_end - permit.plan_prep_start
    
    # Planning department - four buckets (initial waiting/service, recheck waiting/service)
    if (
        permit.planning_initial_waiting > 0
        or permit.planning_initial_service > 0
        or permit.planning_recheck_waiting > 0
        or permit.planning_recheck_service > 0
    ):
        stages["Planning Initial (Waiting)"] = permit.planning_initial_waiting
        stages["Planning Initial (Service)"] = permit.planning_initial_service
        stages["Planning Recheck (Waiting)"] = permit.planning_recheck_waiting
        stages["Planning Recheck (Service)"] = permit.planning_recheck_service
        stages["Planning Total Waiting"] = permit.planning_initial_waiting + permit.planning_recheck_waiting
        stages["Planning Total Service"] = permit.planning_initial_service + permit.planning_recheck_service
    
    # Public Works - separate waiting and service
    if (
        permit.public_works_initial_waiting > 0
        or permit.public_works_initial_service > 0
        or permit.public_works_recheck_waiting > 0
        or permit.public_works_recheck_service > 0
    ):
        stages["Public Works Initial (Waiting)"] = permit.public_works_initial_waiting
        stages["Public Works Initial (Service)"] = permit.public_works_initial_service
        stages["Public Works Recheck (Waiting)"] = permit.public_works_recheck_waiting
        stages["Public Works Recheck (Service)"] = permit.public_works_recheck_service
        stages["Public Works Total Waiting"] = permit.public_works_initial_waiting + permit.public_works_recheck_waiting
        stages["Public Works Total Service"] = permit.public_works_initial_service + permit.public_works_recheck_service
    
    # Fire review - four buckets (initial waiting/service, recheck waiting/service)
    if (
        permit.fire_initial_waiting > 0
        or permit.fire_initial_service > 0
        or permit.fire_recheck_waiting > 0
        or permit.fire_recheck_service > 0
    ):
        stages["Fire Review Initial (Waiting)"] = permit.fire_initial_waiting
        stages["Fire Review Initial (Service)"] = permit.fire_initial_service
        stages["Fire Review Recheck (Waiting)"] = permit.fire_recheck_waiting
        stages["Fire Review Recheck (Service)"] = permit.fire_recheck_service
        stages["Fire Review Total Waiting"] = permit.fire_initial_waiting + permit.fire_recheck_waiting
        stages["Fire Review Total Service"] = permit.fire_initial_service + permit.fire_recheck_service
    
    # Public Health review - four buckets (initial waiting/service, recheck waiting/service)
    if (
        permit.public_health_initial_waiting > 0
        or permit.public_health_initial_service > 0
        or permit.public_health_recheck_waiting > 0
        or permit.public_health_recheck_service > 0
    ):
        stages["Public Health Initial (Waiting)"] = permit.public_health_initial_waiting
        stages["Public Health Initial (Service)"] = permit.public_health_initial_service
        stages["Public Health Recheck (Waiting)"] = permit.public_health_recheck_waiting
        stages["Public Health Recheck (Service)"] = permit.public_health_recheck_service
        stages["Public Health Total Waiting"] = permit.public_health_initial_waiting + permit.public_health_recheck_waiting
        stages["Public Health Total Service"] = permit.public_health_initial_service + permit.public_health_recheck_service
    
    # Agency Referrals permits - separate waiting and service
    if (permit.misc_request is not None and 
        permit.misc_service_start is not None and 
        permit.misc_end is not None):
        stages['Agency Referrals (Waiting)'] = permit.misc_service_start - permit.misc_request
        stages['Agency Referrals (Service)'] = permit.misc_end - permit.misc_service_start
    
    # Waiting time (gaps between stages)
    total_processing_time = permit.ready_for_construction - permit.created_at if permit.ready_for_construction else None
    if total_processing_time:
        accounted_time = sum(stages.values())
        waiting_time = total_processing_time - accounted_time
        if waiting_time > 0:
            stages['Other Waiting'] = waiting_time
    
    return stages


def calculate_step_waiting_service_totals(permit: Permit) -> dict:
    """
    Calculate total waiting and service times for each major process step,
    aggregating across initial/recheck where applicable.
    Returns a dict: {step_name: {"waiting": float, "service": float}}.
    """
    steps = {}

    # EPA Debris
    epa_waiting = permit.epa_debris_total_waiting
    epa_service = 0.0
    if permit.epa_debris_end is not None and permit.epa_debris_service_start is not None:
        epa_service = permit.epa_debris_end - permit.epa_debris_service_start
    if epa_waiting > 0 or epa_service > 0:
        steps["EPA Debris"] = {"waiting": epa_waiting, "service": epa_service}

    # USACE Debris
    usace_waiting = permit.usace_debris_total_waiting
    usace_service = 0.0
    if permit.usace_debris_end is not None and permit.usace_debris_service_start is not None:
        usace_service = permit.usace_debris_end - permit.usace_debris_service_start
    if usace_waiting > 0 or usace_service > 0:
        steps["USACE Debris"] = {"waiting": usace_waiting, "service": usace_service}

    # Authorization (service only)
    if permit.authorization_start is not None and permit.authorization_end is not None:
        auth_service = permit.authorization_end - permit.authorization_start
        if auth_service > 0:
            steps["Authorization"] = {"waiting": 0.0, "service": auth_service}

    # Plan preparation (service only)
    if permit.plan_prep_start is not None and permit.plan_prep_end is not None:
        prep_service = permit.plan_prep_end - permit.plan_prep_start
        if prep_service > 0:
            steps["Plan Preparation"] = {"waiting": 0.0, "service": prep_service}

    # Planning department (aggregate initial + recheck)
    planning_waiting = permit.planning_initial_waiting + permit.planning_recheck_waiting
    planning_service = permit.planning_initial_service + permit.planning_recheck_service
    if planning_waiting > 0 or planning_service > 0:
        steps["Planning"] = {"waiting": planning_waiting, "service": planning_service}

    # Agency Referrals permits
    misc_waiting = 0.0
    misc_service = 0.0
    if (
        permit.misc_request is not None
        and permit.misc_service_start is not None
        and permit.misc_end is not None
    ):
        misc_waiting = permit.misc_service_start - permit.misc_request
        misc_service = permit.misc_end - permit.misc_service_start
    if misc_waiting > 0 or misc_service > 0:
        steps["Agency Referrals"] = {"waiting": misc_waiting, "service": misc_service}

    # Public Works (aggregate initial + recheck)
    public_works_waiting = permit.public_works_total_waiting
    public_works_service = (
        permit.public_works_initial_service + permit.public_works_recheck_service
    )
    if public_works_waiting > 0 or public_works_service > 0:
        steps["Public Works"] = {
            "waiting": public_works_waiting,
            "service": public_works_service,
        }

    # Fire Review (aggregate initial + recheck)
    fire_waiting = permit.fire_initial_waiting + permit.fire_recheck_waiting
    fire_service = permit.fire_initial_service + permit.fire_recheck_service
    if fire_waiting > 0 or fire_service > 0:
        steps["Fire Review"] = {"waiting": fire_waiting, "service": fire_service}

    # Public Health Review (aggregate initial + recheck)
    ph_waiting = permit.public_health_initial_waiting + permit.public_health_recheck_waiting
    ph_service = permit.public_health_initial_service + permit.public_health_recheck_service
    if ph_waiting > 0 or ph_service > 0:
        steps["Public Health"] = {"waiting": ph_waiting, "service": ph_service}

    return steps


def plot_stacked_bar_chart(permits: List[Permit], max_permits: int = 50, figsize=(14, 8)):
    """
    Create a stacked bar chart showing time spent in each stage for each permit.
    
    Args:
        permits: List of Permit objects
        max_permits: Maximum number of permits to display (for readability)
        figsize: Figure size tuple
    """
    # Limit number of permits for readability
    display_permits = permits[:max_permits]
    
    # Define stage order and colors (waiting times are lighter, service times are darker)
    stage_order = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
        'Planning Initial (Waiting)',
        'Planning Initial (Service)',
        'Planning Recheck (Waiting)',
        'Planning Recheck (Service)',
        'Agency Referrals (Waiting)',
        'Agency Referrals (Service)',
        'Public Works Initial (Waiting)',
        'Public Works Initial (Service)',
        'Public Works Recheck (Waiting)',
        'Public Works Recheck (Service)',
        'Fire Review Initial (Waiting)',
        'Fire Review Initial (Service)',
        'Fire Review Recheck (Waiting)',
        'Fire Review Recheck (Service)',
        'Public Health Initial (Waiting)',
        'Public Health Initial (Service)',
        'Public Health Recheck (Waiting)',
        'Public Health Recheck (Service)',
        'Other Waiting',
    ]
    
    colors = {
        # Waiting times (lighter colors)
        'EPA Debris (Waiting)': '#FFB3B3',
        'USACE Debris (Waiting)': '#FFC2A6',
        'Planning Initial (Waiting)': '#FFD4B3',
        'Planning Recheck (Waiting)': '#FFE4C4',
        'Agency Referrals (Waiting)': '#D4A5A5',
        'Public Works Initial (Waiting)': '#C8E8D8',
        'Public Works Recheck (Waiting)': '#B7DCCB',
        'Fire Review Initial (Waiting)': '#FBF3B3',
        'Fire Review Recheck (Waiting)': '#F9E8A0',
        'Public Health Initial (Waiting)': '#E0C8E8',
        'Public Health Recheck (Waiting)': '#D4B5E0',
        'Other Waiting': '#E0E0E0',
        # Service times (darker colors)
        'EPA Debris (Service)': '#FF6B6B',
        'USACE Debris (Service)': '#FF8C5A',
        'Planning Initial (Service)': '#FFA07A',
        'Planning Recheck (Service)': '#FFB890',
        'Agency Referrals (Service)': '#C08080',
        'Public Works Initial (Service)': '#98D8C8',
        'Public Works Recheck (Service)': '#6FC2B0',
        'Fire Review Initial (Service)': '#F7DC6F',
        'Fire Review Recheck (Service)': '#F4D03F',
        'Public Health Initial (Service)': '#BB8FCE',
        'Public Health Recheck (Service)': '#9B6FB8',
        # Stages without waiting (service only)
        'Authorization': '#4ECDC4',
        'Plan Preparation': '#45B7D1',
    }
    
    # Prepare data
    permit_ids = [f"Permit {p.permit_id}" for p in display_permits]
    stage_data = {stage: [] for stage in stage_order}
    
    for permit in display_permits:
        stages = calculate_stage_times(permit)
        for stage in stage_order:
            stage_data[stage].append(stages.get(stage, 0))
    
    # Create stacked bar chart
    fig, ax = plt.subplots(figsize=figsize)
    
    bottom = np.zeros(len(display_permits))
    bars = []
    
    # Always include key stages even if they have zeros (for visibility)
    key_stages = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Planning Initial (Waiting)',
        'Planning Initial (Service)',
        'Public Works Initial (Waiting)',
        'Public Works Initial (Service)',
        'Fire Review Initial (Waiting)',
        'Fire Review Initial (Service)',
        'Authorization',
        'Plan Preparation',
    ]
    
    for stage in stage_order:
        values = stage_data[stage]
        # Plot if there are non-zero values OR if it's a key stage (to ensure visibility)
        if any(v > 0 for v in values) or stage in key_stages:
            bar = ax.bar(permit_ids, values, bottom=bottom, 
                        label=stage, color=colors[stage], alpha=0.8)
            bottom += values
            bars.append(bar)
    
    ax.set_xlabel('Permit ID', fontsize=12)
    ax.set_ylabel('Time (days)', fontsize=12)
    ax.set_title(f'Time Spent in Each Stage by Permit (showing {len(display_permits)} permits)', 
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(axis='y', alpha=0.3)
    
    # Rotate x-axis labels for readability
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    return fig, ax


def _gantt_intervals_from_permit(permit: Permit):
    """
    Extract (start, end, label, color, is_waiting) for each activity interval from a permit.
    Returns a list of tuples. Waiting and service are separate intervals where applicable.
    """
    intervals = []
    # Stages: (label, request_attr, service_start_attr, end_attr, waiting_color, service_color)
    stages_info = [
        ('EPA Debris', 'epa_debris_request', 'epa_debris_service_start', 'epa_debris_end', '#D9E1AD', '#98A83D'),
        ('USACE Debris', 'usace_debris_request', 'usace_debris_service_start', 'usace_debris_end', '#D9E1AD', '#98A83D'),
        ('Authorization', 'authorization_start', None, 'authorization_end', None, '#659DB2'),
        ('Plan Preparation', 'plan_prep_start', None, 'plan_prep_end', None, '#659DB2'),
        ('Planning', 'planning_request', 'planning_service_start', 'planning_end', '#F3DDA1', '#D9A71C'),
        ('Agency Referrals', 'misc_request', 'misc_service_start', 'misc_end', '#F3DDA1', '#D9A71C'),
        ('Public Works', 'public_works_request', 'public_works_service_start', 'public_works_end', '#F3DDA1', '#D9A71C'),
        ('Fire Review', 'fire_review_request', 'fire_review_service_start', 'fire_review_end', '#F3DDA1', '#D9A71C'),
        ('Public Health', 'public_health_request', 'public_health_service_start', 'public_health_end', '#F3DDA1', '#D9A71C'),
    ]
    for stage_name, request_attr, service_start_attr, end_attr, waiting_color, service_color in stages_info:
        request_time = getattr(permit, request_attr, None) if request_attr else None
        service_start_time = getattr(permit, service_start_attr, None) if service_start_attr else None
        end_time = getattr(permit, end_attr, None) if end_attr else None
        if request_time is None or end_time is None:
            continue
        if service_start_attr and service_start_time is not None:
            wait_dur = service_start_time - request_time
            if wait_dur > 0.001 and waiting_color:
                intervals.append((request_time, service_start_time, f'{stage_name} (waiting)', waiting_color, True))
            if end_time - service_start_time > 0 and service_color:
                intervals.append((service_start_time, end_time, f'{stage_name} (service)', service_color, False))
        else:
            if end_time - request_time > 0 and service_color:
                intervals.append((request_time, end_time, stage_name, service_color, False))
    return intervals


def _assign_lanes(intervals):
    """
    Assign each interval to a lane (row) so that overlapping intervals are on different lanes.
    intervals: list of (start, end, label, color, is_waiting).
    Returns: list of lanes; each lane is a list of (start, end, label, color, is_waiting).
    """
    # Sort by start time, then by end time
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    lanes = []  # lanes[i] = list of (start, end, label, color, is_waiting)
    for iv in sorted_intervals:
        start, end, label, color, is_waiting = iv
        placed = False
        for lane_idx, lane in enumerate(lanes):
            if not any(s < end and e > start for s, e, *_ in lane):
                lane.append(iv)
                placed = True
                break
        if not placed:
            lanes.append([iv])
    return lanes


def plot_gantt_single_permit(
    permit: Permit,
    figsize=(14, 5),
    title: str = None,
):
    """
    Create a Gantt chart for a single permit with parallel activities on separate rows
    so that overlapping activities are visible on different bars.

    Args:
        permit: Single Permit object
        figsize: Figure size tuple
        title: Optional chart title (default: "Permit {id} (Segment {segment})")
    """
    intervals = _gantt_intervals_from_permit(permit)
    if not intervals:
        print("No activity intervals found for this permit.")
        return None, None

    fig, ax = plt.subplots(figsize=figsize)

    # Define the four fixed rows the user requested
    # Six fixed rows in logical order:
    # 1) Debris removal
    # 2) Authorization & Plan Preparation
    # 3) Planning & Zoning (Planning + Agency Referrals)
    # 4) Public Works
    # 5) Fire
    # 6) Public Health
    row_definitions = [
        ("Debris removal", ["EPA Debris", "USACE Debris"]),
        ("Authorization & Plan preparation", ["Authorization", "Plan Preparation"]),
        ("Permit reviews", ["Planning", "Agency Referrals", "Public Works"]),
        ("Fire Review", ["Fire Review"])
    ]
    n_rows = len(row_definitions)
    y_positions = list(range(n_rows))
    # We'll place Debris at the top, then Planning/Agency Referrals/Public Works,
    # then Fire Review, and Public Health at the bottom.
    row_labels = [""] * n_rows

    # Map base stage name -> logical row index, and build labels by display index
    stage_to_row = {}
    for idx, (row_name, stages) in enumerate(row_definitions):
        display_y = n_rows - 1 - idx  # invert so first definition is topmost
        row_labels[display_y] = row_name
        for s in stages:
            stage_to_row[s] = idx

    bar_height = 0.65

    # Define canonical order for legend (match stages_info from _gantt_intervals_from_permit)
    legend_order = [
        ('Debris removal (waiting)', True), ('Debris removal (service)', False),
        ('Authorization & Plan Preparation', False),
        ('Permit reviews (waiting)', True), ('Permit reviews (service)', False),
    ]
    seen = set()  # (label, is_waiting)
    label_to_color = {}  # (label, is_waiting) -> color
    for start, end, label, color, is_waiting in intervals:
        key = (label, is_waiting)
        if key not in seen:
            seen.add(key)
            label_to_color[key] = color

    # Plot each interval on the appropriate fixed row
    for start, end, label, color, is_waiting in intervals:
        duration = end - start
        if duration <= 0:
            continue
        base = label.replace(" (waiting)", "").replace(" (service)", "")
        logical_row = stage_to_row.get(base)
        if logical_row is None:
            # Skip stages that are not in the four requested rows
            continue
        # Map logical row (0 = Debris, 1 = Planning/Agency Referrals/PW, 2 = Fire, 3 = Public Health)
        # to display coordinate so Debris is at the top.
        y_pos = n_rows - 1 - logical_row
        hatch = "///" if is_waiting else None
        alpha = 0.6 if is_waiting else 0.9
        ax.barh(
            y_pos,
            duration,
            left=start,
            height=bar_height,
            color=color,
            alpha=alpha,
            edgecolor="black",
            linewidth=0.5,
            hatch=hatch,
        )

    # Build legend in canonical order, only for labels that appear in this permit
    legend_handles = []
    for label, is_waiting in legend_order:
        key = (label, is_waiting)
        if key not in label_to_color:
            continue
        color = label_to_color[key]
        hatch = "///" if is_waiting else None
        alpha = 0.6 if is_waiting else 0.9
        patch = mpatches.Patch(
            facecolor=color,
            alpha=alpha,
            edgecolor="black",
            linewidth=0.5,
            hatch=hatch,
            label=label,
        )
        legend_handles.append(patch)
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=15)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(row_labels, fontsize=16)
    ax.set_xlabel('Time (days)', fontsize=18)
    if title is None:
        title = f"Gantt: Permit {permit.permit_id} ({permit.segment.name})"
    ax.set_title(title, fontsize=20, fontweight='bold')
    ax.tick_params(axis='x', labelsize=15)
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    return fig, ax


def plot_gantt_three_random_permits(
    permits: List[Permit],
    n_permits: int = 3,
    segment_value: Optional[int] = None,
    random_seed: Optional[int] = None,
    figsize=(14, 8),
):
    """
    Plot a Gantt chart showing multiple random permits in the same chart.

    Args:
        permits: List of completed Permit objects
        n_permits: Number of permits to show (default 3)
        segment_value: If provided, only pick permits from this segment (e.g. 4 = CUSTOM_NON_LIKE)
        random_seed: Optional seed for reproducible random choice
        figsize: Figure size tuple
    """
    from permit_simulation import Segment

    if segment_value is not None:
        try:
            segment = Segment(segment_value)
            pool = [p for p in permits if p.segment == segment]
        except ValueError:
            pool = list(permits)
    else:
        pool = list(permits)

    if len(pool) < n_permits:
        n_permits = len(pool)
    if not pool:
        print("No permits available to plot.")
        return None, None

    rng = np.random.default_rng(random_seed)
    selected = rng.choice(pool, size=min(n_permits, len(pool)), replace=False)

    row_definitions = [
        ("Debris removal", ["EPA Debris", "USACE Debris"]),
        ("Authorization & Plan preparation", ["Authorization", "Plan Preparation"]),
        ("Permit reviews", ["Planning", "Agency Referrals", "Public Works"]),
        ("Fire Review", ["Fire Review"]),
    ]
    n_rows_per_permit = len(row_definitions)
    stage_to_row = {}
    for idx, (_, stages) in enumerate(row_definitions):
        for s in stages:
            stage_to_row[s] = idx

    all_row_labels = []
    for perm in selected:
        for row_name, _ in row_definitions:
            all_row_labels.append(f"Permit {perm.permit_id} – {row_name}")

    fig, ax = plt.subplots(figsize=figsize)
    bar_height = 0.65

    # Map raw stage names to grouped legend labels (for waiting vs active)
    legend_group = {
        "EPA Debris": "Debris removal",
        "USACE Debris": "Debris removal",
        "Authorization": "Authorization & Plan preparation",
        "Plan Preparation": "Authorization & Plan preparation",
        "Planning": "Permit reviews",
        "Agency Referrals": "Permit reviews",
        "Public Works": "Permit reviews",
    }

    legend_order = [
        ("Debris removal (waiting)", True), ("Debris removal (active)", False),
        ("Authorization & Plan preparation (waiting)", True), ("Authorization & Plan preparation (active)", False),
        ("Permit reviews (waiting)", True), ("Permit reviews (active)", False),
    ]
    label_to_color = {}
    seen_legend = set()

    for perm_idx, permit in enumerate(selected):
        intervals = _gantt_intervals_from_permit(permit)
        y_offset = perm_idx * n_rows_per_permit

        for start, end, label, color, is_waiting in intervals:
            base = label.replace(" (waiting)", "").replace(" (service)", "")
            group = legend_group.get(base)
            if group is None:
                continue
            suffix = "(waiting)" if is_waiting else "(active)"
            legend_key = (f"{group} {suffix}", is_waiting)
            if legend_key not in seen_legend:
                seen_legend.add(legend_key)
                label_to_color[legend_key] = color

        for start, end, label, color, is_waiting in intervals:
            duration = end - start
            if duration <= 0:
                continue
            base = label.replace(" (waiting)", "").replace(" (service)", "")
            logical_row = stage_to_row.get(base)
            if logical_row is None:
                continue
            y_pos = y_offset + logical_row
            hatch = "///" if is_waiting else None
            alpha = 0.6 if is_waiting else 0.9
            ax.barh(
                y_pos,
                duration,
                left=start,
                height=bar_height,
                color=color,
                alpha=alpha,
                edgecolor="black",
                linewidth=0.5,
                hatch=hatch,
            )

    # Horizontal dashed lines separating each permit
    for i in range(1, n_permits):
        y_sep = i * n_rows_per_permit - 0.5
        ax.axhline(y=y_sep, linestyle='--', color='gray', alpha=0.7, linewidth=1.5)

    legend_handles = []
    for label, is_waiting in legend_order:
        key = (label, is_waiting)
        if key not in label_to_color:
            continue
        color = label_to_color[key]
        hatch = "///" if is_waiting else None
        alpha = 0.6 if is_waiting else 0.9
        legend_handles.append(mpatches.Patch(
            facecolor=color, alpha=alpha, edgecolor="black", linewidth=0.5,
            hatch=hatch, label=label,
        ))
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=15)

    n_total_rows = n_permits * n_rows_per_permit
    ax.set_yticks(range(n_total_rows))
    ax.set_yticklabels([])
    ax.set_xlabel('Time (days)', fontsize=18)
    ax.tick_params(axis='x', labelsize=15)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    plt.tight_layout()
    return fig, ax


def plot_gantt_one_random_permit_segment(
    permits: List[Permit],
    segment_value: int = 4,
    random_seed: Optional[int] = None,
    figsize=(14, 5),
):
    """
    Plot a Gantt chart for one random permit in the given segment.
    Segment 4 = CUSTOM_NON_LIKE. Parallel activities are shown on separate rows.

    Args:
        permits: List of completed Permit objects
        segment_value: Segment enum value (default 4 = CUSTOM_NON_LIKE)
        random_seed: Optional seed for reproducible random choice
        figsize: Figure size tuple
    """
    from permit_simulation import Segment
    try:
        segment = Segment(segment_value)
    except ValueError:
        segment = Segment.CUSTOM_NON_LIKE
    segment_permits = [p for p in permits if p.segment == segment]
    if not segment_permits:
        print(f"No permits found for segment {segment.name} (value {segment_value}).")
        return None, None
    rng = np.random.default_rng(random_seed)
    permit = rng.choice(segment_permits)
    return plot_gantt_single_permit(permit, figsize=figsize)


def plot_average_time_by_stage(permits: List[Permit], figsize=(10, 6)):
    """
    Create a bar chart showing average time spent in each stage across all permits.
    
    Args:
        permits: List of Permit objects
        figsize: Figure size tuple
    """
    # Stage order will be determined dynamically from calculate_stage_times
    # Colors for all possible stages
    colors = {
        # Waiting times (lighter colors)
        'EPA Debris (Waiting)': '#FFB3B3',
        'USACE Debris (Waiting)': '#FFC2A6',
        'Planning (Waiting)': '#FFD4B3',
        'Public Works Initial (Waiting)': '#C8E8D8',
        'Public Works Recheck (Waiting)': '#B7DCCB',
        'Fire Review (Waiting)': '#FBF3B3',
        'Public Health (Waiting)': '#E0C8E8',
        'Agency Referrals (Waiting)': '#D4A5A5',
        'Other Waiting': '#E0E0E0',
        # Service times (darker colors)
        'EPA Debris (Service)': '#FF6B6B',
        'USACE Debris (Service)': '#FF8C5A',
        'Planning (Service)': '#FFA07A',
        'Public Works Initial (Service)': '#98D8C8',
        'Public Works Recheck (Service)': '#6FC2B0',
        'Fire Review (Service)': '#F7DC6F',
        'Public Health (Service)': '#BB8FCE',
        'Agency Referrals (Service)': '#C08080',
        # Stages without waiting (service only)
        'Authorization': '#4ECDC4',
        'Plan Preparation': '#45B7D1',
    }
    
    # Calculate averages - dynamically determine stages from data
    stage_totals = {}
    
    for permit in permits:
        stages = calculate_stage_times(permit)
        for stage, duration in stages.items():
            if stage not in stage_totals:
                stage_totals[stage] = []
            stage_totals[stage].append(duration)
    
    stage_averages = {stage: np.mean(values) if values else 0 
                      for stage, values in stage_totals.items()}
    
    # Filter out stages with zero average, but always include key stages
    key_stages = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
    ]
    stage_averages = {k: v for k, v in stage_averages.items() if v > 0 or k in key_stages}
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=figsize)
    
    # Sort stages: waiting times first, then service times, then others
    def sort_key(stage):
        if '(Waiting)' in stage:
            return (0, stage)
        elif '(Service)' in stage:
            return (1, stage)
        else:
            return (2, stage)
    
    stages = sorted(stage_averages.keys(), key=sort_key)
    averages = [stage_averages[s] for s in stages]
    bar_colors = [colors.get(s, '#D3D3D3') for s in stages]
    
    bars = ax.bar(stages, averages, color=bar_colors, alpha=0.8, edgecolor='black')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Process Stage', fontsize=12)
    ax.set_ylabel('Average Time (days)', fontsize=12)
    ax.set_title('Average Time Spent in Each Process Stage', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    return fig, ax


def plot_time_by_segment(permits: List[Permit], figsize=(12, 6)):
    """
    Create a grouped bar chart showing average time per stage by permit segment.
    
    Args:
        permits: List of Permit objects
        figsize: Figure size tuple
    """
    from permit_simulation import Segment
    
    # Group permits by segment
    segment_permits = {segment: [] for segment in Segment}
    for permit in permits:
        segment_permits[permit.segment].append(permit)
    
    # Calculate averages per segment - collect all stages dynamically
    segment_data = {}
    all_stages = set()
    
    for segment, seg_permits in segment_permits.items():
        if not seg_permits:
            continue
        
        # Collect all stages that appear in the data
        stage_totals = {}
        for permit in seg_permits:
            stages = calculate_stage_times(permit)
            for stage_name, duration in stages.items():
                all_stages.add(stage_name)
                if stage_name not in stage_totals:
                    stage_totals[stage_name] = []
                stage_totals[stage_name].append(duration)
        
        segment_data[segment] = {
            stage: np.mean(values) if values else 0
            for stage, values in stage_totals.items()
        }
    
    # Define preferred order for display
    preferred_order = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
        'Planning Initial (Waiting)',
        'Planning Initial (Service)',
        'Planning Recheck (Waiting)',
        'Planning Recheck (Service)',
        'Public Works Initial (Waiting)',
        'Public Works Initial (Service)',
        'Public Works Recheck (Waiting)',
        'Public Works Recheck (Service)',
        'Fire Review Initial (Waiting)',
        'Fire Review Initial (Service)',
        'Fire Review Recheck (Waiting)',
        'Fire Review Recheck (Service)',
        'Public Health Initial (Waiting)',
        'Public Health Initial (Service)',
        'Public Health Recheck (Waiting)',
        'Public Health Recheck (Service)',
        'Agency Referrals (Waiting)',
        'Agency Referrals (Service)',
    ]
    
    # Filter to only stages with data, maintaining preferred order
    # Always include key stages even if they don't appear in all_stages (for consistency)
    key_stages = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
    ]
    stage_order = [s for s in preferred_order if s in all_stages or s in key_stages]
    # Add any remaining stages not in preferred order
    for stage in sorted(all_stages):
        if stage not in stage_order:
            stage_order.append(stage)
    
    if not stage_order:
        print("Warning: No stage data found for any segment")
        return None, None
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(stage_order))
    width = 0.15
    multiplier = 0
    
    colors_map = {
        Segment.PRE_APPROVED_LIKE: '#2E7D32',
        Segment.PRE_APPROVED_NON_LIKE: '#81C784',
        Segment.CUSTOM_LIKE: '#1565C0',
        Segment.CUSTOM_NON_LIKE: '#90CAF9',
        Segment.SELF_CERT_LIKE: '#EF6C00',
        Segment.SELF_CERT_NON_LIKE: '#FFB74D',
    }
    
    for segment, data in segment_data.items():
        if not any(data.values()):  # Skip if no data
            continue
        
        offset = width * multiplier
        values = [data.get(stage, 0) for stage in stage_order]
        bars = ax.bar(x + offset, values, width, label=segment.name, 
                     color=colors_map.get(segment, '#D3D3D3'), alpha=0.8)
        multiplier += 1
    
    ax.set_xlabel('Process Stage', fontsize=12)
    ax.set_ylabel('Average Time (days)', fontsize=12)
    ax.set_title('Average Time per Stage by Permit Segment', fontsize=14, fontweight='bold')
    ax.set_xticks(x + width * (multiplier - 1) / 2 if multiplier > 0 else x)
    ax.set_xticklabels(stage_order, rotation=45, ha='right')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    return fig, ax


def plot_time_by_segment_like_for_like(permits: List[Permit], figsize=(12, 6)):
    """
    Create a grouped bar chart showing average time per stage for Like-for-like segments only.
    Includes: PRE_APPROVED_LIKE, CUSTOM_LIKE, SELF_CERT_LIKE
    
    Args:
        permits: List of Permit objects
        figsize: Figure size tuple
    """
    from permit_simulation import Segment
    
    # Filter to only like-for-like segments
    like_for_like_segments = [Segment.PRE_APPROVED_LIKE, Segment.CUSTOM_LIKE, Segment.SELF_CERT_LIKE]
    filtered_permits = [p for p in permits if p.segment in like_for_like_segments]
    
    if not filtered_permits:
        print("Warning: No like-for-like permits found")
        return None, None
    
    # Group permits by segment
    segment_permits = {segment: [] for segment in like_for_like_segments}
    for permit in filtered_permits:
        segment_permits[permit.segment].append(permit)
    
    # Calculate averages per segment - collect all stages dynamically
    segment_data = {}
    all_stages = set()
    
    for segment, seg_permits in segment_permits.items():
        if not seg_permits:
            continue
        
        # Collect all stages that appear in the data
        stage_totals = {}
        for permit in seg_permits:
            stages = calculate_stage_times(permit)
            for stage_name, duration in stages.items():
                all_stages.add(stage_name)
                if stage_name not in stage_totals:
                    stage_totals[stage_name] = []
                stage_totals[stage_name].append(duration)
        
        segment_data[segment] = {
            stage: np.mean(values) if values else 0
            for stage, values in stage_totals.items()
        }
    
    # Define preferred order for display
    preferred_order = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
        'Planning Initial (Waiting)',
        'Planning Initial (Service)',
        'Planning Recheck (Waiting)',
        'Planning Recheck (Service)',
        'Public Works Initial (Waiting)',
        'Public Works Initial (Service)',
        'Public Works Recheck (Waiting)',
        'Public Works Recheck (Service)',
        'Fire Review Initial (Waiting)',
        'Fire Review Initial (Service)',
        'Fire Review Recheck (Waiting)',
        'Fire Review Recheck (Service)',
        'Public Health Initial (Waiting)',
        'Public Health Initial (Service)',
        'Public Health Recheck (Waiting)',
        'Public Health Recheck (Service)',
        'Agency Referrals (Waiting)',
        'Agency Referrals (Service)',
    ]
    
    # Filter to only stages with data, maintaining preferred order
    key_stages = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
    ]
    stage_order = [s for s in preferred_order if s in all_stages or s in key_stages]
    # Add any remaining stages not in preferred order
    for stage in sorted(all_stages):
        if stage not in stage_order:
            stage_order.append(stage)
    
    if not stage_order:
        print("Warning: No stage data found for any segment")
        return None, None
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(stage_order))
    width = 0.25
    multiplier = 0
    
    colors_map = {
        Segment.PRE_APPROVED_LIKE: '#2E7D32',
        Segment.CUSTOM_LIKE: '#1565C0',
        Segment.SELF_CERT_LIKE: '#EF6C00',
    }
    
    for segment in like_for_like_segments:
        if segment not in segment_data or not any(segment_data[segment].values()):
            continue
        
        data = segment_data[segment]
        offset = width * multiplier
        values = [data.get(stage, 0) for stage in stage_order]
        bars = ax.bar(x + offset, values, width, label=segment.name, 
                     color=colors_map.get(segment, '#D3D3D3'), alpha=0.8)
        multiplier += 1
    
    ax.set_xlabel('Process Stage', fontsize=12)
    ax.set_ylabel('Average Time (days)', fontsize=12)
    ax.set_title('Average Time per Stage by Permit Segment (Like-for-like Only)', fontsize=14, fontweight='bold')
    ax.set_xticks(x + width * (multiplier - 1) / 2 if multiplier > 0 else x)
    ax.set_xticklabels(stage_order, rotation=45, ha='right')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    return fig, ax


def plot_time_by_segment_non_like_for_like(permits: List[Permit], figsize=(12, 6)):
    """
    Create a grouped bar chart showing average time per stage for Non-like-for-like segments only.
    Includes: PRE_APPROVED_NON_LIKE, CUSTOM_NON_LIKE, SELF_CERT_NON_LIKE
    
    Args:
        permits: List of Permit objects
        figsize: Figure size tuple
    """
    from permit_simulation import Segment
    
    # Filter to only non-like-for-like segments
    non_like_for_like_segments = [Segment.PRE_APPROVED_NON_LIKE, Segment.CUSTOM_NON_LIKE, Segment.SELF_CERT_NON_LIKE]
    filtered_permits = [p for p in permits if p.segment in non_like_for_like_segments]
    
    if not filtered_permits:
        print("Warning: No non-like-for-like permits found")
        return None, None
    
    # Group permits by segment
    segment_permits = {segment: [] for segment in non_like_for_like_segments}
    for permit in filtered_permits:
        segment_permits[permit.segment].append(permit)
    
    # Calculate averages per segment - collect all stages dynamically
    segment_data = {}
    all_stages = set()
    
    for segment, seg_permits in segment_permits.items():
        if not seg_permits:
            continue
        
        # Collect all stages that appear in the data
        stage_totals = {}
        for permit in seg_permits:
            stages = calculate_stage_times(permit)
            for stage_name, duration in stages.items():
                all_stages.add(stage_name)
                if stage_name not in stage_totals:
                    stage_totals[stage_name] = []
                stage_totals[stage_name].append(duration)
        
        segment_data[segment] = {
            stage: np.mean(values) if values else 0
            for stage, values in stage_totals.items()
        }
    
    # Define preferred order for display
    preferred_order = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
        'Planning Initial (Waiting)',
        'Planning Initial (Service)',
        'Planning Recheck (Waiting)',
        'Planning Recheck (Service)',
        'Public Works Initial (Waiting)',
        'Public Works Initial (Service)',
        'Public Works Recheck (Waiting)',
        'Public Works Recheck (Service)',
        'Fire Review Initial (Waiting)',
        'Fire Review Initial (Service)',
        'Fire Review Recheck (Waiting)',
        'Fire Review Recheck (Service)',
        'Public Health Initial (Waiting)',
        'Public Health Initial (Service)',
        'Public Health Recheck (Waiting)',
        'Public Health Recheck (Service)',
        'Agency Referrals (Waiting)',
        'Agency Referrals (Service)',
    ]
    
    # Filter to only stages with data, maintaining preferred order
    key_stages = [
        'EPA Debris (Waiting)',
        'EPA Debris (Service)',
        'USACE Debris (Waiting)',
        'USACE Debris (Service)',
        'Authorization',
        'Plan Preparation',
    ]
    stage_order = [s for s in preferred_order if s in all_stages or s in key_stages]
    # Add any remaining stages not in preferred order
    for stage in sorted(all_stages):
        if stage not in stage_order:
            stage_order.append(stage)
    
    if not stage_order:
        print("Warning: No stage data found for any segment")
        return None, None
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(stage_order))
    width = 0.25
    multiplier = 0
    
    colors_map = {
        Segment.PRE_APPROVED_NON_LIKE: '#81C784',
        Segment.CUSTOM_NON_LIKE: '#90CAF9',
        Segment.SELF_CERT_NON_LIKE: '#FFB74D',
    }
    
    for segment in non_like_for_like_segments:
        if segment not in segment_data or not any(segment_data[segment].values()):
            continue
        
        data = segment_data[segment]
        offset = width * multiplier
        values = [data.get(stage, 0) for stage in stage_order]
        bars = ax.bar(x + offset, values, width, label=segment.name, 
                     color=colors_map.get(segment, '#D3D3D3'), alpha=0.8)
        multiplier += 1
    
    ax.set_xlabel('Process Stage', fontsize=12)
    ax.set_ylabel('Average Time (days)', fontsize=12)
    ax.set_title('Average Time per Stage by Permit Segment (Non-like-for-like Only)', fontsize=14, fontweight='bold')
    ax.set_xticks(x + width * (multiplier - 1) / 2 if multiplier > 0 else x)
    ax.set_xticklabels(stage_order, rotation=45, ha='right')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    return fig, ax


def plot_total_time_by_segment(permits: List[Permit], figsize=(10, 6), show_boxplot=True):
    """
    Create a visualization of the total time from disaster to construction start for each segment.
    Can be a box plot (default) or a bar chart with error bars.
    
    Args:
        permits: List of Permit objects
        figsize: Figure size tuple
        show_boxplot: If True, show box plot; if False, show bar chart with error bars
    """
    from permit_simulation import Segment
    
    segment_times = {segment: [] for segment in Segment}
    for permit in permits:
        if permit.ready_for_construction is not None and permit.created_at is not None:
            total_time = permit.ready_for_construction - permit.created_at
            segment_times[permit.segment].append(total_time)
    
    # Filter out segments with no data
    segment_data = {s: times for s, times in segment_times.items() if times}
    
    if not segment_data:
        print("No data to plot for total time by segment.")
        return None, None
    
    segments = list(segment_data.keys())
    labels = [s.name for s in segments]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if show_boxplot:
        data = [segment_data[s] for s in segments]
        bp = ax.boxplot(data, patch_artist=True, vert=True, showmeans=True, 
                        medianprops={'color': 'red'}, meanprops={'marker': 'o', 'markeredgecolor': 'black', 'markerfacecolor': 'green'})
        
        # Add colors to box plots
        colors = ['#2E7D32', '#81C784', '#1565C0', '#90CAF9', '#EF6C00', '#FFB74D']
        for patch, color in zip(bp['boxes'], colors[:len(segments)]):
            patch.set_facecolor(color)
        
        # Add sample size (n)
        for i, s in enumerate(segments):
            count = len(segment_data[s])
            y_pos = np.median(data[i])  # Position near the median
            ax.text(i + 1, np.max(data[i]) + 0.05 * (np.max(data[i]) - np.min(data[i])), f'n={count}',
                    horizontalalignment='center', verticalalignment='bottom', fontsize=9, color='gray')
        
        # Add dashed reference lines for 1 year and 2 years
        one_year = 365
        two_years = 730
        ax.axhline(y=one_year, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label='1 Year')
        ax.axhline(y=two_years, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label='2 Years')
        
        ax.set_ylabel('Total Time (days)', fontsize=12)
        ax.set_title('Total Time from Disaster to Construction Start by Segment (Box Plot)', fontsize=14, fontweight='bold')
        ax.set_xticks(np.arange(1, len(segments) + 1))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
    else:
        means = [np.mean(segment_data[s]) for s in segments]
        stds = [np.std(segment_data[s]) for s in segments]
        
        ax.bar(labels, means, yerr=stds, capsize=5, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#BB8FCE'][:len(segments)], alpha=0.8)
        ax.set_ylabel('Average Total Time (days)', fontsize=12)
        ax.set_title('Average Total Time from Disaster to Construction Start by Segment', fontsize=14, fontweight='bold')
        ax.set_xticks(np.arange(len(segments)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    return fig, ax


def plot_total_time_by_segment_quartiles(permits: List[Permit], figsize=(10, 6)):
    """
    Create a bar chart of total time from disaster to construction start by segment,
    showing median with 25th and 75th percentile as error bars.

    Args:
        permits: List of Permit objects
        figsize: Figure size tuple
    """
    from permit_simulation import Segment

    segment_times = {segment: [] for segment in Segment}
    for permit in permits:
        if permit.ready_for_construction is not None and permit.created_at is not None:
            total_time = permit.ready_for_construction - permit.created_at
            segment_times[permit.segment].append(total_time)

    segment_data = {s: times for s, times in segment_times.items() if times}
    if not segment_data:
        print("No data to plot for total time by segment.")
        return None, None

    segments = list(segment_data.keys())
    labels = ["Pre-approved like", "Pre-approved non-like", "Custom like", "Custom non-like", "Self-certified like", "Self-certified non-like"]

    medians = [np.median(segment_data[s]) for s in segments]
    p25 = [np.percentile(segment_data[s], 25) for s in segments]
    p75 = [np.percentile(segment_data[s], 75) for s in segments]

    # Asymmetric error bars: lower = median - p25, upper = p75 - median
    yerr_lower = [medians[i] - p25[i] for i in range(len(segments))]
    yerr_upper = [p75[i] - medians[i] for i in range(len(segments))]
    yerr = [yerr_lower, yerr_upper]

    fig, ax = plt.subplots(figsize=figsize)
    colors = ['#2E7D32', '#81C784', '#1565C0', '#90CAF9', '#EF6C00', '#FFB74D']
    x = np.arange(len(segments))
    bars = ax.bar(x, medians, yerr=yerr, capsize=5, color=colors[:len(segments)], alpha=0.8, edgecolor='black')

    # Add sample size (n)
    for i, s in enumerate(segments):
        count = len(segment_data[s])
        ax.text(i, p75[i] + 0.02 * (p75[i] - p25[i]) if p75[i] != p25[i] else medians[i] + 5, f'n={count}',
                horizontalalignment='center', verticalalignment='bottom', fontsize=9, color='gray')

    one_year = 365
    ax.axhline(y=one_year, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.text(1.02, one_year, ' 1 Year', transform=ax.get_yaxis_transform(), ha='left', va='center',
            fontsize=10, color='gray', alpha=0.8)

    ax.set_ylabel('Total Time (days)', fontsize=12)
    ax.set_title('Total Time from Disaster to Construction Start by Segment (Median, 25th–75th percentiles)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    return fig, ax


def plot_median_total_time_by_process(
    permits_by_process: dict,
    figsize=(12, 6),
):
    """
    Create a grouped bar chart of median total time (disaster to construction start)
    by segment for Standard, Sequential, and Parallel process.

    Args:
        permits_by_process: Dict mapping process name (e.g. "Standard", "Sequential", "Parallel")
            to list of completed Permit objects.
        figsize: Figure size tuple.
    """
    from permit_simulation import Segment

    segment_order = [
        Segment.PRE_APPROVED_LIKE,
        Segment.PRE_APPROVED_NON_LIKE,
        Segment.CUSTOM_LIKE,
        Segment.CUSTOM_NON_LIKE,
        Segment.SELF_CERT_LIKE,
        Segment.SELF_CERT_NON_LIKE,
    ]

    # Build median total time per (process, segment)
    # permits_by_process: {"Standard": [permits], "Sequential": [permits], "Parallel": [permits]}
    process_names = list(permits_by_process.keys())
    medians = {pname: {} for pname in process_names}

    for pname, permits in permits_by_process.items():
        for seg in segment_order:
            times = [
                p.ready_for_construction - p.created_at
                for p in permits
                if p.segment == seg and p.ready_for_construction is not None
            ]
            medians[pname][seg] = float(np.median(times)) if times else np.nan

    # Only include segments that have at least one non-NaN median across processes
    segments_to_plot = [
        seg for seg in segment_order
        if any(not np.isnan(medians[p].get(seg, np.nan)) for p in process_names)
    ]
    if not segments_to_plot:
        print("No segment data to plot.")
        return None, None

    labels = [s.name for s in segments_to_plot]
    x = np.arange(len(labels))
    width = 0.25
    n_processes = len(process_names)

    fig, ax = plt.subplots(figsize=figsize)

    colors = {"Standard": "#1565C0", "Sequential": "#2E7D32", "Parallel": "#EF6C00"}
    for i, pname in enumerate(process_names):
        offset = width * (i - (n_processes - 1) / 2)
        values = [medians[pname].get(seg, np.nan) for seg in segments_to_plot]
        values = [v if not np.isnan(v) else 0 for v in values]
        color = colors.get(pname, "#888888")
        ax.bar(x + offset, values, width, label=pname, color=color, alpha=0.85, edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Median total time (days)", fontsize=12)
    ax.set_xlabel("Segment", fontsize=12)
    ax.set_title("Median total time from disaster to construction start by segment", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    return fig, ax


def plot_average_waiting_and_service_by_step(
    permits: List[Permit], figsize=(10, 6)
):
    """
    Create a bar chart showing average total waiting vs service time for each
    major process step (EPA, USACE, Planning, Public Works, etc.), with
    initial and recheck times aggregated together.
    """
    if not permits:
        print("No permits provided for waiting/service by step chart.")
        return None, None

    # Accumulate per-step waiting and service times across permits
    step_waiting = {}
    step_service = {}

    for permit in permits:
        totals = calculate_step_waiting_service_totals(permit)
        for step_name, values in totals.items():
            step_waiting.setdefault(step_name, []).append(values["waiting"])
            step_service.setdefault(step_name, []).append(values["service"])

    if not step_waiting:
        print("No step data found for waiting/service chart.")
        return None, None

    # Define preferred order to match process flow
    preferred_order = [
        "EPA Debris",
        "USACE Debris",
        "Authorization",
        "Plan Preparation",
        "Planning",
        "Agency Referrals",
        "Public Works",
        "Fire Review",
        "Public Health",
    ]

    steps = [s for s in preferred_order if s in step_waiting]
    # Add any remaining steps not in preferred order
    for step in sorted(step_waiting.keys()):
        if step not in steps:
            steps.append(step)

    waiting_means = [np.mean(step_waiting[s]) for s in steps]
    service_means = [np.mean(step_service.get(s, [0.0])) for s in steps]

    x = np.arange(len(steps))
    width = 0.35

    fig, ax = plt.subplots(figsize=figsize)

    bars_wait = ax.bar(
        x - width / 2,
        waiting_means,
        width,
        label="Waiting",
        color="#BDBDBD",
        edgecolor="black",
    )
    bars_service = ax.bar(
        x + width / 2,
        service_means,
        width,
        label="Service",
        color="#81C784",
        edgecolor="black",
    )

    # Add value labels
    for bar in list(bars_wait) + list(bars_service):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xlabel("Process Step", fontsize=12)
    ax.set_ylabel("Average Time (days)", fontsize=12)
    ax.set_title(
        "Average Total Waiting vs Service Time by Process Step",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(steps, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    return fig, ax


def visualize_all(permits: List[Permit], save_prefix: str = None, show: bool = True):
    """
    Create all visualizations and optionally save them.
    
    Args:
        permits: List of Permit objects
        save_prefix: If provided, save figures with this prefix
        show: If True, display figures interactively
    """
    print(f"Creating visualizations for {len(permits)} permits...")
    
    # 1. Stacked bar chart
    print("  Creating stacked bar chart...")
    fig1, _ = plot_stacked_bar_chart(permits, max_permits=50)
    if save_prefix:
        fig1.savefig(f"{save_prefix}_stacked_bar.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_stacked_bar.png")
    
    
    # 2. Average time by stage
    print("  Creating average time by stage chart...")
    fig2, _ = plot_average_time_by_stage(permits)
    if save_prefix:
        fig2.savefig(f"{save_prefix}_average_by_stage.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_average_by_stage.png")
    
    # 3. Time by segment (all segments)
    print("  Creating time by segment chart...")
    fig3, _ = plot_time_by_segment(permits)
    if save_prefix:
        fig3.savefig(f"{save_prefix}_by_segment.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_by_segment.png")
    
    # 4. Time by segment - Like-for-like only
    print("  Creating time by segment chart (Like-for-like only)...")
    fig4, _ = plot_time_by_segment_like_for_like(permits)
    if save_prefix and fig4:
        fig4.savefig(f"{save_prefix}_by_segment_like_for_like.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_by_segment_like_for_like.png")
    
    # 5. Time by segment - Non-like-for-like only
    print("  Creating time by segment chart (Non-like-for-like only)...")
    fig5, _ = plot_time_by_segment_non_like_for_like(permits)
    if save_prefix and fig5:
        fig5.savefig(f"{save_prefix}_by_segment_non_like_for_like.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_by_segment_non_like_for_like.png")
    
    # 6. Total time by segment (box plot)
    print("  Creating total time by segment chart (box plot)...")
    fig6, _ = plot_total_time_by_segment(permits)
    if save_prefix and fig6:
        fig6.savefig(f"{save_prefix}_total_time_by_segment.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_total_time_by_segment.png")

    # 6. Average total waiting vs service by step
    print("  Creating waiting vs service by step chart...")
    fig7, _ = plot_average_waiting_and_service_by_step(permits)
    if save_prefix and fig7:
        fig7.savefig(f"{save_prefix}_waiting_service_by_step.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_waiting_service_by_step.png")
    
    if show:
        plt.show()
    print("Visualizations complete!")


if __name__ == "__main__":
    # Example usage
    from run_simulation import run_simulation
    
    print("Running simulation...")
    sim = run_simulation(num_permits=50, random_seed=42, inter_arrival_time=1.0)
    
    print(f"\nCompleted {len(sim.completed_permits)} permits")
    print("Creating visualizations...\n")
    
    visualize_all(sim.completed_permits, save_prefix="permit_analysis")

