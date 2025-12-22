"""
Visualization script for permit processing times.
Creates various charts showing time spent in each stage of the process.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import List
from permit_simulation import Permit


def calculate_stage_times(permit: Permit) -> dict:
    """
    Calculate time spent in each stage for a permit.
    Returns a dictionary with stage names and durations in days.
    """
    stages = {}
    
    # Debris removal (EPA + USACE) - separate waiting and service
    if permit.debris_removal_request and permit.debris_removal_end:
        if permit.debris_removal_service_start:
            stages['Debris Removal (Waiting)'] = permit.debris_removal_service_start - permit.debris_removal_request
            stages['Debris Removal (Service)'] = permit.debris_removal_end - permit.debris_removal_service_start
        else:
            # Fallback for old data
            stages['Debris Removal'] = permit.debris_removal_end - permit.debris_removal_request
    
    # Authorization (no waiting, just service time)
    if permit.authorization_start and permit.authorization_end:
        stages['Authorization'] = permit.authorization_end - permit.authorization_start
    
    # Plan preparation (no waiting, just service time)
    if permit.plan_prep_start and permit.plan_prep_end:
        stages['Plan Preparation'] = permit.plan_prep_end - permit.plan_prep_start
    
    # Planning department - separate waiting and service
    if permit.planning_request and permit.planning_end:
        if permit.planning_service_start:
            stages['Planning (Waiting)'] = permit.planning_service_start - permit.planning_request
            stages['Planning (Service)'] = permit.planning_end - permit.planning_service_start
        else:
            # Fallback for old data
            stages['Planning'] = permit.planning_end - permit.planning_request
    
    # Public Works - separate waiting and service
    if permit.public_works_request and permit.public_works_end:
        if permit.public_works_service_start:
            # Use cumulative waiting time if available (accounts for recheck waiting)
            if hasattr(permit, 'public_works_total_waiting') and permit.public_works_total_waiting > 0:
                stages['Public Works (Waiting)'] = permit.public_works_total_waiting
            else:
                # Fallback: use first service start time (doesn't account for recheck waiting)
                stages['Public Works (Waiting)'] = permit.public_works_service_start - permit.public_works_request
            stages['Public Works (Service)'] = permit.public_works_end - permit.public_works_service_start
        else:
            # Fallback for old data
            stages['Public Works'] = permit.public_works_end - permit.public_works_request
    
    # Fire review - separate waiting and service
    if permit.fire_review_request and permit.fire_review_end:
        if permit.fire_review_service_start:
            stages['Fire Review (Waiting)'] = permit.fire_review_service_start - permit.fire_review_request
            stages['Fire Review (Service)'] = permit.fire_review_end - permit.fire_review_service_start
        else:
            # Fallback for old data
            stages['Fire Review'] = permit.fire_review_end - permit.fire_review_request
    
    # Public Health review - separate waiting and service
    if permit.public_health_request and permit.public_health_end:
        if permit.public_health_service_start:
            stages['Public Health (Waiting)'] = permit.public_health_service_start - permit.public_health_request
            stages['Public Health (Service)'] = permit.public_health_end - permit.public_health_service_start
        else:
            # Fallback for old data
            stages['Public Health'] = permit.public_health_end - permit.public_health_request
    
    # Miscellaneous permits - separate waiting and service
    if permit.misc_request and permit.misc_end:
        if permit.misc_service_start:
            stages['Miscellaneous (Waiting)'] = permit.misc_service_start - permit.misc_request
            stages['Miscellaneous (Service)'] = permit.misc_end - permit.misc_service_start
        else:
            # Fallback for old data
            stages['Miscellaneous'] = permit.misc_end - permit.misc_request
    
    # Waiting time (gaps between stages)
    total_processing_time = permit.ready_for_construction - permit.created_at if permit.ready_for_construction else None
    if total_processing_time:
        accounted_time = sum(stages.values())
        waiting_time = total_processing_time - accounted_time
        if waiting_time > 0:
            stages['Other Waiting'] = waiting_time
    
    return stages


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
    
    # Define stage order and colors (waiting times are lighter/dashed, service times are solid)
    stage_order = [
        'Debris Removal (Waiting)',
        'Debris Removal (Service)',
        'Authorization',
        'Plan Preparation',
        'Planning (Waiting)',
        'Planning (Service)',
        'Public Works (Waiting)',
        'Public Works (Service)',
        'Fire Review (Waiting)',
        'Fire Review (Service)',
        'Public Health (Waiting)',
        'Public Health (Service)',
        'Miscellaneous (Waiting)',
        'Miscellaneous (Service)',
        'Other Waiting',
        # Legacy names for backward compatibility
        'Debris Removal',
        'Planning',
        'Public Works',
        'Fire Review',
        'Public Health',
        'Miscellaneous',
        'Waiting/Other'
    ]
    
    colors = {
        # Waiting times (lighter colors)
        'Debris Removal (Waiting)': '#FFB3B3',
        'Planning (Waiting)': '#FFD4B3',
        'Public Works (Waiting)': '#C8E8D8',
        'Fire Review (Waiting)': '#FBF3B3',
        'Public Health (Waiting)': '#E0C8E8',
        'Miscellaneous (Waiting)': '#D4A5A5',
        'Other Waiting': '#E0E0E0',
        # Service times (darker colors)
        'Debris Removal (Service)': '#FF6B6B',
        'Planning (Service)': '#FFA07A',
        'Public Works (Service)': '#98D8C8',
        'Fire Review (Service)': '#F7DC6F',
        'Public Health (Service)': '#BB8FCE',
        'Miscellaneous (Service)': '#C08080',
        # Stages without waiting (service only)
        'Authorization': '#4ECDC4',
        'Plan Preparation': '#45B7D1',
        # Legacy names
        'Debris Removal': '#FF6B6B',
        'Planning': '#FFA07A',
        'Public Works': '#98D8C8',
        'Fire Review': '#F7DC6F',
        'Public Health': '#BB8FCE',
        'Miscellaneous': '#C08080',
        'Waiting/Other': '#D3D3D3'
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
    
    for stage in stage_order:
        values = stage_data[stage]
        if any(v > 0 for v in values):  # Only plot if there are non-zero values
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


def plot_gantt_chart(permits: List[Permit], max_permits: int = 30, figsize=(14, 10)):
    """
    Create a Gantt chart showing the timeline of each permit through the process.
    
    Args:
        permits: List of Permit objects
        max_permits: Maximum number of permits to display
        figsize: Figure size tuple
    """
    display_permits = permits[:max_permits]
    
    # Define stages and colors - format: (name, request_attr, service_start_attr, end_attr, waiting_color, service_color)
    stages_info = [
        ('Debris Removal', 'debris_removal_request', 'debris_removal_service_start', 'debris_removal_end', '#FFB3B3', '#FF6B6B'),
        ('Authorization', 'authorization_start', None, 'authorization_end', None, '#4ECDC4'),
        ('Plan Preparation', 'plan_prep_start', None, 'plan_prep_end', None, '#45B7D1'),
        ('Planning', 'planning_request', 'planning_service_start', 'planning_end', '#FFD4B3', '#FFA07A'),
        ('Public Works', 'public_works_request', 'public_works_service_start', 'public_works_end', '#C8E8D8', '#98D8C8'),
        ('Fire Review', 'fire_review_request', 'fire_review_service_start', 'fire_review_end', '#FBF3B3', '#F7DC6F'),
        ('Public Health', 'public_health_request', 'public_health_service_start', 'public_health_end', '#E0C8E8', '#BB8FCE'),
        ('Miscellaneous', 'misc_request', 'misc_service_start', 'misc_end', '#D4A5A5', '#C08080'),
    ]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    y_positions = list(range(len(display_permits)))
    y_labels = [f"Permit {p.permit_id} ({p.segment.name})" for p in display_permits]
    
    # Plot each stage for each permit
    for i, permit in enumerate(display_permits):
        y_pos = len(display_permits) - i - 1
        
        # Track the last end time to identify gaps
        last_end_time = permit.created_at
        
        for stage_info in stages_info:
            if len(stage_info) == 5:
                # Old format (backward compatibility)
                stage_name, start_attr, end_attr, color = stage_info[:4]
                start_time = getattr(permit, start_attr, None)
                end_time = getattr(permit, end_attr, None)
                
                if start_time is not None and end_time is not None:
                    # Show gap before this stage if there is one
                    if start_time > last_end_time + 0.01:  # Small threshold to avoid tiny gaps
                        gap_duration = start_time - last_end_time
                        ax.barh(y_pos, gap_duration, left=last_end_time, height=0.6,
                               color='#FFD4B3', alpha=0.6, edgecolor='black', 
                               linewidth=0.5, hatch='///', label='Waiting/Gap (between stages)' if i == 0 and stage_info == stages_info[0] else '')
                    
                    duration = end_time - start_time
                    if duration > 0:
                        ax.barh(y_pos, duration, left=start_time, height=0.6,
                               color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
                    
                    # Update last_end_time
                    last_end_time = max(last_end_time, end_time)
            else:
                # New format with waiting/service separation
                stage_name, request_attr, service_start_attr, end_attr, waiting_color, service_color = stage_info
                
                request_time = getattr(permit, request_attr, None)
                service_start_time = getattr(permit, service_start_attr, None) if service_start_attr else None
                end_time = getattr(permit, end_attr, None)
                
                if request_time is not None and end_time is not None:
                    # Show gap before this stage if there is one
                    if request_time > last_end_time + 0.01:  # Small threshold to avoid tiny gaps
                        gap_duration = request_time - last_end_time
                        ax.barh(y_pos, gap_duration, left=last_end_time, height=0.6,
                               color='#FFD4B3', alpha=0.6, edgecolor='black', 
                               linewidth=0.5, hatch='///', label='Waiting/Gap (between stages)' if i == 0 and stage_info == stages_info[0] else '')
                    
                    if service_start_attr and service_start_time is not None:
                        # Show waiting time and service time separately
                        waiting_duration = service_start_time - request_time
                        service_duration = end_time - service_start_time
                        
                        if waiting_duration > 0:
                            ax.barh(y_pos, waiting_duration, left=request_time, height=0.6,
                                   color=waiting_color, alpha=0.6, edgecolor='black', 
                                   linewidth=0.5, hatch='///', label=f'{stage_name} (Waiting)' if i == 0 else '')
                        if service_duration > 0:
                            ax.barh(y_pos, service_duration, left=service_start_time, height=0.6,
                                   color=service_color, alpha=0.8, edgecolor='black', linewidth=0.5,
                                   label=f'{stage_name} (Service)' if i == 0 else '')
                    else:
                        # No service start time (backward compatibility or no waiting)
                        duration = end_time - request_time
                        if duration > 0:
                            ax.barh(y_pos, duration, left=request_time, height=0.6,
                                   color=service_color, alpha=0.8, edgecolor='black', linewidth=0.5)
                    
                    # Update last_end_time to the end of this stage
                    last_end_time = max(last_end_time, end_time)
    
    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels)
    ax.set_xlabel('Time (days)', fontsize=12)
    ax.set_title(f'Gantt Chart: Permit Processing Timeline (showing {len(display_permits)} permits)',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    # Create legend - collect unique labels
    legend_elements = []
    seen_labels = set()
    for stage_info in stages_info:
        if len(stage_info) == 5:
            # Old format
            stage_name, _, _, color = stage_info[:4]
            label = stage_name
        else:
            # New format - create separate entries for waiting and service
            stage_name = stage_info[0]
            waiting_color = stage_info[4]
            service_color = stage_info[5]
            
            if waiting_color and f'{stage_name} (Waiting)' not in seen_labels:
                legend_elements.append(mpatches.Patch(facecolor=waiting_color, alpha=0.6, 
                                                     hatch='///', label=f'{stage_name} (Waiting)'))
                seen_labels.add(f'{stage_name} (Waiting)')
            
            if service_color and f'{stage_name} (Service)' not in seen_labels:
                legend_elements.append(mpatches.Patch(facecolor=service_color, alpha=0.8, 
                                                     label=f'{stage_name} (Service)'))
                seen_labels.add(f'{stage_name} (Service)')
            continue
        
        # Add gap/waiting label if not already added
        if 'Waiting/Gap (between stages)' not in seen_labels:
            legend_elements.append(mpatches.Patch(facecolor='#FFD4B3', alpha=0.6, 
                                                 edgecolor='black', hatch='///',
                                                 label='Waiting/Gap (between stages)'))
            seen_labels.add('Waiting/Gap (between stages)')
        
        if label not in seen_labels:
            legend_elements.append(mpatches.Patch(facecolor=color, alpha=0.8, label=label))
            seen_labels.add(label)
    
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    
    plt.tight_layout()
    
    return fig, ax


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
        'Debris Removal (Waiting)': '#FFB3B3',
        'Planning (Waiting)': '#FFD4B3',
        'Public Works (Waiting)': '#C8E8D8',
        'Fire Review (Waiting)': '#FBF3B3',
        'Public Health (Waiting)': '#E0C8E8',
        'Miscellaneous (Waiting)': '#D4A5A5',
        'Other Waiting': '#E0E0E0',
        # Service times (darker colors)
        'Debris Removal (Service)': '#FF6B6B',
        'Planning (Service)': '#FFA07A',
        'Public Works (Service)': '#98D8C8',
        'Fire Review (Service)': '#F7DC6F',
        'Public Health (Service)': '#BB8FCE',
        'Miscellaneous (Service)': '#C08080',
        # Stages without waiting (service only)
        'Authorization': '#4ECDC4',
        'Plan Preparation': '#45B7D1',
        # Legacy names
        'Debris Removal': '#FF6B6B',
        'Planning': '#FFA07A',
        'Public Works': '#98D8C8',
        'Fire Review': '#F7DC6F',
        'Public Health': '#BB8FCE',
        'Miscellaneous': '#C08080',
        'Waiting/Other': '#D3D3D3'
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
    
    # Filter out stages with zero average
    stage_averages = {k: v for k, v in stage_averages.items() if v > 0}
    
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
        'Debris Removal (Waiting)',
        'Debris Removal (Service)',
        'Authorization',
        'Plan Preparation',
        'Planning (Waiting)',
        'Planning (Service)',
        'Public Works (Waiting)',
        'Public Works (Service)',
        'Fire Review (Waiting)',
        'Fire Review (Service)',
        'Public Health (Waiting)',
        'Public Health (Service)',
        # Legacy names for backward compatibility
        'Debris Removal',
        'Planning',
        'Public Works',
        'Fire Review',
        'Public Health',
    ]
    
    # Filter to only stages with data, maintaining preferred order
    stage_order = [s for s in preferred_order if s in all_stages]
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
        Segment.PRE_APPROVED_LIKE: '#FF6B6B',
        Segment.PRE_APPROVED_NON_LIKE: '#FF8E8E',
        Segment.CUSTOM_LIKE: '#4ECDC4',
        Segment.CUSTOM_NON_LIKE: '#6EDDD6',
        Segment.SELF_CERT_LIKE: '#45B7D1',
        Segment.SELF_CERT_NON_LIKE: '#6BC5D8',
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
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#BB8FCE']
        for patch, color in zip(bp['boxes'], colors[:len(segments)]):
            patch.set_facecolor(color)
        
        # Add sample size (n)
        for i, s in enumerate(segments):
            count = len(segment_data[s])
            y_pos = np.median(data[i])  # Position near the median
            ax.text(i + 1, np.max(data[i]) + 0.05 * (np.max(data[i]) - np.min(data[i])), f'n={count}',
                    horizontalalignment='center', verticalalignment='bottom', fontsize=9, color='gray')
        
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


def visualize_all(permits: List[Permit], save_prefix: str = None):
    """
    Create all visualizations and optionally save them.
    
    Args:
        permits: List of Permit objects
        save_prefix: If provided, save figures with this prefix
    """
    print(f"Creating visualizations for {len(permits)} permits...")
    
    # 1. Stacked bar chart
    print("  Creating stacked bar chart...")
    fig1, _ = plot_stacked_bar_chart(permits, max_permits=50)
    if save_prefix:
        fig1.savefig(f"{save_prefix}_stacked_bar.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_stacked_bar.png")
    
    # 2. Gantt chart
    print("  Creating Gantt chart...")
    fig2, _ = plot_gantt_chart(permits, max_permits=30)
    if save_prefix:
        fig2.savefig(f"{save_prefix}_gantt.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_gantt.png")
    
    # 3. Average time by stage
    print("  Creating average time by stage chart...")
    fig3, _ = plot_average_time_by_stage(permits)
    if save_prefix:
        fig3.savefig(f"{save_prefix}_average_by_stage.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_average_by_stage.png")
    
    # 4. Time by segment
    print("  Creating time by segment chart...")
    fig4, _ = plot_time_by_segment(permits)
    if save_prefix:
        fig4.savefig(f"{save_prefix}_by_segment.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_by_segment.png")
    
    # 5. Total time by segment
    print("  Creating total time by segment chart...")
    fig5, _ = plot_total_time_by_segment(permits)
    if save_prefix and fig5:
        fig5.savefig(f"{save_prefix}_total_time_by_segment.png", dpi=300, bbox_inches='tight')
        print(f"    Saved: {save_prefix}_total_time_by_segment.png")
    
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

