"""
Visualization script for permit processing times.
Creates various charts showing time spent in each stage of the process.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.axes import Axes
import numpy as np
from typing import List, Optional, Sequence
from permit_simulation import Permit


def _show_boxplot_stats_table(
    pairs: List[tuple[str, Sequence[float]]],
    *,
    heading: Optional[str],
    enabled: bool,
) -> None:
    if not enabled or not pairs:
        return
    from simulation_plot_helpers import show_boxplot_stats_table

    nonempty: List[tuple[str, Sequence[float]]] = []
    for lab, vals in pairs:
        arr = np.asarray(vals, dtype=float)
        if np.isfinite(arr).any():
            nonempty.append((lab, vals))
    if not nonempty:
        return
    show_boxplot_stats_table(nonempty, heading=heading)


def _show_aggregate_bxp_stats_table(
    rows: List[dict],
    *,
    heading: Optional[str],
    enabled: bool,
) -> None:
    if not enabled or not rows:
        return
    from simulation_plot_helpers import show_aggregate_bxp_stats_table

    show_aggregate_bxp_stats_table(rows, heading=heading)


GANTT_COLORS_OPTION_1 = {
    "EPA Debris (waiting)": "#CFE4FF", #light blue
    "EPA Debris (service)": "#6DB1FF", #dark blue
    "USACE Debris (waiting)": "#CFE4FF", #light blue
    "USACE Debris (service)": "#6DB1FF", #dark blue
    "Planning (waiting)": "#FFDDA6", #light orange
    "Planning (service)": "#FC9432", #dark orange
    "Agency Referral (waiting)": "#DEDEFF", #light purple
    "Agency Referral (service)": "#9391FF", #dark purple
    "Special Zoning": "#FFE341", #light yellow
    "Public Works (waiting)": "#F4D9FF", #light pink
    "Public Works (service)": "#E08FFF", #dark pink
    "Fire Review (waiting)": "#FFD9D9", #light red
    "Fire Review (service)": "#FE7070", #dark red
    "Pre-Application Activities": "#C3F7C5", # lighter green
    "Applicant Revisions": "#55C45E", # darker green
}

GANTT_COLORS_OPTION_2 = {
    "EPA Debris (waiting)": "#CFE4FF",
    "EPA Debris (service)": "#CDB1FF",
    "USACE Debris (waiting)": "#CFE4FF",
    "USACE Debris (service)": "#CDB1FF",
    "Planning (waiting)": "#FFF7A1",
    "Planning (service)": "#FFE341",
    "Agency Referral (waiting)": "#FFDDA6",
    "Agency Referral (service)": "#FC9432",
    "Special Zoning": "#FC9432",
    "Public Works (waiting)": "#FFF7A1",
    "Public Works (service)": "#FFE341",
    "Fire Review (waiting)": "#FFF7A1",
    "Fire Review (service)": "#FFE341",
    "Pre-Application Activities": "#C3F7C5",
    "Applicant Revisions": "#55C45E",
}

GANTT_COLOR_OPTIONS = {
    "option_1": GANTT_COLORS_OPTION_1,
    "option_2": GANTT_COLORS_OPTION_2,
}


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

    # Pre-application activities: plan preparation (single step)
    pre_app_service = 0.0
    if permit.plan_prep_start is not None and permit.plan_prep_end is not None:
        pre_app_service = permit.plan_prep_end - permit.plan_prep_start
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


def _gantt_intervals_from_permit(
    permit: Permit,
    color_map: Optional[dict] = None,
    color_option: str = "option_1",
):
    """
    Extract (start, end, label, color, is_waiting) for each activity interval from a permit.
    Returns a list of tuples. Waiting and service are separate intervals where applicable.

    Args:
        permit: Permit object to extract intervals from.
        color_map: Optional dict mapping exact interval labels to colors.
            Supported labels include:
            - "<Stage> (waiting)" and "<Stage> (service)" for queueable stages
            - "Special Zoning", "Pre-Application Activities", "Applicant Revisions"
            If provided, these entries override the selected color option.
        color_option: Name of base palette ("option_1" or "option_2").
    """
    colors = dict(GANTT_COLOR_OPTIONS.get(color_option, GANTT_COLORS_OPTION_1))
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

    # Pre-application activities: plan preparation
    if (
        getattr(permit, "plan_prep_start", None) is not None
        and getattr(permit, "plan_prep_end", None) is not None
        and permit.plan_prep_end > permit.plan_prep_start
    ):
        intervals.append((
            permit.plan_prep_start,
            permit.plan_prep_end,
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
    color_option: str = "option_1",
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
        color_option: Name of base Gantt palette ("option_1" or "option_2").

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

    intervals = _gantt_intervals_from_permit(
        p,
        color_map=color_map,
        color_option=color_option,
    )
    if not intervals:
        print("No activity intervals found for this permit.")
        return None, None

    fig, ax = plt.subplots(figsize=figsize)
    days_per_month = 30.0

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

    # One legend entry per interval label actually drawn.
    # Use a stable process-flow order and put unknown labels last.
    legend_order = [
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
    legend_order_index = {lab: i for i, lab in enumerate(legend_order)}
    label_to_color = {}  # (label, is_waiting) -> color
    for _start, _end, label, color, is_waiting in intervals:
        label_to_color.setdefault((label, is_waiting), color)

    # Plot each interval on the appropriate fixed row
    for start, end, label, color, is_waiting in intervals:
        start_months = start / days_per_month
        duration = (end - start) / days_per_month
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
            left=start_months,
            height=bar_height,
            color=color,
            alpha=alpha,
            edgecolor="black",
            linewidth=0.5,
            hatch=hatch,
        )

    # Build legend in canonical order, only for labels that appear in this permit.
    legend_handles = []
    legend_items = sorted(
        label_to_color.items(),
        key=lambda item: (
            legend_order_index.get(item[0][0], len(legend_order)),
            item[0][0],
        ),
    )
    for (label, is_waiting), color in legend_items:
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
    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=17)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(row_labels, fontsize=18)
    ax.set_xlabel('Time (months)', fontsize=20)
    if title is None:
        title = f"Gantt: Permit {p.permit_id} ({p.segment.name})"
    ax.set_title(title, fontsize=22, fontweight='bold')
    ax.tick_params(axis='x', labelsize=17)
    ax.tick_params(axis='y', labelsize=18)
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
    color_option: str = "option_1",
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
        color_option: Name of base Gantt palette ("option_1" or "option_2").
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

    permit_labels = [f"Permit {idx + 1}" for idx in range(n_permits)]

    fig, ax = plt.subplots(figsize=figsize)
    days_per_month = 30.0
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
        intervals = _gantt_intervals_from_permit(
            permit,
            color_map=color_map,
            color_option=color_option,
        )
        y_offset = perm_idx * n_rows_per_permit

        for start, end, label, color, is_waiting in intervals:
            start_months = start / days_per_month
            duration = (end - start) / days_per_month
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
                left=start_months,
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
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=17)

    n_total_rows = n_permits * n_rows_per_permit
    lane_centers = [
        i * n_rows_per_permit + (n_rows_per_permit - 1) / 2 for i in range(n_permits)
    ]
    ax.set_yticks(lane_centers)
    ax.set_yticklabels(permit_labels, fontsize=18)
    ax.set_xlabel('Time (months)', fontsize=20)
    ax.tick_params(axis='x', labelsize=17)
    ax.tick_params(axis='y', labelsize=18)
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
    color_option: str = "option_1",
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
        color_option: Name of base Gantt palette ("option_1" or "option_2").
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
    return plot_gantt_single_permit(
        permit,
        figsize=figsize,
        color_map=color_map,
        color_option=color_option,
    )


def plot_total_time_by_segment(
    permits: List[Permit],
    figsize=(10, 6),
    *,
    show_stats_table: bool = True,
):
    """
    Box plot of time from disaster to construction start for each segment (years).

    When ``show_stats_table`` is True (default), prints or displays a small table
    (``n``, mean, std, min, quartiles, max) for each box series after the figure.
    """
    from permit_simulation import Segment

    segment_times = {segment: [] for segment in Segment}
    for permit in permits:
        if permit.ready_for_construction is not None and permit.created_at is not None:
            total_time_years = (permit.ready_for_construction - permit.created_at) / 365.0
            segment_times[permit.segment].append(total_time_years)

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

    data = [segment_data[s] for s in segments]
    bp = ax.boxplot(
        data,
        patch_artist=True,
        vert=True,
        showmeans=True,
        medianprops={"color": "red"},
        meanprops={"marker": "o", "markeredgecolor": "black", "markerfacecolor": "green"},
    )

    # Add colors to box plots (match quartiles chart: Custom like, Pre-approved like, Self-cert like, then non-like)
    colors = ["#1565C0", "#2E7D32", "#EF6C00", "#90CAF9", "#81C784", "#FFB74D"]
    for patch, color in zip(bp["boxes"], colors[: len(segments)]):
        patch.set_facecolor(color)

    # Add dashed reference lines for 1 year and 2 years with text labels
    one_year = 1
    two_years = 2
    ax.axhline(y=one_year, color="gray", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.axhline(y=two_years, color="gray", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(
        1.02,
        one_year,
        " 1 Year",
        transform=ax.get_yaxis_transform(),
        ha="left",
        va="center",
        fontsize=10,
        color="gray",
        alpha=0.8,
    )
    ax.text(
        1.02,
        two_years,
        " 2 Years",
        transform=ax.get_yaxis_transform(),
        ha="left",
        va="center",
        fontsize=10,
        color="gray",
        alpha=0.8,
    )

    ax.set_ylabel("Time from Disaster to Construction Start (years)", fontsize=12)
    ax.set_title(
        "Time from Disaster to Construction Start by Segment (Box Plot)",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(np.arange(1, len(segments) + 1))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    _show_boxplot_stats_table(
        list(zip(labels, data)),
        heading="Total time disaster → construction by segment (years)",
        enabled=show_stats_table,
    )
    return fig, ax


def plot_total_time_by_segment_quartiles(
    permits: List[Permit],
    figsize=(10, 6),
    *,
    show_stats_table: bool = True,
):
    """
    Box plot of time from disaster to construction start by segment (years),
    one observation per **permit** in the pooled list (single run or merged runs).

    For Monte Carlo uncertainty across runs, prefer passing run-partitioned permits
    elsewhere; this helper stays permit-level for backward compatibility.
    """
    from permit_simulation import Segment

    segment_times = {segment: [] for segment in Segment}
    for permit in permits:
        if permit.ready_for_construction is not None and permit.created_at is not None:
            total_time_years = (permit.ready_for_construction - permit.created_at) / 365.0
            segment_times[permit.segment].append(total_time_years)

    segment_data = {s: times for s, times in segment_times.items() if times}
    if not segment_data:
        print("No data to plot for total time by segment.")
        return None, None

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
    data = [segment_data[s] for s in segments]

    fig, ax = plt.subplots(figsize=figsize)
    colors = ["#1565C0", "#2E7D32", "#EF6C00", "#90CAF9", "#81C784", "#FFB74D"]
    bp = ax.boxplot(
        data,
        patch_artist=True,
        vert=True,
        showfliers=True,
        whis=1.5,
    )
    for patch, color in zip(bp["boxes"], colors[: len(segments)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
        patch.set_edgecolor("black")

    one_year = 1
    ax.axhline(y=one_year, color="gray", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(
        1.02,
        one_year,
        " 1 Year",
        transform=ax.get_yaxis_transform(),
        ha="left",
        va="center",
        fontsize=10,
        color="gray",
        alpha=0.8,
    )

    ax.set_ylabel("Time from Disaster to Construction Start (years)", fontsize=12)
    ax.set_title(
        "Time from Disaster to Construction Start by Segment (box plot)",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(np.arange(1, len(segments) + 1))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    _show_boxplot_stats_table(
        list(zip(labels, data)),
        heading="Total time disaster → construction by segment (years)",
        enabled=show_stats_table,
    )
    return fig, ax


def plot_median_total_time_by_process(
    permits_by_process: dict,
    figsize=(12, 6),
    title: Optional[str] = None,
    *,
    application_to_ready: bool = False,
    ylabel: Optional[str] = None,
    ax: Optional[Axes] = None,
    legend: bool = True,
    show_stats_table: Optional[bool] = None,
):
    """
    Grouped box plots by segment.

    - ``application_to_ready=False`` (default): total time disaster → construction.
    - ``application_to_ready=True``: plan application (``planning_request``) →
      ``ready_for_construction``.

    If each dict value is ``list[list[Permit]]`` (one inner list per Monte Carlo run),
    all **permit-level** times in that segment are **pooled across runs** (sample size
    is the total number of permit observations), and one Tukey box is computed on that
    pooled sample and drawn with ``bxp``. Flat ``list[Permit]`` is the same with a single
    run's worth of permits.

    Pass ``ax`` to draw into an existing subplot (skips ``tight_layout`` on the figure).
    Set ``legend=False`` when combining several subplots and adding a figure-level legend.
    ``show_stats_table``: if ``None`` (default), a summary table is shown only when this
    call creates the figure (``ax`` was not passed). Pass ``True`` or ``False`` to override.
    ``ylabel``: if set, replaces the default y-axis label derived from ``application_to_ready``
    and whether runs are pooled.
    """
    from simulation_plot_helpers import pooled_tukey_boxplot_stats, values_are_run_lists

    from permit_simulation import Segment

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

    process_names = list(permits_by_process.keys())
    partitioned = values_are_run_lists(permits_by_process)
    n_runs_max = max((len(permits_by_process[p]) for p in process_names), default=0)
    multi_run_partitioned = partitioned and n_runs_max > 1
    owns_figure = ax is None
    if show_stats_table is None:
        show_stats_table = owns_figure
    if owns_figure:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    def _time_days(p) -> Optional[float]:
        if application_to_ready:
            if p.ready_for_construction is None or p.planning_request is None:
                return None
            return float(p.ready_for_construction - p.planning_request)
        if p.ready_for_construction is None:
            return None
        return float(p.ready_for_construction - p.created_at)

    def _per_run_value_lists(pname: str, seg: Segment) -> list[list[float]]:
        out: list[list[float]] = []
        for run_ps in permits_by_process[pname]:
            times = [
                float(t)
                for p in run_ps
                if getattr(p, "segment", None) == seg and (t := _time_days(p)) is not None
            ]
            if times:
                out.append(times)
        return out

    def _flat_value_list(pname: str, seg: Segment) -> list[float]:
        bucket = permits_by_process[pname]
        if partitioned:
            times: list[float] = []
            for run_ps in bucket:
                for p in run_ps:
                    if getattr(p, "segment", None) != seg:
                        continue
                    t = _time_days(p)
                    if t is not None:
                        times.append(float(t))
            return times
        return [
            float(t)
            for p in bucket
            if getattr(p, "segment", None) == seg and (t := _time_days(p)) is not None
        ]

    segments_to_plot = [
        seg
        for seg in segment_order
        if any(
            (
                len(_per_run_value_lists(p, seg)) > 0
                if partitioned
                else len(_flat_value_list(p, seg)) > 0
            )
            for p in process_names
        )
    ]
    if not segments_to_plot:
        print("No segment data to plot.")
        if owns_figure:
            plt.close(fig)
        return None, None

    plot_labels = [label_by_segment[s] for s in segments_to_plot]

    # Align with policy_lever_impact_analysis "Policy Intervention Comparison" palette:
    # Baseline (standard) gray, sequential dark green, parallel light green; AI rows use blues.
    colors = {
        "Standard": "#4d4d4d",
        "Sequential": "#238b45",
        "Parallel": "#74c476",
        "Initial AI Check": "#2171b5",
        "Full AI Review": "#9ecae1",
    }

    n_proc = len(process_names)
    # Within each segment, process box centers are 1 unit apart (base, base+1, …).
    # Use that full span for box width so adjacent process boxes touch edge-to-edge.
    intra_center_spacing = 1.0
    stride = n_proc * intra_center_spacing + 0.65
    box_width = intra_center_spacing
    bxp_stats_list: list[dict] = []
    aggregate_table_rows: list[dict] = []
    box_labels: list[str] = []
    positions_plot: list[float] = []
    facecolors: list[str] = []

    for j, seg in enumerate(segments_to_plot):
        base = j * stride
        for i, pname in enumerate(process_names):
            if partitioned:
                pr_lists = _per_run_value_lists(pname, seg)
            else:
                pts = _flat_value_list(pname, seg)
                pr_lists = [pts] if pts else []
            if not pr_lists:
                continue
            ms = pooled_tukey_boxplot_stats(pr_lists, whis=1.5)
            if not np.isfinite(ms["med"]):
                continue
            bxp_stats_list.append(
                {
                    "med": ms["med"],
                    "q1": ms["q1"],
                    "q3": ms["q3"],
                    "whislo": ms["whislo"],
                    "whishi": ms["whishi"],
                    "fliers": [],
                }
            )
            aggregate_table_rows.append(
                {
                    "series": f"{pname} | {label_by_segment[seg]}",
                    "n": ms["n"],
                    "n_runs": len(permits_by_process[pname]) if partitioned else 1,
                    "q1": ms["q1"],
                    "median": ms["med"],
                    "q3": ms["q3"],
                    "whisker_low": ms["whislo"],
                    "whisker_high": ms["whishi"],
                }
            )
            box_labels.append(f"{pname} | {label_by_segment[seg]}")
            positions_plot.append(base + i * intra_center_spacing)
            facecolors.append(colors.get(pname, "#888888"))

    if not bxp_stats_list:
        print("No segment data to plot.")
        if owns_figure:
            plt.close(fig)
        return None, None

    bp = ax.bxp(
        bxp_stats_list,
        positions=positions_plot,
        widths=box_width,
        patch_artist=True,
        showfliers=False,
    )
    for patch, fc in zip(bp["boxes"], facecolors):
        patch.set_facecolor(fc)
        patch.set_alpha(0.85)
        patch.set_edgecolor("black")

    _default_ylabel = (
        (
            "Application → ready (days); Tukey box on all permits (runs pooled)"
            if application_to_ready
            else "Total time disaster → construction (days); Tukey box on all permits (runs pooled)"
        )
        if multi_run_partitioned
        else (
            "Application → ready (days); Tukey box from permit-level times"
            if application_to_ready
            else "Total time disaster → construction (days); Tukey box from permit-level times"
        )
    )
    ax.set_ylabel(ylabel if ylabel is not None else _default_ylabel, fontsize=11)
    ax.set_xlabel("Permit Type", fontsize=12)
    ax.set_title(
        title
        if title is not None
        else (
            (
                "Time from plan application to ready for construction by segment"
                + (
                    " (all runs pooled)"
                    if multi_run_partitioned
                    else " (Tukey box, permit-level)"
                )
            )
            if application_to_ready
            else (
                "Total time from disaster to construction start by segment"
                + (
                    " (all runs pooled)"
                    if multi_run_partitioned
                    else " (Tukey box, permit-level)"
                )
            )
        ),
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks([j * stride + (n_proc - 1) * intra_center_spacing / 2 for j in range(len(segments_to_plot))])
    ax.set_xticklabels(plot_labels, rotation=45, ha="right")

    def _set_segment_bxp_xlim() -> None:
        # Pad past outer box edges (half box width + gap); old x_pad=0.5 sat flush on edges.
        if not positions_plot:
            return
        half_w = box_width * 0.5
        side_gap = 0.75
        ax.set_xlim(
            min(positions_plot) - half_w - side_gap,
            max(positions_plot) + half_w + side_gap,
        )

    _set_segment_bxp_xlim()
    if legend:
        ax.legend(
            handles=[
                mpatches.Patch(facecolor=colors.get(p, "#888"), alpha=0.85, edgecolor="black")
                for p in process_names
            ],
            labels=process_names,
            loc="upper left",
            bbox_to_anchor=(1.02, 1),
            fontsize=11,
        )
    ax.grid(axis="y", alpha=0.3)

    stats_heading = (
        title
        if title is not None
        else (
            "Application → ready by segment (days)"
            if application_to_ready
            else "Total time disaster → construction by segment (days)"
        )
    )
    _show_aggregate_bxp_stats_table(
        aggregate_table_rows,
        heading=stats_heading,
        enabled=show_stats_table,
    )

    if owns_figure:
        plt.tight_layout()
        _set_segment_bxp_xlim()
    return fig, ax


def plot_average_waiting_and_service_by_step(
    permits: List[Permit],
    figsize=(10, 6),
    label_map: Optional[dict] = None,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    silent: bool = False,
    runs: Optional[List[List[Permit]]] = None,
    *,
    title_size: Optional[float] = None,
    axis_label_size: Optional[float] = None,
    tick_label_size: Optional[float] = None,
    legend_size: Optional[float] = None,
    bar_value_size: Optional[float] = None,
    show_stats_table: bool = True,
):
    """
    Grouped **bar chart** of mean waiting vs mean service time by process step.

    Permit-level times are pooled into ``step_waiting`` / ``step_service`` (when ``runs``
    is set, all runs are flattened into the same pool). Each bar shows the arithmetic
    **mean** time for that step.

    Step names stay as internal keys unless you pass ``label_map`` for display labels.
    Pass ``show_stats_table=False`` to skip the printed distribution summary table.
    """
    if not permits and not runs:
        print("No permits provided for waiting/service by step chart.")
        return None, None

    pool = permits
    if runs:
        pool = [p for run in runs for p in run]

    step_waiting: dict = {}
    step_service: dict = {}

    for permit in pool:
        totals = calculate_step_waiting_service_totals(permit)
        for step_name, values in totals.items():
            step_waiting.setdefault(step_name, []).append(values["waiting"])
            step_service.setdefault(step_name, []).append(values["service"])

    if not step_waiting:
        print("No step data found for waiting/service chart.")
        return None, None

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

    use_multi_run_pooled = runs is not None and len(runs) > 1

    waiting_means: list[float] = []
    service_means: list[float] = []
    waiting_stds: list[float] = []
    service_stds: list[float] = []
    for s in steps:
        w = np.asarray(step_waiting[s], dtype=float)
        sv = np.asarray(step_service[s], dtype=float)
        waiting_means.append(float(np.mean(w)) if w.size else 0.0)
        service_means.append(float(np.mean(sv)) if sv.size else 0.0)
        waiting_stds.append(float(np.std(w, ddof=1)) if w.size > 1 else 0.0)
        service_stds.append(float(np.std(sv, ddof=1)) if sv.size > 1 else 0.0)

    x = np.arange(len(steps))
    width = 0.35

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    default_title = 14 if standalone else 10
    default_axis = 12 if standalone else 9
    default_tick = 10 if standalone else 7
    default_legend = 11 if standalone else 7

    if steps:
        ax.bar(
            x - width / 2,
            waiting_means,
            width,
            label="Waiting",
            color="#BDBDBD",
            edgecolor="black",
            linewidth=0.6,
            alpha=0.95,
        )
        ax.bar(
            x + width / 2,
            service_means,
            width,
            label="Service",
            color="#81C784",
            edgecolor="black",
            linewidth=0.6,
            alpha=0.95,
        )
        ax.legend(
            loc="upper right",
            fontsize=legend_size if legend_size is not None else default_legend,
            framealpha=0.95,
        )

    default_title_text = (
        "Average waiting vs service by process step (mean per permit; all runs pooled)"
        if use_multi_run_pooled
        else "Average waiting vs service by process step (mean per permit)"
    )
    ax.set_title(
        title if title is not None else default_title_text,
        fontsize=title_size if title_size is not None else default_title,
        fontweight="bold",
        pad=12 if standalone else 6,
    )
    ax.set_ylabel(
        "Time (days)",
        fontsize=axis_label_size if axis_label_size is not None else default_axis,
    )
    ax.set_xlabel(
        "Process Step",
        fontsize=axis_label_size if axis_label_size is not None else default_axis,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        display_labels,
        rotation=40,
        ha="right",
        fontsize=tick_label_size if tick_label_size is not None else default_tick,
    )
    ax.tick_params(axis="y", labelsize=tick_label_size if tick_label_size is not None else default_tick)
    ax.grid(axis="y", alpha=0.35, linestyle="-", color="#BDBDBD")
    ax.set_axisbelow(True)

    ymax = max(max(waiting_means, default=0.0), max(service_means, default=0.0))
    if ymax > 0:
        ax.set_ylim(0, ymax * 1.12)

    # Explicit x limits: margins() often leaves grouped bars flush with the y-axis / right spine.
    if steps:
        n = len(steps)
        left_edge = float(-width / 2)
        right_edge = float((n - 1) + width / 2)
        span = max(right_edge - left_edge, 1e-9)
        x_pad = max(width, 0.1 * span)
        ax.set_xlim(left_edge - x_pad, right_edge + x_pad)

    stats_pairs: List[tuple[str, Sequence[float]]] = []
    for dl, s in zip(display_labels, steps):
        stats_pairs.append((f"{dl} — waiting", step_waiting[s]))
        stats_pairs.append((f"{dl} — service", step_service[s]))
    _show_boxplot_stats_table(
        stats_pairs,
        heading=title if title is not None else default_title_text,
        enabled=show_stats_table,
    )

    if not silent:
        print("Waiting / service by step (days); mean ± σ (pooled permit-level):")
        for step, dl, wm, ws, sm, ss in zip(
            steps, display_labels, waiting_means, waiting_stds, service_means, service_stds
        ):
            print(
                f"  {step} ({dl}): waiting mean={wm:.2f}, σ={ws:.2f}; "
                f"service mean={sm:.2f}, σ={ss:.2f}"
            )

    if standalone:
        plt.tight_layout()
    return fig, ax


def plot_expedited_baseline_app_to_ready_boxplots(
    permits_base_by_case: dict,
    permits_balanced_by_case: dict,
    *,
    permit_counts: Sequence[int] = (2000, 6500),
    staffing_order: Sequence[str] = ("low", "medium", "high"),
    block_gap: float = 1.12,
    figsize: tuple = (11.0, 6.2),
    ax: Optional[Axes] = None,
    title: str = "Time Savings from Expedited Permit Options",
    ylabel: str = "Time to ready for construction (months)",
    baseline_label: str = "Mean permitting time (baseline)",
    expedited_label: str = "Mean permitting time (expedited permits)",
    showfliers: bool = False,
    show_stats_table: bool = False,
):
    """
    Grouped **box plots** comparing baseline vs expedited (balanced) permit mix.

    For each combination of permit volume, staffing level, and scenario, every permit
    observation of time from **plan application** to **ready for construction** is pooled across **all
    Monte Carlo runs** (one box per scenario side, using the full run×permit sample).

    Expects dict keys ``"permits={n}|staffing={level}"`` as produced in
    ``run_simulation_with_segments_cases`` experiment cell.
    """
    from matplotlib.transforms import blended_transform_factory

    def _app_to_ready_months(p: Permit) -> Optional[float]:
        if p.ready_for_construction is None or p.planning_request is None:
            return None
        days = float(p.ready_for_construction - p.planning_request)
        return days / (365.0 / 12.0)

    tick_pos: list[float] = []
    tick_labs: list[str] = []
    pos_b: list[float] = []
    pos_e: list[float] = []
    data_b: list[list[float]] = []
    data_e: list[list[float]] = []
    block_centers: list[float] = []

    x = 0.0
    box_w = 0.34
    dw = 0.19

    for n in permit_counts:
        n0 = len(tick_pos)
        for staff in staffing_order:
            key = f"permits={n}|staffing={staff}"
            bperm = permits_base_by_case.get(key, [])
            eperm = permits_balanced_by_case.get(key, [])
            bvals = [v for v in (_app_to_ready_months(p) for p in bperm) if v is not None and np.isfinite(v)]
            evals = [v for v in (_app_to_ready_months(p) for p in eperm) if v is not None and np.isfinite(v)]
            if not bvals and not evals:
                x += 1.0
                continue
            tick_pos.append(x)
            tick_labs.append(staff.capitalize())
            pos_b.append(x - dw)
            pos_e.append(x + dw)
            data_b.append(bvals if bvals else [float("nan")])
            data_e.append(evals if evals else [float("nan")])
            x += 1.0
        if len(tick_pos) > n0:
            block_centers.append(float(np.mean(tick_pos[n0:])))
        x += block_gap

    if not data_b:
        print("No application→ready data for expedited vs baseline box plot.")
        return None, None

    x_right = x - block_gap + 0.5
    owns_figure = ax is None
    if owns_figure:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    bp_b = ax.boxplot(
        data_b,
        positions=pos_b,
        widths=box_w,
        patch_artist=True,
        showfliers=showfliers,
        whis=1.5,
        medianprops=dict(color="darkred", linewidth=2),
    )
    bp_e = ax.boxplot(
        data_e,
        positions=pos_e,
        widths=box_w,
        patch_artist=True,
        showfliers=showfliers,
        whis=1.5,
        medianprops=dict(color="darkred", linewidth=2),
    )
    for patch in bp_b["boxes"]:
        patch.set_facecolor("#BDBDBD")
        patch.set_alpha(0.95)
        patch.set_edgecolor("black")
    for patch in bp_e["boxes"]:
        patch.set_facecolor("#7E57C2")
        patch.set_alpha(0.95)
        patch.set_edgecolor("black")

    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_labs, rotation=0, fontsize=11)
    ax.set_xlim(-0.55, x_right)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.35, linestyle="-", color="#BDBDBD")
    ax.set_axisbelow(True)

    flat: list[float] = []
    for a, b in zip(data_b, data_e):
        flat.extend([v for v in a if np.isfinite(v)])
        flat.extend([v for v in b if np.isfinite(v)])
    ymax = float(np.nanmax(flat)) * 1.12 if flat else 1.0
    ax.set_ylim(0.0, ymax)

    trans = blended_transform_factory(ax.transData, ax.transAxes)
    for cx, nperm in zip(block_centers, permit_counts):
        ax.text(cx, -0.09, f"{nperm:,}", transform=trans, ha="center", va="top", fontsize=12, fontweight="bold")

    ax.legend(
        handles=[
            mpatches.Patch(facecolor="#BDBDBD", edgecolor="black", alpha=0.95, label=baseline_label),
            mpatches.Patch(facecolor="#7E57C2", edgecolor="black", alpha=0.95, label=expedited_label),
        ],
        loc="upper right",
        fontsize=10,
        framealpha=0.95,
    )

    if show_stats_table:
        pairs: List[tuple[str, Sequence[float]]] = []
        for lab, bb, ee in zip(tick_labs, data_b, data_e):
            pairs.append((f"{lab} — baseline", bb))
            pairs.append((f"{lab} — expedited", ee))
        _show_boxplot_stats_table(
            pairs,
            heading=title,
            enabled=True,
        )

    if owns_figure:
        plt.tight_layout(rect=[0, 0.05, 1, 1])
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
    sim = run_simulation(num_permits=50, random_seed=42)
    
    print(f"\nCompleted {len(sim.completed_permits)} permits")
    print("Creating visualizations...\n")
    
    visualize_all(sim.completed_permits, save_prefix="permit_analysis")

