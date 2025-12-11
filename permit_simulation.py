"""
Discrete Event Simulation of Post-Disaster Permitting Process
Using SimPy to model the workflow from fire event to construction readiness.
"""

import simpy
import random
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
import statistics


class Segment(Enum):
    """Permit segments based on plan type and likeness."""
    PRE_APPROVED_LIKE = 1  # Pre-approved plan, Like-for-like
    PRE_APPROVED_NON_LIKE = 2  # Pre-approved plan, Non-like-for-like
    CUSTOM_LIKE = 3  # Custom build, Like-for-like
    CUSTOM_NON_LIKE = 4  # Custom build, Non-like-for-like
    SELF_CERT_LIKE = 5  # Custom build w/ self-certification, Like-for-like
    SELF_CERT_NON_LIKE = 6  # Custom build w/ self-certification, Non-like-for-like


@dataclass
class Permit:
    """Represents a permit application in the system."""
    permit_id: int
    segment: Segment
    created_at: float
    # Timestamps for tracking
    debris_removal_start: Optional[float] = None
    debris_removal_end: Optional[float] = None
    authorization_start: Optional[float] = None
    authorization_end: Optional[float] = None
    plan_prep_start: Optional[float] = None
    plan_prep_end: Optional[float] = None
    planning_start: Optional[float] = None
    planning_end: Optional[float] = None
    public_works_start: Optional[float] = None
    public_works_end: Optional[float] = None
    fire_review_start: Optional[float] = None
    fire_review_end: Optional[float] = None
    public_health_start: Optional[float] = None
    public_health_end: Optional[float] = None
    ready_for_construction: Optional[float] = None
    # Tracking
    public_works_rechecks: int = 0
    public_works_approved: Optional[bool] = None


class PermitSimulation:
    """Main simulation class for the permitting process."""
    
    def __init__(self, env: simpy.Environment, random_seed: int = 42):
        self.env = env
        self.random_seed = random_seed
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        # Resource pools
        self.epa_debris_servers = simpy.Resource(env, capacity=140)
        self.usace_debris_servers = simpy.Resource(env, capacity=140)
        self.planning_servers = simpy.Resource(env, capacity=25)
        self.public_works_servers = simpy.Resource(env, capacity=25)
        self.fire_servers = simpy.Resource(env, capacity=25)
        self.public_health_servers = simpy.Resource(env, capacity=25)
        
        # Statistics
        self.completed_permits: List[Permit] = []
        self.in_progress_permits: Dict[int, Permit] = {}
        self.permit_counter = 0
        
    def sample_segment(self) -> Segment:
        """Sample a permit segment based on distribution.
        Currently ~80% like-for-like, ~20% non-like-for-like.
        Distribution across plan types not specified, using uniform.
        """
        is_like_for_like = random.random() < 0.80
        
        # Randomly assign plan type (could be adjusted based on actual distribution)
        plan_type = random.choices(
            ['pre_approved', 'custom', 'self_cert'],
            weights=[1, 1, 1]  # Equal weights, adjust as needed
        )[0]
        
        if plan_type == 'pre_approved':
            return Segment.PRE_APPROVED_LIKE if is_like_for_like else Segment.PRE_APPROVED_NON_LIKE
        elif plan_type == 'custom':
            return Segment.CUSTOM_LIKE if is_like_for_like else Segment.CUSTOM_NON_LIKE
        else:  # self_cert
            return Segment.SELF_CERT_LIKE if is_like_for_like else Segment.SELF_CERT_NON_LIKE
    
    def sample_normal(self, mean: float, std: float) -> float:
        """Sample from normal distribution, ensuring non-negative."""
        return max(0, np.random.normal(mean, std))
    
    def sample_lognormal(self, median: float, sigma: float) -> float:
        """Sample from lognormal distribution with given median and sigma."""
        # Convert median to mu for lognormal
        mu = np.log(median)
        return max(0, np.random.lognormal(mu, sigma))
    
    def sample_uniform_days(self) -> float:
        """Sample uniform: 2 or 3 days, each with 50% probability."""
        days = random.choice([2, 3])
        return days * 24  # Convert to hours
    
    def epa_debris_removal(self, permit: Permit):
        """EPA Debris Removal (Phase 1)."""
        permit.debris_removal_start = self.env.now
        with self.epa_debris_servers.request() as request:
            yield request
            # Uniform: 2 or 3 days, each with 50% probability
            duration = self.sample_uniform_days()
            yield self.env.timeout(duration)
        permit.debris_removal_end = self.env.now
    
    def usace_debris_removal(self, permit: Permit):
        """USACE Debris Removal (Phase 2)."""
        with self.usace_debris_servers.request() as request:
            yield request
            # Uniform: 2 or 3 days, each with 50% probability
            duration = self.sample_uniform_days()
            yield self.env.timeout(duration)
    
    def securing_authorization(self, permit: Permit):
        """Securing authorization & funding to rebuild."""
        permit.authorization_start = self.env.now
        # N(42, 20) in days, convert to hours
        duration_days = self.sample_normal(42, 20)
        yield self.env.timeout(duration_days * 24)
        permit.authorization_end = self.env.now
    
    def prepare_submit_plans(self, permit: Permit):
        """Prepare & submit plans."""
        permit.plan_prep_start = self.env.now
        
        # Segments 1 & 2 (pre-approved plan) → N(10, 2) days
        # Segments 3-6 (custom-builds) → lognormal dist with median 150 and sigma = 0.6 days
        if permit.segment in [Segment.PRE_APPROVED_LIKE, Segment.PRE_APPROVED_NON_LIKE]:
            duration_days = self.sample_normal(10, 2)
        else:  # Segments 3-6
            duration_days = self.sample_lognormal(150, 0.6)
        
        yield self.env.timeout(duration_days * 24)
        permit.plan_prep_end = self.env.now
    
    def planning_department(self, permit: Permit):
        """Planning department processing.
        Segments 5&6 (self-certification) skip this step entirely.
        """
        if permit.segment in [Segment.SELF_CERT_LIKE, Segment.SELF_CERT_NON_LIKE]:
            # Skip planning department
            return
        
        permit.planning_start = self.env.now
        with self.planning_servers.request() as request:
            yield request
            
            # Segments 2 & 4 (non-like-for-like) - N(33, 10) days
            # Segments 1 & 3 (like-for-like) - N(3, 1) days
            if permit.segment in [Segment.PRE_APPROVED_NON_LIKE, Segment.CUSTOM_NON_LIKE]:
                duration_days = self.sample_normal(33, 10)
            else:  # Segments 1 & 3
                duration_days = self.sample_normal(3, 1)
            
            yield self.env.timeout(duration_days * 24)
        permit.planning_end = self.env.now
    
    def public_works_initial_check(self, permit: Permit):
        """Public works (Building & Safety) Initial Check.
        Only segments 3-6 (non-pre-approved) go through this step.
        Sets permit.public_works_approved to True if approved, False if needs re-check.
        """
        if permit.segment in [Segment.PRE_APPROVED_LIKE, Segment.PRE_APPROVED_NON_LIKE]:
            # Pre-approved plans skip initial check
            permit.public_works_approved = True
            return
        
        permit.public_works_start = self.env.now
        with self.public_works_servers.request() as request:
            yield request
            # N(11.6, 2) days
            duration_days = self.sample_normal(11.6, 2)
            yield self.env.timeout(duration_days * 24)
        
        # 75% approved, 25% need re-check
        approved = random.random() < 0.75
        permit.public_works_approved = approved
        
        if approved:
            permit.public_works_end = self.env.now
        else:
            permit.public_works_rechecks += 1
    
    def public_works_recheck(self, permit: Permit):
        """Public works (Building & Safety) Re-check."""
        with self.public_works_servers.request() as request:
            yield request
            # N(8.3, 2) days
            duration_days = self.sample_normal(8.3, 2)
            yield self.env.timeout(duration_days * 24)
        
        # 75% approved, 25% need re-check again
        approved = random.random() < 0.75
        permit.public_works_approved = approved
        
        if approved:
            permit.public_works_end = self.env.now
        else:
            permit.public_works_rechecks += 1
    
    def fire_review(self, permit: Permit):
        """Fire department review (30% of permits, low confidence)."""
        permit.fire_review_start = self.env.now
        with self.fire_servers.request() as request:
            yield request
            # N(13, 2) days
            duration_days = self.sample_normal(13, 2)
            yield self.env.timeout(duration_days * 24)
        permit.fire_review_end = self.env.now
    
    def public_health_review(self, permit: Permit):
        """Public Health department review (1.3% of permits)."""
        permit.public_health_start = self.env.now
        with self.public_health_servers.request() as request:
            yield request
            # N(10, 2) days - low confidence
            duration_days = self.sample_normal(10, 2)
            yield self.env.timeout(duration_days * 24)
        permit.public_health_end = self.env.now
    
    def permit_process(self, permit: Permit):
        """Main process flow for a single permit."""
        # Two parallel paths from fire event:
        # Path 1: Debris removal
        debris_process = self.env.process(self.debris_removal_path(permit))
        
        # Path 2: Authorization and plan preparation
        auth_process = self.env.process(self.authorization_path(permit))
        
        # Wait for both paths to complete
        yield debris_process & auth_process
        
        # Planning department (skipped for segments 5&6)
        yield self.env.process(self.planning_department(permit))
        
        # Public Works (Building & Safety)
        # Pre-approved plans skip initial check
        if permit.segment not in [Segment.PRE_APPROVED_LIKE, Segment.PRE_APPROVED_NON_LIKE]:
            yield self.env.process(self.public_works_initial_check(permit))
            
            # Re-check loop if not approved
            while not permit.public_works_approved:
                yield self.env.process(self.public_works_recheck(permit))
        else:
            # Pre-approved plans are automatically approved
            permit.public_works_start = self.env.now
            permit.public_works_end = self.env.now
            permit.public_works_approved = True
        
        # Parallel reviews after approval
        review_processes = []
        
        # Fire review: 30% of permits
        if random.random() < 0.30:
            review_processes.append(self.env.process(self.fire_review(permit)))
        
        # Public Health review: 1.3% of permits
        if random.random() < 0.013:
            review_processes.append(self.env.process(self.public_health_review(permit)))
        
        # Wait for all reviews to complete
        if review_processes:
            yield simpy.AllOf(self.env, review_processes)
        
        # Ready for construction
        permit.ready_for_construction = self.env.now
        self.completed_permits.append(permit)
        if permit.permit_id in self.in_progress_permits:
            del self.in_progress_permits[permit.permit_id]
    
    def debris_removal_path(self, permit: Permit):
        """Debris removal path: EPA → USACE."""
        yield self.env.process(self.epa_debris_removal(permit))
        yield self.env.process(self.usace_debris_removal(permit))
    
    def authorization_path(self, permit: Permit):
        """Authorization and plan preparation path."""
        yield self.env.process(self.securing_authorization(permit))
        yield self.env.process(self.prepare_submit_plans(permit))
    
    def create_permit(self) -> Permit:
        """Create a new permit with a sampled segment."""
        self.permit_counter += 1
        permit = Permit(
            permit_id=self.permit_counter,
            segment=self.sample_segment(),
            created_at=self.env.now
        )
        self.in_progress_permits[permit.permit_id] = permit
        return permit
    
    def get_statistics(self) -> Dict:
        """Calculate and return simulation statistics."""
        if not self.completed_permits:
            return {"message": "No permits completed yet"}
        
        stats = {
            "total_completed": len(self.completed_permits),
            "total_in_progress": len(self.in_progress_permits),
            "segment_distribution": {},
            "average_total_time": {},
            "average_times_by_segment": {},
        }
        
        # Segment distribution
        for segment in Segment:
            count = sum(1 for p in self.completed_permits if p.segment == segment)
            stats["segment_distribution"][segment.name] = count
        
        # Calculate total processing times
        total_times = []
        for permit in self.completed_permits:
            if permit.ready_for_construction:
                total_time = permit.ready_for_construction - permit.created_at
                total_times.append(total_time)
        
        if total_times:
            stats["average_total_time"] = {
                "mean": statistics.mean(total_times),
                "median": statistics.median(total_times),
                "std": statistics.stdev(total_times) if len(total_times) > 1 else 0,
                "min": min(total_times),
                "max": max(total_times),
            }
        
        # Times by segment
        for segment in Segment:
            segment_permits = [p for p in self.completed_permits if p.segment == segment]
            if segment_permits:
                segment_times = [
                    p.ready_for_construction - p.created_at
                    for p in segment_permits
                    if p.ready_for_construction
                ]
                if segment_times:
                    stats["average_times_by_segment"][segment.name] = {
                        "mean": statistics.mean(segment_times),
                        "median": statistics.median(segment_times),
                        "count": len(segment_times),
                    }
        
        # Re-check statistics
        recheck_counts = [p.public_works_rechecks for p in self.completed_permits]
        stats["public_works_rechecks"] = {
            "average": statistics.mean(recheck_counts) if recheck_counts else 0,
            "max": max(recheck_counts) if recheck_counts else 0,
            "total_permits_with_rechecks": sum(1 for c in recheck_counts if c > 0),
        }
        
        return stats

