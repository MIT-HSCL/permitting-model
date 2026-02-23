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
    # Timestamps for tracking (request time, service start, service end)
    # Debris removal
    debris_removal_request: Optional[float] = None
    debris_removal_service_start: Optional[float] = None
    debris_removal_end: Optional[float] = None
    # Debris removal (separate EPA vs USACE)
    epa_debris_request: Optional[float] = None
    epa_debris_service_start: Optional[float] = None
    epa_debris_end: Optional[float] = None
    epa_debris_total_waiting: float = 0.0
    usace_debris_request: Optional[float] = None
    usace_debris_service_start: Optional[float] = None
    usace_debris_end: Optional[float] = None
    usace_debris_total_waiting: float = 0.0
    # Authorization (no waiting, just service time)
    authorization_start: Optional[float] = None
    authorization_end: Optional[float] = None
    # Plan preparation (no waiting, just service time)
    plan_prep_start: Optional[float] = None
    plan_prep_end: Optional[float] = None
    # Planning department
    planning_request: Optional[float] = None
    planning_service_start: Optional[float] = None
    planning_end: Optional[float] = None
    planning_total_waiting: float = 0.0  # Cumulative waiting time across all rereviews
    planning_rechecks: int = 0
    planning_initial_waiting: float = 0.0
    planning_initial_service: float = 0.0
    planning_recheck_waiting: float = 0.0
    planning_recheck_service: float = 0.0
    # Public Works
    public_works_request: Optional[float] = None
    public_works_service_start: Optional[float] = None  # First service start (for waiting time calculation)
    public_works_end: Optional[float] = None
    public_works_total_waiting: float = 0.0  # Cumulative waiting time across all checks/rechecks
    public_works_rechecks: int = 0
    public_works_initial_waiting: float = 0.0
    public_works_initial_service: float = 0.0
    public_works_recheck_waiting: float = 0.0
    public_works_recheck_service: float = 0.0
    # Fire review
    fire_review_request: Optional[float] = None
    fire_review_service_start: Optional[float] = None
    fire_review_end: Optional[float] = None
    fire_review_total_waiting: float = 0.0  # Cumulative waiting time across all rereviews
    fire_rechecks: int = 0
    fire_initial_waiting: float = 0.0
    fire_initial_service: float = 0.0
    fire_recheck_waiting: float = 0.0
    fire_recheck_service: float = 0.0
    # Public Health review
    public_health_request: Optional[float] = None
    public_health_service_start: Optional[float] = None
    public_health_end: Optional[float] = None
    public_health_total_waiting: float = 0.0  # Cumulative waiting time across all rereviews
    public_health_rechecks: int = 0
    public_health_initial_waiting: float = 0.0
    public_health_initial_service: float = 0.0
    public_health_recheck_waiting: float = 0.0
    public_health_recheck_service: float = 0.0
    # Agency Referrals permits
    misc_request: Optional[float] = None
    misc_service_start: Optional[float] = None
    misc_end: Optional[float] = None
    # Final
    ready_for_construction: Optional[float] = None


class PermitSimulation:
    """Main simulation class for the permitting process."""
    
    def __init__(
        self,
        env: simpy.Environment,
        random_seed: int = 42,
        ai_review: str = "none",
        pct_pre_approved: float = 0.02,
        pct_custom: float = 0.90,
        pct_self_cert: float = 0.08,
        pct_like_for_like: float = 0.80,

    ):
        """
        Initialize the simulation.

        Args:
            env: SimPy Environment.
            random_seed: Random seed for reproducibility.
            ai_review: AI review mode: "none", "initial_check", "full_review".
            pct_pre_approved: Share of permits that are pre-approved plans (0–1 fraction).
            pct_custom: Share of permits that are custom builds (0–1 fraction).
            pct_self_cert: Share of permits that are self-certification (0–1 fraction).
            pct_like_for_like: Share of permits that are like-for-like (0–1 fraction).

        Notes:
            - pct_pre_approved + pct_custom + pct_self_cert do not have to sum to 1.0
              exactly; they are used as weights and normalized internally.
            - pct_like_for_like controls the global probability that a permit is
              like-for-like vs non-like-for-like across all plan types.
        """
        self.env = env
        self.random_seed = random_seed
        self.ai_review = ai_review
        random.seed(random_seed)
        np.random.seed(random_seed)

        # Store segment mix parameters
        self.pct_pre_approved = pct_pre_approved
        self.pct_custom = pct_custom
        self.pct_self_cert = pct_self_cert
        self.pct_like_for_like = pct_like_for_like
        
        # Resource pools
        self.epa_debris_servers = simpy.Resource(env, capacity=160)
        self.usace_debris_servers = simpy.Resource(env, capacity=116)
        self.planning_servers = simpy.PriorityResource(env, capacity=100)  # 20 servers × 5 permits each
        self.public_works_servers = simpy.PriorityResource(env, capacity=200) # 40 servers x 5 permits each
        self.fire_servers = simpy.PriorityResource(env, capacity=100)
        self.public_health_servers = simpy.PriorityResource(env, capacity=25)
        self.misc_servers = simpy.Resource(env, capacity=1000)
        
        # Statistics
        self.completed_permits: List[Permit] = []
        self.in_progress_permits: Dict[int, Permit] = {}
        self.permit_counter = 0
        
    def sample_segment(self) -> Segment:
        """
        Sample a permit segment based on configured distributions.

        By default this reproduces the previous behavior:
        ~80% like-for-like vs 20% non-like-for-like, and
        plan types split roughly as:
            - 2% pre-approved
            - 90% custom
            - 8% self-certification.

        These proportions can be overridden via the constructor or through
        the `run_simulation` helper.
        """
        # Like-for-like vs non-like-for-like
        is_like_for_like = random.random() < self.pct_like_for_like
        
        # Plan type: pre_approved, custom, or self_cert
        plan_type = random.choices(
            ['pre_approved', 'custom', 'self_cert'],
            weights=[self.pct_pre_approved, self.pct_custom, self.pct_self_cert],
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
        return random.choice([2, 3])
    
    def epa_debris_removal(self, permit: Permit):
        """EPA Debris Removal (Phase 1)."""
        permit.debris_removal_request = self.env.now
        permit.epa_debris_request = self.env.now
        request_time = self.env.now
        with self.epa_debris_servers.request() as request:
            yield request
            permit.debris_removal_service_start = self.env.now
            permit.epa_debris_service_start = self.env.now
            permit.epa_debris_total_waiting += (permit.epa_debris_service_start - request_time)
            # Uniform: 2 or 3 days, each with 50% probability
            duration = self.sample_uniform_days()
            yield self.env.timeout(duration)
        permit.epa_debris_end = self.env.now
        # Note: debris_removal_end will be set after USACE completes
    
    def usace_debris_removal(self, permit: Permit):
        """USACE Debris Removal (Phase 2)."""
        # USACE follows immediately after EPA
        permit.usace_debris_request = self.env.now
        request_time = self.env.now
        with self.usace_debris_servers.request() as request:
            yield request
            permit.usace_debris_service_start = self.env.now
            permit.usace_debris_total_waiting += (permit.usace_debris_service_start - request_time)
            # Uniform: 2 or 3 days, each with 50% probability
            duration = self.sample_uniform_days()
            yield self.env.timeout(duration)
        permit.usace_debris_end = self.env.now
        # Set end time after both EPA and USACE phases complete
        permit.debris_removal_end = self.env.now
    
    def securing_authorization(self, permit: Permit):
        """Securing authorization & funding to rebuild."""
        permit.authorization_start = self.env.now
        # N(42, 20) days
        duration_days = self.sample_normal(42, 20)
        yield self.env.timeout(duration_days)
        permit.authorization_end = self.env.now
    
    def prepare_submit_plans(self, permit: Permit):
        """Prepare & submit plans."""
        permit.plan_prep_start = self.env.now
        
        # Segments 1 & 2 (pre-approved plan) → N(10, 2) days
        # Segments 3-6 (custom-builds) → lognormal dist with median 150 and sigma = 0.6 days
        if permit.segment in [Segment.PRE_APPROVED_LIKE, Segment.PRE_APPROVED_NON_LIKE]:
            duration_days = self.sample_normal(30, 20)
        else:  # Segments 3-6
            duration_days = self.sample_lognormal(150, 0.6)
        
        yield self.env.timeout(duration_days)
        permit.plan_prep_end = self.env.now
    
    def planning_department(self, permit: Permit):
        """Planning department processing with approval/recheck logic.
        """
        is_initial = permit.planning_rechecks == 0
        if is_initial and permit.planning_request is None:
            permit.planning_request = self.env.now
        request_time = self.env.now

        priority = 1 if permit.planning_rechecks == 0 else 0
        with self.planning_servers.request(priority=priority) as request:
            yield request
            service_start_time = self.env.now
            if is_initial:
                permit.planning_service_start = service_start_time
            permit.planning_total_waiting += (service_start_time - request_time)
            if is_initial:
                permit.planning_initial_waiting += (service_start_time - request_time)
            else:
                permit.planning_recheck_waiting += (service_start_time - request_time)
            # Segments 2 & 4 (non-like-for-like) - N(9, 2) days
            # Segments 1 & 3 (like-for-like) - N(3, 1) days
            if is_initial:
                if permit.segment in [Segment.PRE_APPROVED_NON_LIKE, Segment.CUSTOM_NON_LIKE, Segment.SELF_CERT_NON_LIKE]:
                    duration_days = self.sample_normal(3, 1)
                else:  # like-for-like
                   duration_days = self.sample_normal(2, 0.5)
                if self.ai_review == "initial_check":
                    duration_days = duration_days * 0.7
                elif self.ai_review == "full_review":
                    duration_days = duration_days * 0.1
            else:
                # Recheck uses shorter time
                if self.ai_review == "full_review":
                    duration_days = self.sample_normal(1, 0.2)
                else:
                    duration_days = self.sample_normal(2, 0.5)
            
            yield self.env.timeout(duration_days)
            service_end_time = self.env.now
            if is_initial:
                permit.planning_initial_service += (service_end_time - service_start_time)
            else:
                permit.planning_recheck_service += (service_end_time - service_start_time)
        
        if permit.planning_rechecks == 0:
            # 25% approved, 75% need re-check
            approved = random.random() < 0.25
            is_initial = False
        else:
            # 95% approved, 5% need re-check if has already been rechecked
            approved = random.random() < 0.95

        if approved:
            permit.planning_end = self.env.now
        else:
            permit.planning_rechecks += 1

        return approved

    def misc_permits(self, permit: Permit):
        """Agency Referrals permits administered by various other departments.
        Segments 1, 3, and 5 (like-for-like) skip this step entirely.
        """
        if permit.segment in [Segment.PRE_APPROVED_LIKE, Segment.CUSTOM_LIKE, Segment.SELF_CERT_LIKE]:
            # Skip agency referrals if like-for-like
            return
        
        permit.misc_request = self.env.now
        with self.misc_servers.request() as request:
            yield request
            permit.misc_service_start = self.env.now
            # lognormal 30, sigma 0.7 days days
            duration_days = self.sample_lognormal(30, 0.7)
            yield self.env.timeout(duration_days)
        permit.misc_end = self.env.now
    
    def public_works(self, permit: Permit):
        """Public works (Building & Safety) Initial Check.
        Segments 3-6 (non-pre-approved) take longer.
        Sets permit.public_works_approved to True if approved, False if needs re-check.
        """
        is_initial = permit.public_works_rechecks == 0
        if is_initial and permit.public_works_request is None:
            permit.public_works_request = self.env.now
        request_time = self.env.now

        priority = 1 if permit.public_works_rechecks == 0 else 0
        with self.public_works_servers.request(priority=priority) as request:
            yield request
            service_start_time = self.env.now
            if is_initial:
                permit.public_works_service_start = service_start_time  # Track first service start
            permit.public_works_total_waiting += (service_start_time - request_time)  # Track cumulative waiting
            if is_initial:
                permit.public_works_initial_waiting += (service_start_time - request_time)
            else:
                permit.public_works_recheck_waiting += (service_start_time - request_time)
            duration_days = self.sample_normal(8, 2)
            duration_days_pre_approved = self.sample_normal(1, 0.5)
            duration_days_recheck = self.sample_normal(1, 0.5)
            if is_initial:
                if permit.segment in [Segment.PRE_APPROVED_LIKE, Segment.PRE_APPROVED_NON_LIKE, Segment.SELF_CERT_LIKE, Segment.SELF_CERT_NON_LIKE]:
                    if self.ai_review == "initial_check":
                        duration_days_pre_approved = duration_days_pre_approved * 0.7
                    elif self.ai_review == "full_review":
                        duration_days_pre_approved = duration_days_pre_approved * 0.1
                    yield self.env.timeout(duration_days_pre_approved)
                else:
                    if self.ai_review == "initial_check":
                        duration_days = duration_days * 0.7
                    elif self.ai_review == "full_review":
                        duration_days = duration_days * 0.1
                    yield self.env.timeout(duration_days)
            else:
                if self.ai_review == "full_review":
                    duration_days_recheck = duration_days_recheck * 0.1
                yield self.env.timeout(duration_days_recheck)
            service_end_time = self.env.now
            if is_initial:
                permit.public_works_initial_service += (service_end_time - service_start_time)
            else:
                permit.public_works_recheck_service += (service_end_time - service_start_time)

        if permit.public_works_rechecks == 0:
            # 25% approved, 75% need re-check
            approved = random.random() < 0.25
            is_initial = False
        else:
            # 95% approved, 5% need re-check if has already been rechecked
            approved = random.random() < 0.95

        if approved:
            permit.public_works_end = self.env.now
        else:
            permit.public_works_rechecks += 1

        return approved

    def public_works_until_approved(self, permit: Permit):
        """Loop public works until approved (used for parallel flow)."""
        public_works_approved = False
        while not public_works_approved:
            public_works_approved = yield self.env.process(self.public_works(permit))

    def planning_until_approved(self, permit: Permit):
        """Loop planning department until approved."""
        planning_approved = False
        while not planning_approved:
            planning_approved = yield self.env.process(self.planning_department(permit))

    def fire_review_until_approved(self, permit: Permit):
        """Loop fire review until approved."""
        fire_approved = False
        while not fire_approved:
            fire_approved = yield self.env.process(self.fire_review(permit))

    def public_health_review_until_approved(self, permit: Permit):
        """Loop public health review until approved."""
        public_health_approved = False
        while not public_health_approved:
            public_health_approved = yield self.env.process(self.public_health_review(permit))

    
    def fire_review(self, permit: Permit):
        """Fire department review (all permits) with approval/recheck logic.
        70% take ~1 day, 30% take ~13 days.
        """
        is_initial = permit.fire_rechecks == 0
        if is_initial and permit.fire_review_request is None:
            permit.fire_review_request = self.env.now
        request_time = self.env.now

        priority = 1 if permit.fire_rechecks == 0 else 0
        with self.fire_servers.request(priority=priority) as request:
            yield request
            service_start_time = self.env.now
            if is_initial:
                permit.fire_review_service_start = service_start_time
            permit.fire_review_total_waiting += (service_start_time - request_time)
            if is_initial:
                permit.fire_initial_waiting += (service_start_time - request_time)
            else:
                permit.fire_recheck_waiting += (service_start_time - request_time)
            # 70% take ~1 day, 30% take ~13 days (for initial)
            if is_initial:
                if random.random() < 0.70:
                    # Quick review: ~1 day (normal distribution around 1 day)
                    duration_days = self.sample_normal(1, 0.2)
                else:
                    # Detailed review: ~13 days (normal distribution around 13 days)
                    duration_days = self.sample_normal(8, 2)
            else:
                # Recheck uses shorter time
                duration_days = self.sample_normal(2, 0.5)
            yield self.env.timeout(duration_days)
            service_end_time = self.env.now
            if is_initial:
                permit.fire_initial_service += (service_end_time - service_start_time)
            else:
                permit.fire_recheck_service += (service_end_time - service_start_time)
        
        if permit.fire_rechecks == 0:
            # 25% approved, 75% need re-check
            approved = random.random() < 0.25
            is_initial = False
        else:
            # 95% approved, 5% need re-check if has already been rechecked
            approved = random.random() < 0.95

        if approved:
            permit.fire_review_end = self.env.now
        else:
            permit.fire_rechecks += 1

        return approved
    
    def public_health_review(self, permit: Permit):
        """Public Health department review (1.3% of permits) with approval/recheck logic."""
        is_initial = permit.public_health_rechecks == 0
        if is_initial and permit.public_health_request is None:
            permit.public_health_request = self.env.now
        request_time = self.env.now

        priority = 1 if permit.public_health_rechecks == 0 else 0
        with self.public_health_servers.request(priority=priority) as request:
            yield request
            service_start_time = self.env.now
            if is_initial:
                permit.public_health_service_start = service_start_time
            permit.public_health_total_waiting += (service_start_time - request_time)
            if is_initial:
                permit.public_health_initial_waiting += (service_start_time - request_time)
            else:
                permit.public_health_recheck_waiting += (service_start_time - request_time)
            # N(10, 2) days - low confidence (for initial)
            if is_initial:
                duration_days = self.sample_normal(10, 2)
            else:
                # Recheck uses shorter time
                duration_days = self.sample_normal(5, 1)
            yield self.env.timeout(duration_days)
            service_end_time = self.env.now
            if is_initial:
                permit.public_health_initial_service += (service_end_time - service_start_time)
            else:
                permit.public_health_recheck_service += (service_end_time - service_start_time)
        
        if permit.public_health_rechecks == 0:
            # 25% approved, 75% need re-check
            approved = random.random() < 0.25
            is_initial = False
        else:
            # 95% approved, 5% need re-check if has already been rechecked
            approved = random.random() < 0.95

        if approved:
            permit.public_health_end = self.env.now
        else:
            permit.public_health_rechecks += 1

        return approved
    
    def permit_process(self, permit: Permit):
        """Main process flow for a single permit."""
        # Two parallel paths from fire event:
        # Path 1: Debris removal
        debris_process = self.env.process(self.debris_removal_path(permit))
        
        # Path 2: Authorization and plan preparation
        plan_process = self.env.process(self.plan_path(permit))
        
        # Wait for both paths to complete
        yield debris_process & plan_process
        
        # Planning department (skipped for segments 5&6) - loop until approved
        yield self.env.process(self.planning_until_approved(permit))
        
        # Agency Referrals permits (for non-like-for-like segments 2, 4, 6)
        # Runs sequentially between planning and public works
        yield self.env.process(self.misc_permits(permit))
        
        # Parallel processes: Building & Safety (Public Works), Fire Review, and Public Health Review
        parallel_processes = []
        
        # Public Works (Building & Safety) - loop until approved
        parallel_processes.append(self.env.process(self.public_works_until_approved(permit)))
        
        # Fire review: all permits go through fire review - loop until approved
        parallel_processes.append(self.env.process(self.fire_review_until_approved(permit)))
        
        # Public Health review: 1.3% of permits - loop until approved
        if random.random() < 0.013:
            parallel_processes.append(self.env.process(self.public_health_review_until_approved(permit)))
        
        # Wait for all parallel processes to complete
        if parallel_processes:
            yield simpy.AllOf(self.env, parallel_processes)
        
        # Ready for construction
        permit.ready_for_construction = self.env.now
        self.completed_permits.append(permit)
        if permit.permit_id in self.in_progress_permits:
            del self.in_progress_permits[permit.permit_id]
    
    def permit_process_sequential(self, permit: Permit):
        """Alternative process flow for a single permit with no parallelism.

        This runs each major step one after the other, so you can directly
        compare a fully sequential workflow to the original parallel one.
        """
        # Debris removal first (EPA → USACE)
        yield self.env.process(self.debris_removal_path(permit))
        
        # Then authorization and plan preparation
        yield self.env.process(self.securing_authorization(permit))
        yield self.env.process(self.prepare_submit_plans(permit))
        
        # Planning department (skipped for segments 5&6) - loop until approved
        yield self.env.process(self.planning_until_approved(permit))
        
        # Agency Referrals permits (for non-like-for-like segments 2, 4, 6)
        yield self.env.process(self.misc_permits(permit))
        
        # Building & Safety (Public Works) - loop until approved
        yield self.env.process(self.public_works_until_approved(permit))
        
        # Fire review: all permits go through fire review (sequential) - loop until approved
        yield self.env.process(self.fire_review_until_approved(permit))
        
        # Public Health review: 1.3% of permits (sequential) - loop until approved
        if random.random() < 0.013:
            yield self.env.process(self.public_health_review_until_approved(permit))
        
        # Ready for construction
        permit.ready_for_construction = self.env.now
        self.completed_permits.append(permit)
        if permit.permit_id in self.in_progress_permits:
            del self.in_progress_permits[permit.permit_id]

    def permit_process_parallel(self, permit: Permit):
        """Alternative process flow for a single permit with maximum parallelism.
        """
        parallel_processes = []
        parallel_processes.append(self.env.process(self.debris_removal_path(permit)))
        parallel_processes.append(self.env.process(self.securing_authorization(permit)))
        parallel_processes.append(self.env.process(self.parallel_plan_reviews(permit)))
        yield simpy.AllOf(self.env, parallel_processes)
        
        # Ready for construction
        permit.ready_for_construction = self.env.now
        self.completed_permits.append(permit)
        if permit.permit_id in self.in_progress_permits:
            del self.in_progress_permits[permit.permit_id]
    
    def debris_removal_path(self, permit: Permit):
        """Debris removal path: EPA → USACE."""
        yield self.env.timeout(45) # 45 day wait for debris removal to start
        yield self.env.process(self.epa_debris_removal(permit))
        yield self.env.process(self.usace_debris_removal(permit))
    
    def plan_path(self, permit: Permit):
        """Authorization and plan preparation path."""
        yield self.env.process(self.securing_authorization(permit))
        yield self.env.process(self.prepare_submit_plans(permit))

    def parallel_plan_reviews(self, permit: Permit):
        """Parallel reviews path after plan submission."""
        yield self.env.process(self.prepare_submit_plans(permit))
        parallel_processes = []
        parallel_processes.append(self.env.process(self.planning_until_approved(permit)))
        parallel_processes.append(self.env.process(self.misc_permits(permit)))
        parallel_processes.append(self.env.process(self.public_works_until_approved(permit)))
        parallel_processes.append(self.env.process(self.fire_review_until_approved(permit)))
        if random.random() < 0.013:
            parallel_processes.append(self.env.process(self.public_health_review_until_approved(permit)))
        yield simpy.AllOf(self.env, parallel_processes)
    
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
                        "min": min(segment_times),
                        "max": max(segment_times),
                        "count": len(segment_times),
                    }
        
        # Re-check statistics
        recheck_counts = [p.public_works_rechecks for p in self.completed_permits]
        stats["public_works_rechecks"] = {
            "average": statistics.mean(recheck_counts) if recheck_counts else 0,
            "max": max(recheck_counts) if recheck_counts else 0,
            "total_permits_with_rechecks": sum(1 for c in recheck_counts if c > 0),
        }

        # Debris removal (EPA vs USACE): waiting + service time
        epa_waiting = [p.epa_debris_total_waiting for p in self.completed_permits]
        usace_waiting = [p.usace_debris_total_waiting for p in self.completed_permits]

        epa_service = [
            (p.epa_debris_end - p.epa_debris_service_start)
            for p in self.completed_permits
            if p.epa_debris_end is not None and p.epa_debris_service_start is not None
        ]
        usace_service = [
            (p.usace_debris_end - p.usace_debris_service_start)
            for p in self.completed_permits
            if p.usace_debris_end is not None and p.usace_debris_service_start is not None
        ]

        stats["debris_removal_epa"] = {
            "waiting_mean": statistics.mean(epa_waiting) if epa_waiting else 0,
            "waiting_median": statistics.median(epa_waiting) if epa_waiting else 0,
            "service_mean": statistics.mean(epa_service) if epa_service else 0,
            "service_median": statistics.median(epa_service) if epa_service else 0,
        }
        stats["debris_removal_usace"] = {
            "waiting_mean": statistics.mean(usace_waiting) if usace_waiting else 0,
            "waiting_median": statistics.median(usace_waiting) if usace_waiting else 0,
            "service_mean": statistics.mean(usace_service) if usace_service else 0,
            "service_median": statistics.median(usace_service) if usace_service else 0,
        }

        # Total waiting and service time (across all stages)
        total_waiting_times = []
        total_service_times = []
        for p in self.completed_permits:
            waiting = (
                p.epa_debris_total_waiting
                + p.usace_debris_total_waiting
                + p.planning_total_waiting
                + p.public_works_total_waiting
                + p.fire_review_total_waiting
                + p.public_health_total_waiting
            )
            if p.misc_request is not None and p.misc_service_start is not None:
                waiting += p.misc_service_start - p.misc_request
            total_waiting_times.append(waiting)

            service = 0.0
            if p.epa_debris_end is not None and p.epa_debris_service_start is not None:
                service += p.epa_debris_end - p.epa_debris_service_start
            if p.usace_debris_end is not None and p.usace_debris_service_start is not None:
                service += p.usace_debris_end - p.usace_debris_service_start
            if p.authorization_end is not None and p.authorization_start is not None:
                service += p.authorization_end - p.authorization_start
            if p.plan_prep_end is not None and p.plan_prep_start is not None:
                service += p.plan_prep_end - p.plan_prep_start
            service += p.planning_initial_service + p.planning_recheck_service
            service += p.public_works_initial_service + p.public_works_recheck_service
            service += p.fire_initial_service + p.fire_recheck_service
            service += p.public_health_initial_service + p.public_health_recheck_service
            if p.misc_end is not None and p.misc_service_start is not None:
                service += p.misc_end - p.misc_service_start
            total_service_times.append(service)

        stats["total_waiting_time"] = {
            "mean": statistics.mean(total_waiting_times) if total_waiting_times else 0,
            "median": statistics.median(total_waiting_times) if total_waiting_times else 0,
            "std": statistics.stdev(total_waiting_times) if len(total_waiting_times) > 1 else 0,
            "min": min(total_waiting_times) if total_waiting_times else 0,
            "max": max(total_waiting_times) if total_waiting_times else 0,
        }
        stats["total_service_time"] = {
            "mean": statistics.mean(total_service_times) if total_service_times else 0,
            "median": statistics.median(total_service_times) if total_service_times else 0,
            "std": statistics.stdev(total_service_times) if len(total_service_times) > 1 else 0,
            "min": min(total_service_times) if total_service_times else 0,
            "max": max(total_service_times) if total_service_times else 0,
        }

        return stats

