"""
Visualization script for permit processing times.
Creates various charts showing time spent in each stage of the process.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import List, Optional
from permit_simulation import Permit

DEFAULT_GANTT_COLORS = {
    "EPA Debris (waiting)": "#B3E5FC",      # Light blue (waiting state)
    "EPA Debris (service)": "#0288D1",      # Darker blue (active state)
    "USACE Debris (waiting)": "#B3E5FC",
    "USACE Debris (service)": "#0288D1",
    "Planning (waiting)": "#FFE0B2",        # Light orange (waiting state)
    "Planning (service)": "#FF8F00",        # Darker orange (active state)
    "Agency Referral (waiting)": "#E1BEE7", # Light purple (waiting state)
    "Agency Referral (service)": "#7B1FA2", # Darker purple (active state)
    "Special Zoning": "#FFF59D",            # Light yellow
    "Public Works (waiting)": "#F0F4C3",    # Light purple-gray (waiting state)
    "Public Works (service)": "#9575CD",    # Medium purple (active state)
    "Fire Review (waiting)": "#FFCCBC",     # Light red/pink (waiting state)
    "Fire Review (service)": "#D84315",     # Darker red (active state)
    "Pre-Application Activities": "#C8E6C9", # Light green
    "Applicant Revisions": "#81C784",       # Medium green
}


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

    
    # Pre-application activities (authorization + plan preparation, service only)
    pre_app = 0.0
    if permit.authorization_start is not None and permit.authorization_end is not None:
        pre_app += permit.authorization_end - permit.authorization_start
    if permit.plan_prep_start is not None and permit.plan_prep_end is not None:
        pre_app += permit.plan_prep_end - permit.plan_prep_start
    if pre_app > 0:
        stages["Pre-application activities"] = pre_app

    # Applicant revisions (aggregated service time done by applicant)
    if getattr(permit, "applicant_revisions_total_time", 0.0) > 0:
        stages["Applicant Revisions"] = permit.applicant_revisions_total_time
    
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
    
    # Agency referral — separate waiting and service
    if (permit.agency_referral_request is not None and
        permit.agency_referral_service_start is not None and
        permit.agency_referral_end is not None):
        stages['Agency Referral (Waiting)'] = permit.agency_referral_service_start - permit.agency_referral_request
        stages['Agency Referral (Service)'] = permit.agency_referral_end - permit.agency_referral_service_start
    
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

    # Pre-application activities: authorization + plan preparation (single step)
    pre_app_service = 0.0
    if permit.authorization_start is not None and permit.authorization_end is not None:
        pre_app_service += permit.authorization_end - permit.authorization_start
    if permit.plan_prep_start is not None and permit.plan_prep_end is not None:
        pre_app_service += permit.plan_prep_end - permit.plan_prep_start
    if pre_app_service > 0:
        steps["Pre-Application Activities"] = {"waiting": 0.0, "service": pre_app_service}

    # Applicant revisions (service only, no agency waiting)
    if getattr(permit, "applicant_revisions_total_time", 0.0) > 0:
        steps["Applicant Revisions"] = {
            "waiting": 0.0,
            "service": permit.applicant_revisions_total_time,
        }

    # Planning department (aggregate initial + recheck)
    planning_waiting = permit.planning_initial_waiting + permit.planning_recheck_waiting
    planning_service = permit.planning_initial_service + permit.planning_recheck_service
    if planning_waiting > 0 or planning_service > 0:
        steps["Planning"] = {"waiting": planning_waiting, "service": planning_service}

    # Agency referral
    agency_referral_waiting = 0.0
    agency_referral_service = 0.0
    if (
        permit.agency_referral_request is not None
        and permit.agency_referral_service_start is not None
        and permit.agency_referral_end is not None
    ):
        agency_referral_waiting = permit.agency_referral_service_start - permit.agency_referral_request
        agency_referral_service = permit.agency_referral_end - permit.agency_referral_service_start
    if agency_referral_waiting > 0 or agency_referral_service > 0:
        steps["Agency Referral"] = {"waiting": agency_referral_waiting, "service": agency_referral_service}

    # Special Zoning Review (service only, no agency waiting tracked)
    if getattr(permit, "zoning_start", None) is not None and getattr(permit, "zoning_end", None) is not None:
        zoning_service = permit.zoning_end - permit.zoning_start
        if zoning_service > 0:
            steps["Special Zoning"] = {"waiting": 0.0, "service": zoning_service}

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

    return steps


def _gantt_intervals_from_permit(permit: Permit, color_map: Optional[dict] = None):
    """
    Extract (start, end, label, color, is_waiting) for each activity interval from a permit.
    Returns a list of tuples. Waiting and service are separate intervals where applicable.

    Args:
        permit: Permit object to extract intervals from.
        color_map: Optional dict mapping exact interval labels to colors.
            Supported labels include:
            - "<Stage> (waiting)" and "<Stage> (service)" for queueable stages
            - "Special Zoning", "Pre-Application Activities", "Applicant Revisions"
            If omitted, uses DEFAULT_GANTT_COLORS.
    """
    colors = dict(DEFAULT_GANTT_COLORS)
    if color_map:
        colors.update(color_map)

    def stage_color(label: str, fallback: str) -> str:
        return colors.get(label, fallback)

    intervals = []
    # Stages: (label, request_attr, service_start_attr, end_attr)
    stages_info = [
        ("EPA Debris", "epa_debris_request", "epa_debris_service_start", "epa_debris_end"),
        ("USACE Debris", "usace_debris_request", "usace_debris_service_start", "usace_debris_end"),
        ("Planning", "planning_request", "planning_service_start", "planning_end"),
        ("Agency Referral", "agency_referral_request", "agency_referral_service_start", "agency_referral_end"),
        ("Special Zoning", "zoning_start", None, "zoning_end"),
        ("Public Works", "public_works_request", "public_works_service_start", "public_works_end"),
        ("Fire Review", "fire_review_request", "fire_review_service_start", "fire_review_end"),
    ]

    # Intervals where the applicant is revising (no reviews should be active).
    revision_intervals = sorted(
        getattr(permit, "applicant_revision_intervals", []),
        key=lambda x: x[0],
    )

    def carve_out_revisions(start, end, is_review_service):
        """Return sub-intervals of [start, end] that do NOT overlap applicant revisions."""
        if not is_review_service or not revision_intervals:
            return [(start, end)]
        result = []
        cur = start
        for rs, re in revision_intervals:
            if re <= cur or rs >= end:
                continue
            if rs > cur:
                result.append((cur, min(rs, end)))
            cur = max(cur, re)
            if cur >= end:
                break
        if cur < end:
            result.append((cur, end))
        return result

    review_stages = {"Planning", "Agency Referral", "Public Works", "Fire Review"}

    # Pre-application activities: one bar from start of authorization through plan submission
    pa_start = getattr(permit, "authorization_start", None)
    pa_end = getattr(permit, "plan_prep_end", None)
    if pa_start is not None and pa_end is not None and pa_end > pa_start:
        intervals.append((
            pa_start,
            pa_end,
            "Pre-Application Activities",
            stage_color("Pre-Application Activities", "#659DB2"),
            False,
        ))
    elif getattr(permit, "plan_prep_start", None) is not None and pa_end is not None and pa_end > permit.plan_prep_start:
        intervals.append((
            permit.plan_prep_start,
            pa_end,
            "Pre-Application Activities",
            stage_color("Pre-Application Activities", "#659DB2"),
            False,
        ))

    for stage_name, request_attr, service_start_attr, end_attr in stages_info:
        request_time = getattr(permit, request_attr, None) if request_attr else None
        service_start_time = getattr(permit, service_start_attr, None) if service_start_attr else None
        end_time = getattr(permit, end_attr, None) if end_attr else None
        if request_time is None or end_time is None:
            continue
        if service_start_attr and service_start_time is not None:
            wait_dur = service_start_time - request_time
            waiting_label = f"{stage_name} (waiting)"
            service_label = f"{stage_name} (service)"
            if wait_dur > 0.001:
                intervals.append((
                    request_time,
                    service_start_time,
                    waiting_label,
                    stage_color(waiting_label, "#BDBDBD"),
                    True,
                ))
            if end_time - service_start_time > 0:
                is_review_service = stage_name in review_stages
                for seg_start, seg_end in carve_out_revisions(service_start_time, end_time, is_review_service):
                    if seg_end - seg_start > 0:
                        intervals.append((
                            seg_start,
                            seg_end,
                            service_label,
                            stage_color(service_label, "#81C784"),
                            False,
                        ))
        else:
            if end_time - request_time > 0:
                intervals.append((
                    request_time,
                    end_time,
                    stage_name,
                    stage_color(stage_name, "#81C784"),
                    False,
                ))

    # Applicant revisions: service-only intervals recorded on the permit
    for start, end in getattr(permit, "applicant_revision_intervals", []):
        if start is None or end is None:
            continue
        if end - start > 0:
            intervals.append((
                start,
                end,
                "Applicant Revisions",
                stage_color("Applicant Revisions", "#659DB2"),
                False,
            ))
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
    permit: Permit = None,
    permits: List[Permit] = None,
    permit_id: Optional[int] = None,
    figsize=(14, 5),
    title: str = None,
    color_map: Optional[dict] = None,
):
    """
    Create a Gantt chart for a single permit with parallel activities on separate rows
    so that overlapping activities are visible on different bars.

    Args:
        permit: Single Permit object (use this when you have the permit directly)
        permits: List of permits (use with permit_id to look up by ID)
        permit_id: Permit ID to look up from permits list (use with permits)
        figsize: Figure size tuple
        title: Optional chart title (default: "Permit {id} (Segment {segment})")
        color_map: Optional dict of interval-label -> color overrides.
            Example keys: "EPA Debris (waiting)", "Planning (service)",
            "Special Zoning", "Pre-Application Activities", "Applicant Revisions".

    Note: completed_permits is ordered by completion time, not permit_id. Use permit_id
    to plot a specific permit by its ID, e.g. plot_gantt_single_permit(permits=sim.completed_permits, permit_id=237)
    """
    if permit is not None:
        p = permit
    elif permits is not None and permit_id is not None:
        p = next((x for x in permits if x.permit_id == permit_id), None)
        if p is None:
            print(f"No permit found with permit_id={permit_id}. Available IDs: {[x.permit_id for x in permits[:10]]}...")
            return None, None
    else:
        raise ValueError("Provide either permit= or (permits=, permit_id=)")

    intervals = _gantt_intervals_from_permit(p, color_map=color_map)
    if not intervals:
        print("No activity intervals found for this permit.")
        return None, None

    fig, ax = plt.subplots(figsize=figsize)

    # Define the four fixed rows the user requested
    # Six fixed rows in logical order:
    # 1) Debris removal
    # 2) Pre-application activities
    # 3) Planning & Zoning (Planning + Agency Referral)
    # 4) Public Works
    # 5) Fire
    row_definitions = [
        ("Remove debris", ["EPA Debris", "USACE Debris"]),
        ("Applicant activities", ["Pre-Application Activities", "Applicant Revisions"]),
        ("Planning, Special Zoning, and Building & Safety", ["Planning", "Special Zoning", "Public Works"]),
        ("Agency Referral and Fire", ["Agency Referral", "Fire Review"])
    ]
    n_rows = len(row_definitions)
    y_positions = list(range(n_rows))
    # We'll place Debris at the top, then Planning/Agency Referral/Public Works,
    # then Fire Review at the bottom.
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
        ('Remove debris (waiting)', True), ('Remove debris (service)', False),
        ('Homeowner', False),
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
        # Map logical row (0 = Debris, 1 = Planning/Agency Referral/PW, 2 = Fire)
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
        title = f"Gantt: Permit {p.permit_id} ({p.segment.name})"
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
    color_map: Optional[dict] = None,
):
    """
    Plot a Gantt chart showing multiple random permits in the same chart.

    Args:
        permits: List of completed Permit objects
        n_permits: Number of permits to show (default 3)
        segment_value: If provided, only pick permits from this segment (e.g. 4 = CUSTOM_NON_LIKE)
        random_seed: Optional seed for reproducible random choice
        figsize: Figure size tuple
        color_map: Optional dict of interval-label -> color overrides.
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
        ("Remove debris", ["EPA Debris", "USACE Debris"]),
        ("Applicant activities", ["Pre-Application Activities", "Applicant Revisions"]),
        # Must match _gantt_intervals_from_permit stage names ("Special Zoning", not "Special Zoning Review")
        ("Planning and Building & Safety", ["Planning", "Special Zoning", "Public Works"]),
        ("Agency Referral and Fire", ["Agency Referral", "Fire Review"]),
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

    # One legend entry per interval label actually drawn (full label + waiting flag)
    plotted_legend = {}

    # Consistent legend order; unknown labels sort last
    _legend_label_order = [
        "EPA Debris (waiting)", "EPA Debris (service)",
        "USACE Debris (waiting)", "USACE Debris (service)",
        "Pre-Application Activities",
        "Planning (waiting)", "Planning (service)",
        "Special Zoning",
        "Public Works (waiting)", "Public Works (service)",
        "Agency Referral (waiting)", "Agency Referral (service)",
        "Fire Review (waiting)", "Fire Review (service)",
        "Applicant Revisions",
    ]
    _order_index = {lab: i for i, lab in enumerate(_legend_label_order)}

    def _legend_sort_key(item):
        (lab, _iw), _col = item
        return (_order_index.get(lab, len(_legend_label_order)), lab)

    for perm_idx, permit in enumerate(selected):
        intervals = _gantt_intervals_from_permit(permit, color_map=color_map)
        y_offset = perm_idx * n_rows_per_permit

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
            leg_key = (label, is_waiting)
            if leg_key not in plotted_legend:
                plotted_legend[leg_key] = color

    # Horizontal dashed lines separating each permit
    for i in range(1, n_permits):
        y_sep = i * n_rows_per_permit - 0.5
        ax.axhline(y=y_sep, linestyle='--', color='gray', alpha=0.7, linewidth=1.5)

    legend_handles = []
    for (lab, is_waiting), color in sorted(plotted_legend.items(), key=_legend_sort_key):
        hatch = "///" if is_waiting else None
        alpha = 0.6 if is_waiting else 0.9
        legend_handles.append(mpatches.Patch(
            facecolor=color, alpha=alpha, edgecolor="black", linewidth=0.5,
            hatch=hatch, label=lab,
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
    color_map: Optional[dict] = None,
):
    """
    Plot a Gantt chart for one random permit in the given segment.
    Segment 4 = CUSTOM_NON_LIKE. Parallel activities are shown on separate rows.

    Args:
        permits: List of completed Permit objects
        segment_value: Segment enum value (default 4 = CUSTOM_NON_LIKE)
        random_seed: Optional seed for reproducible random choice
        figsize: Figure size tuple
        color_map: Optional dict of interval-label -> color overrides.
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
    return plot_gantt_single_permit(permit, figsize=figsize, color_map=color_map)


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
    
    # Use stable segment order and friendly labels (match quartiles plot)
    segment_order = [
        Segment.CUSTOM_LIKE,
        Segment.PRE_APPROVED_LIKE,
        Segment.SELF_CERT_LIKE,
        Segment.CUSTOM_NON_LIKE,
        Segment.PRE_APPROVED_NON_LIKE,
        Segment.SELF_CERT_NON_LIKE,
    ]
    label_by_segment = {
        Segment.PRE_APPROVED_LIKE: "Pre-approved like",
        Segment.PRE_APPROVED_NON_LIKE: "Pre-approved non-like",
        Segment.CUSTOM_LIKE: "Custom like",
        Segment.CUSTOM_NON_LIKE: "Custom non-like",
        Segment.SELF_CERT_LIKE: "Self-certified like",
        Segment.SELF_CERT_NON_LIKE: "Self-certified non-like",
    }
    segments = [s for s in segment_order if s in segment_data]
    labels = [label_by_segment[s] for s in segments]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if show_boxplot:
        data = [segment_data[s] for s in segments]
        bp = ax.boxplot(data, patch_artist=True, vert=True, showmeans=True, 
                        medianprops={'color': 'red'}, meanprops={'marker': 'o', 'markeredgecolor': 'black', 'markerfacecolor': 'green'})
        
        # Add colors to box plots (match quartiles chart: Custom like, Pre-approved like, Self-cert like, then non-like)
        colors = ['#1565C0', '#2E7D32', '#EF6C00', '#90CAF9', '#81C784', '#FFB74D']
        for patch, color in zip(bp['boxes'], colors[:len(segments)]):
            patch.set_facecolor(color)
        
        # Add sample size (n)
        for i, s in enumerate(segments):
            count = len(segment_data[s])
            y_pos = np.median(data[i])  # Position near the median
            ax.text(i + 1, np.max(data[i]) + 0.05 * (np.max(data[i]) - np.min(data[i])), f'n={count}',
                    horizontalalignment='center', verticalalignment='bottom', fontsize=9, color='gray')
        
        # Add dashed reference lines for 1 year and 2 years with text labels
        one_year = 365
        two_years = 730
        ax.axhline(y=one_year, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)
        ax.axhline(y=two_years, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)
        ax.text(1.02, one_year, ' 1 Year', transform=ax.get_yaxis_transform(), ha='left', va='center',
                fontsize=10, color='gray', alpha=0.8)
        ax.text(1.02, two_years, ' 2 Years', transform=ax.get_yaxis_transform(), ha='left', va='center',
                fontsize=10, color='gray', alpha=0.8)
        
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

    # Enforce a stable segment order so bars and labels always align.
    segment_order = [
        Segment.CUSTOM_LIKE,
        Segment.PRE_APPROVED_LIKE,
        Segment.SELF_CERT_LIKE,
        Segment.CUSTOM_NON_LIKE,
        Segment.PRE_APPROVED_NON_LIKE,
        Segment.SELF_CERT_NON_LIKE,
    ]
    label_by_segment = {
        Segment.CUSTOM_LIKE: "Custom like",
        Segment.PRE_APPROVED_LIKE: "Pre-approved like",
        Segment.SELF_CERT_LIKE: "Self-certified like",
        Segment.CUSTOM_NON_LIKE: "Custom non-like",
        Segment.PRE_APPROVED_NON_LIKE: "Pre-approved non-like",
        Segment.SELF_CERT_NON_LIKE: "Self-certified non-like",
    }

    segments = [s for s in segment_order if s in segment_data]
    labels = [label_by_segment[s] for s in segments]

    medians = [np.median(segment_data[s]) for s in segments]
    p25 = [np.percentile(segment_data[s], 25) for s in segments]
    p75 = [np.percentile(segment_data[s], 75) for s in segments]

    # Asymmetric error bars: lower = median - p25, upper = p75 - median
    yerr_lower = [medians[i] - p25[i] for i in range(len(segments))]
    yerr_upper = [p75[i] - medians[i] for i in range(len(segments))]
    yerr = [yerr_lower, yerr_upper]

    fig, ax = plt.subplots(figsize=figsize)
    colors = ['#1565C0', '#2E7D32', '#EF6C00', '#90CAF9', '#81C784' , '#FFB74D']
    x = np.arange(len(segments))
    bars = ax.bar(x, medians, yerr=yerr, capsize=5, color=colors[:len(segments)], alpha=0.8, edgecolor='black')

    # Overlay outlier points (above 75th percentile only) in a straight line
    for i, s in enumerate(segments):
        times = np.array(segment_data[s])
        outliers = times[times > p75[i]]
        if len(outliers) > 0:
            ax.scatter(np.full(len(outliers), x[i]), outliers, color='black', alpha=0.4, s=20, zorder=5)

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
        Segment.CUSTOM_LIKE,
        Segment.PRE_APPROVED_LIKE,
        Segment.SELF_CERT_LIKE,
        Segment.CUSTOM_NON_LIKE,
        Segment.PRE_APPROVED_NON_LIKE,
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

    labels = ["Custom like", "Pre-approved like", "Self-certified like", "Custom non-like", "Pre-approved non-like", "Self-certified non-like"]
    x = np.arange(len(labels))
    width = 0.25
    n_processes = len(process_names)

    fig, ax = plt.subplots(figsize=figsize)

    colors = {
        "Standard": "#1976D2",
        "Sequential": "#F57C00",
        "Parallel": "#388E3C",
        "Initial AI Check": "#F57C00",
        "Full AI Review": "#388E3C",
    }
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
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    return fig, ax


def plot_average_waiting_and_service_by_step(
    permits: List[Permit],
    figsize=(10, 6),
    label_map: Optional[dict] = None,
):
    """
    Bar chart of average waiting vs service time by process step.

    Uses the same *types* of labels as a standard process chart:
    - Title: average waiting vs service by process step
    - Y-axis: average time (days)
    - X-axis: process step
    - Legend: Waiting (gray) vs Service (green)

    Step *names* stay as your internal keys unless you pass ``label_map``
    (optional display strings only—you do not need to match any fixed list).

    Returns:
        (fig, ax) or (None, None) if there is nothing to plot.
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

    # Process-flow order; only steps that appear in the data are plotted
    preferred_order = [
        "EPA Debris",
        "USACE Debris",
        "Pre-Application Activities",
        "Planning",
        "Special Zoning",
        "Public Works",
        "Agency Referral",
        "Fire Review",
        "Applicant Revisions",
    ]

    steps = [s for s in preferred_order if s in step_waiting]
    for step in sorted(step_waiting.keys()):
        if step not in steps:
            steps.append(step)

    label_map = label_map or {}
    display_labels = [label_map.get(s, s) for s in steps]

    waiting_means = [np.mean(step_waiting[s]) for s in steps]
    waiting_stds = [np.std(step_waiting[s]) for s in steps]
    service_means = [np.mean(step_service.get(s, [0.0])) for s in steps]
    service_stds = [np.std(step_service.get(s, [0.0])) for s in steps]

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

    ax.set_title(
        "Average Total Waiting vs Service Time by Process Step",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_ylabel("Average Time (days)", fontsize=12)
    ax.set_xlabel("Process Step", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(display_labels, rotation=40, ha="right", fontsize=10)
    ax.legend(loc="upper right", fontsize=11, framealpha=0.95)
    ax.grid(axis="y", alpha=0.35, linestyle="-", color="#BDBDBD")
    ax.set_axisbelow(True)

    ymax = max(max(waiting_means + [0]), max(service_means + [0]))
    if ymax > 0:
        ax.set_ylim(0, ymax * 1.12)

    # Value labels above bars (skip clutter when bar is tiny)
    for bar in list(bars_wait) + list(bars_service):
        height = bar.get_height()
        if height < 0.05:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    print("Average waiting and service time by step (days):")
    for step, w_mean, w_std, s_mean, s_std in zip(
        steps, waiting_means, waiting_stds, service_means, service_stds
    ):
        print(
            f"  {step}: "
            f"waiting mean={w_mean:.2f}, σ={w_std:.2f}; "
            f"service mean={s_mean:.2f}, σ={s_std:.2f}"
        )

    plt.tight_layout()
    return fig, ax


def plot_permits_by_stage_over_time(
    permits: List[Permit],
    stages: Optional[List[str]] = None,
    include_waiting: bool = True,
    include_service: bool = True,
    num_points: int = 200,
    figsize=(12, 6),
):
    """
    Plot the total number of permits active in each stage over time.

    This uses the same stage definitions as the Gantt chart helper
    (_gantt_intervals_from_permit), and counts a permit as \"in a stage\"
    whenever it is either waiting or in service for that stage (configurable).

    Args:
        permits: List of Permit objects.
        stages: Optional list of stage labels to include. If None, uses all
                stages seen in the intervals (e.g. 'Planning', 'Public Works').
                Note: waiting/service variants like 'Planning (waiting)' and
                'Planning (service)' are collapsed to 'Planning'.
        include_waiting: If True, count waiting intervals for each stage.
        include_service: If True, count service intervals for each stage.
        num_points: Number of time samples between earliest start and latest
                    end to estimate counts.
        figsize: Matplotlib figure size.
    """
    if not permits:
        print("No permits provided for stage-over-time chart.")
        return None, None

    # Collect FIRST time each permit reaches each stage (for cumulative curves)
    stage_first_times: dict[str, list[float]] = {}
    t_min = None
    t_max = None

    for permit in permits:
        per_permit_first: dict[str, float] = {}
        for start, end, label, _color, is_waiting in _gantt_intervals_from_permit(permit):
            # Collapse 'Planning (waiting)' / 'Planning (service)' -> 'Planning'
            base_label = label.split(" (")[0]
            if is_waiting and not include_waiting:
                continue
            if (not is_waiting) and not include_service:
                continue
            if start is None or end is None or end <= start:
                continue

            prev = per_permit_first.get(base_label)
            if prev is None or start < prev:
                per_permit_first[base_label] = start

        for stage_name, first_time in per_permit_first.items():
            stage_first_times.setdefault(stage_name, []).append(first_time)
            t_min = first_time if t_min is None else min(t_min, first_time)
            t_max = first_time if t_max is None else max(t_max, first_time)

    if t_min is None:
        print("No stage timing data found for stage-over-time chart.")
        return None, None

    # Choose which stages to plot
    all_stage_names = sorted(stage_first_times.keys())
    if stages is None:
        stages_to_plot = all_stage_names
    else:
        stages_to_plot = [s for s in stages if s in stage_first_times]
        if not stages_to_plot:
            print("None of the requested stages were found in the data.")
            return None, None

    # Sample times and count permits that have REACHED each stage (cumulative)
    times = np.linspace(t_min, t_max, num_points)
    counts = {stage: np.zeros_like(times, dtype=float) for stage in stages_to_plot}

    for stage in stages_to_plot:
        first_times = np.sort(np.array(stage_first_times.get(stage, []), dtype=float))
        if first_times.size == 0:
            continue
        arr = counts[stage]
        idx = 0
        running = 0.0
        for i, t in enumerate(times):
            while idx < first_times.size and first_times[idx] <= t:
                running += 1.0
                idx += 1
            arr[i] = running

    # Convert to share of permits (0–100%) for cumulative recovery-style curves
    total_permits = max(len(permits), 1)
    fig, ax = plt.subplots(figsize=figsize)

    # Convert simulation time (days) to rough months for readability
    time_months = times / 30.0

    for stage in stages_to_plot:
        share_pct = counts[stage] / total_permits * 100.0
        ax.plot(time_months, share_pct, linewidth=2, label=stage)

    ax.set_xlabel("Months postdisaster (simulation time)", fontsize=12)
    ax.set_ylabel("Share of permits in stage (%)", fontsize=12)
    ax.set_title("Share of permits by stage over time", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower right")
    ax.grid(axis="both", alpha=0.3)

    plt.tight_layout()
    return fig, ax


def visualize_all(permits: List[Permit], save_prefix: str = None, show: bool = True):
    """
    Create key visualizations and optionally save them.
    
    Currently includes:
    - Total time from disaster to construction start by segment (box plot)
    - Average total waiting vs service time by step
    """
    print(f"Creating visualizations for {len(permits)} permits...")
    
    # 1. Total time by segment (box plot)
    print("  Creating total time by segment chart (box plot)...")
    fig1, _ = plot_total_time_by_segment(permits)
    if save_prefix and fig1:
        fig1.savefig(f"{save_prefix}_total_time_by_segment.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_total_time_by_segment.png")

    # 2. Average total waiting vs service by step
    print("  Creating waiting vs service by step chart...")
    fig2, _ = plot_average_waiting_and_service_by_step(permits)
    if save_prefix and fig2:
        fig2.savefig(f"{save_prefix}_waiting_service_by_step.png", dpi=300, bbox_inches='tight')
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

