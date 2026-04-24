"""
Discrete Event Simulation of Post-Disaster Permitting Process
Using SimPy to model the workflow from fire event to construction readiness.
"""

import simpy
import random
import numpy as np
import heapq
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional
import statistics
from scipy.stats import lognorm


class Segment(Enum):
    """Permit segments based on plan type and likeness."""
    PRE_APPROVED_LIKE = 1  # Pre-approved plan, Like-for-like
    PRE_APPROVED_NON_LIKE = 2  # Pre-approved plan, Non-like-for-like
    CUSTOM_LIKE = 3  # Custom build, Like-for-like
    CUSTOM_NON_LIKE = 4  # Custom build, Non-like-for-like
    SELF_CERT_LIKE = 5  # Custom build w/ self-certification, Like-for-like
    SELF_CERT_NON_LIKE = 6  # Custom build w/ self-certification, Non-like-for-like


class StaffCaseloadPool:
    """Priority-aware pool of staff with per-person concurrent caseload caps."""

    def __init__(self, env: simpy.Environment, staff_count: int, caseload_per_staff: int):
        self.env = env
        self.staff_count = max(1, int(staff_count))
        self.caseload_per_staff = max(1, int(caseload_per_staff))
        self._loads = [0] * self.staff_count
        self._waiters: list[tuple[int, int, simpy.Event]] = []
        self._seq = 0

    def _next_available_staff(self) -> Optional[int]:
        available = [idx for idx, load in enumerate(self._loads) if load < self.caseload_per_staff]
        if not available:
            return None
        return min(available, key=lambda idx: (self._loads[idx], idx))

    def request(self, priority: int = 1, preferred_staff_id: Optional[int] = None):
        """Yield a staff id once a staff member has available caseload."""
        while True:
            if preferred_staff_id is not None:
                if 0 <= preferred_staff_id < self.staff_count and self._loads[preferred_staff_id] < self.caseload_per_staff:
                    staff_id = preferred_staff_id
                else:
                    staff_id = None
            else:
                staff_id = self._next_available_staff()
            if staff_id is not None:
                self._loads[staff_id] += 1
                return staff_id

            evt = self.env.event()
            heapq.heappush(self._waiters, (priority, self._seq, evt))
            self._seq += 1
            yield evt

    def release(self, staff_id: int):
        self._loads[staff_id] = max(0, self._loads[staff_id] - 1)
        if self._waiters:
            _, _, evt = heapq.heappop(self._waiters)
            if not evt.triggered:
                evt.succeed()


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
    planning_reviewer_staff_id: Optional[int] = None
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
    public_works_reviewer_staff_id: Optional[int] = None
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
    fire_reviewer_staff_id: Optional[int] = None
    # Applicant revisions (when plan is returned but not yet approved); N(30, 10) days per occurrence
    applicant_revisions_total_time: float = 0.0
    applicant_revision_count: int = 0
    applicant_revision_intervals: List[tuple] = field(default_factory=list)
    # Agency referral permits
    agency_referral_request: Optional[float] = None
    agency_referral_service_start: Optional[float] = None
    agency_referral_end: Optional[float] = None
    # Special zoning review (service only, no explicit waiting)
    zoning_start: Optional[float] = None
    zoning_end: Optional[float] = None
    # Final
    ready_for_construction: Optional[float] = None


def epa_debris_calendar_metrics(permits: Iterable[Permit]) -> Dict[str, Optional[float]]:
    """
    Across permits: earliest EPA service start, latest EPA end, and wall-clock span
    (last end minus first start; overlaps allowed). Uses the same time units as the simulation.
    """
    starts = [p.epa_debris_service_start for p in permits if p.epa_debris_service_start is not None]
    ends = [p.epa_debris_end for p in permits if p.epa_debris_end is not None]
    if not starts or not ends:
        return {
            "first_service_start": None,
            "last_service_end": None,
            "calendar_span_first_start_to_last_end": None,
        }
    first = min(starts)
    last = max(ends)
    return {
        "first_service_start": first,
        "last_service_end": last,
        "calendar_span_first_start_to_last_end": last - first,
    }


def _permit_county_review_days(p: Permit) -> float:
    """Cumulative days in county-led review queues + review service (planning, PW, fire, zoning, agency referral)."""
    t = (
        p.planning_total_waiting
        + p.planning_initial_service
        + p.planning_recheck_service
        + p.public_works_total_waiting
        + p.public_works_initial_service
        + p.public_works_recheck_service
        + p.fire_review_total_waiting
        + p.fire_initial_service
        + p.fire_recheck_service
    )
    if p.zoning_end is not None and p.zoning_start is not None:
        t += p.zoning_end - p.zoning_start
    if p.agency_referral_request is not None and p.agency_referral_service_start is not None:
        t += p.agency_referral_service_start - p.agency_referral_request
    if p.agency_referral_end is not None and p.agency_referral_service_start is not None:
        t += p.agency_referral_end - p.agency_referral_service_start
    return t


def _permit_applicant_days(p: Permit) -> float:
    """Cumulative days in pre-application (authorization + plan prep) and applicant revision work."""
    t = p.applicant_revisions_total_time
    if p.authorization_end is not None and p.authorization_start is not None:
        t += p.authorization_end - p.authorization_start
    if p.plan_prep_end is not None and p.plan_prep_start is not None:
        t += p.plan_prep_end - p.plan_prep_start
    return t


def usace_debris_calendar_metrics(permits: Iterable[Permit]) -> Dict[str, Optional[float]]:
    """
    Across permits: earliest USACE service start, latest USACE end, and wall-clock span
    (last end minus first start; overlaps allowed). Same time units as the simulation.
    """
    starts = [p.usace_debris_service_start for p in permits if p.usace_debris_service_start is not None]
    ends = [p.usace_debris_end for p in permits if p.usace_debris_end is not None]
    if not starts or not ends:
        return {
            "first_service_start": None,
            "last_service_end": None,
            "calendar_span_first_start_to_last_end": None,
        }
    first = min(starts)
    last = max(ends)
    return {
        "first_service_start": first,
        "last_service_end": last,
        "calendar_span_first_start_to_last_end": last - first,
    }


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
        review_duration_families: Optional[Dict[str, str]] = None,
        review_duration_multipliers: Optional[Dict[str, float]] = None,
        pre_application_distribution: str = "baseline",
        planning_staff_count: int = 20,
        planning_caseload_per_staff: float = 7.5,
        public_works_staff_count: int = 40,
        public_works_caseload_per_staff: float = 7.5,
        fire_staff_count: int = 100,
        fire_caseload_per_staff: float = 1.0,

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
            review_duration_families: Optional per-stage distribution family mapping for
                'planning', 'public_works', and 'fire'. Supported families:
                'normal', 'lognormal', 'triangular', 'uniform'.
            review_duration_multipliers: Optional per-stage duration multipliers.
                Supported keys include 'planning', 'public_works', 'fire',
                'special_zoning', and 'agency_referral'.
            pre_application_distribution: Distribution used for pre-application
                activities. Supported values:
                - 'baseline': existing segment-specific behavior
                - 'lognormal_180': lognormal with median 180 days
                - 'lognormal_60': lognormal with median 60 days
                - 'poisson_10': Poisson with lambda 10 days
            planning_staff_count: Number of planning staff.
            planning_caseload_per_staff: Average concurrent planning caseload per staff.
            public_works_staff_count: Number of public works staff.
            public_works_caseload_per_staff: Average concurrent public works
                caseload per staff.
            fire_staff_count: Number of fire review staff.
            fire_caseload_per_staff: Average concurrent fire caseload per staff.

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

        default_review_families = {
            "planning": "normal",
            "public_works": "normal",
            "fire": "normal",
        }
        self.review_duration_families = dict(default_review_families)
        if review_duration_families:
            self.review_duration_families.update(review_duration_families)
        self.review_duration_multipliers = {
            "planning": 1.0,
            "public_works": 1.0,
            "fire": 1.0,
            "special_zoning": 1.0,
            "agency_referral": 1.0,
        }
        if review_duration_multipliers:
            self.review_duration_multipliers.update(review_duration_multipliers)
        self.pre_application_distribution = pre_application_distribution
        self.planning_staff_count = max(1, int(round(planning_staff_count)))
        self.public_works_staff_count = max(1, int(round(public_works_staff_count)))
        self.fire_staff_count = max(1, int(round(fire_staff_count)))
        self.planning_caseload_per_staff = max(0.0, float(planning_caseload_per_staff))
        self.public_works_caseload_per_staff = max(0.0, float(public_works_caseload_per_staff))
        self.fire_caseload_per_staff = max(0.0, float(fire_caseload_per_staff))
        self.planning_staff_pool = StaffCaseloadPool(
            env=env,
            staff_count=self.planning_staff_count,
            caseload_per_staff=max(1, int(round(self.planning_caseload_per_staff))),
        )
        self.public_works_staff_pool = StaffCaseloadPool(
            env=env,
            staff_count=self.public_works_staff_count,
            caseload_per_staff=max(1, int(round(self.public_works_caseload_per_staff))),
        )
        self.fire_staff_pool = StaffCaseloadPool(
            env=env,
            staff_count=self.fire_staff_count,
            caseload_per_staff=max(1, int(round(self.fire_caseload_per_staff))),
        )

        # Resource pools
        self.epa_debris_servers = simpy.Resource(env, capacity=160)
        self.usace_debris_servers = simpy.Resource(env, capacity=116)
        
        # Statistics
        self.completed_permits: List[Permit] = []
        self.in_progress_permits: Dict[int, Permit] = {}
        self.permit_counter = 0
        # Applicant revision coordination per permit:
        # - _revision_events gates review processes while a revision is pending/running
        # - _active_reviews counts in-progress review services (Planning, Public Works, Fire, Public Health)
        # - _no_active_events is triggered when active reviews drop to zero so revisions
        #   can start without overlapping any review service time.
        self._revision_events: Dict[int, simpy.Event] = {}
        self._active_reviews: Dict[int, int] = {}
        self._no_active_events: Dict[int, simpy.Event] = {}
        
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

    def _lognormal_from_mean_std(self, mean: float, std: float) -> tuple[float, float]:
        """Convert real-space mean/std to numpy.lognormal(mu, sigma)."""
        mean = max(mean, 1e-6)
        std = max(std, 1e-6)
        sigma2 = np.log(1.0 + (std ** 2) / (mean ** 2))
        sigma = np.sqrt(sigma2)
        mu = np.log(mean) - 0.5 * sigma2
        return mu, sigma

    def sample_duration_family(self, family: str, mean: float, std: float) -> float:
        """Sample non-negative duration from a named family using mean/std scale."""
        mean = max(mean, 1e-6)
        std = max(std, 1e-6)
        family = family.lower()

        if family == "normal":
            value = np.random.normal(mean, std)
        elif family == "lognormal":
            mu, sigma = self._lognormal_from_mean_std(mean, std)
            value = np.random.lognormal(mu, sigma)
        elif family == "triangular":
            left = max(0.0, mean - 2.0 * std)
            mode = mean
            right = mean + 2.0 * std
            value = np.random.triangular(left, mode, right)
        elif family == "uniform":
            low = max(0.0, mean - std)
            high = mean + std
            value = np.random.uniform(low, high)
        else:
            raise ValueError(f"Unsupported duration family: {family}")

        return max(0.0, float(value))

    def sample_stage_duration(self, stage: str, mean: float, std: float) -> float:
        """Sample duration for a stage using configured family."""
        family = self.review_duration_families.get(stage, "normal")
        multiplier = self.review_duration_multipliers.get(stage, 1.0)
        return self.sample_duration_family(family, mean * multiplier, std * multiplier)

    def sample_pre_application_duration(self, permit: Permit) -> float:
        """Sample pre-application duration using configured distribution choice."""
        dist = self.pre_application_distribution
        if dist == "baseline":
            if permit.segment in [Segment.PRE_APPROVED_LIKE, Segment.PRE_APPROVED_NON_LIKE]:
                return self.sample_lognormal(249, 0.53)
            return max(0, lognorm.rvs(0.886, 0, 444))
        if dist == "lognormal_180":
            return self.sample_lognormal(180, 0.53)
        if dist == "lognormal_60":
            return self.sample_lognormal(60, 0.53)
        if dist == "poisson_10":
            return max(0.0, float(np.random.poisson(10)))
        if dist == "lognormal_10":
            return self.sample_lognormal(10, 0.53)
        raise ValueError(f"Unsupported pre_application_distribution: {dist}")
    
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
            duration = self.sample_normal(1, 0.5)
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
    
    def pre_application_activities(self, permit: Permit):
        "Encompasses all pre-application activities, including preparing/submitting plans, securing financing, etc"
        # Prepare & submit plans
        permit.plan_prep_start = self.env.now

        duration_days_plan = self.sample_pre_application_duration(permit)

        yield self.env.timeout(duration_days_plan)
        permit.plan_prep_end = self.env.now
    
    def planning_department(self, permit: Permit):
        """Planning department processing with approval/recheck logic.
        """
        # If a revision is in progress for this permit, wait until it completes
        rev_evt = self._revision_events.get(permit.permit_id)
        if rev_evt is not None and not rev_evt.triggered:
            yield rev_evt

        is_initial = permit.planning_rechecks == 0
        if is_initial and permit.planning_request is None:
            permit.planning_request = self.env.now
        request_time = self.env.now

        priority = 1 if permit.planning_rechecks == 0 else 0
        planning_staff_id: Optional[int] = None
        try:
            preferred_staff_id = permit.planning_reviewer_staff_id if not is_initial else None
            planning_staff_id = yield self.env.process(
                self.planning_staff_pool.request(
                    priority=priority,
                    preferred_staff_id=preferred_staff_id,
                )
            )
            if is_initial and permit.planning_reviewer_staff_id is None:
                permit.planning_reviewer_staff_id = planning_staff_id

            service_start_time = self.env.now
            if is_initial:
                permit.planning_service_start = service_start_time
            permit.planning_total_waiting += (service_start_time - request_time)
            if is_initial:
                permit.planning_initial_waiting += (service_start_time - request_time)
            else:
                permit.planning_recheck_waiting += (service_start_time - request_time)
            # Mark review service as active (for revision overlap control)
            self._active_reviews[permit.permit_id] = self._active_reviews.get(permit.permit_id, 0) + 1

            if is_initial:
                if permit.segment in [Segment.PRE_APPROVED_NON_LIKE, Segment.CUSTOM_NON_LIKE, Segment.SELF_CERT_NON_LIKE]:
                    duration_days = self.sample_stage_duration("planning", 9, 1)
                else:  # like-for-like
                    duration_days = self.sample_stage_duration("planning", 5, 0.5)
                if self.ai_review == "initial_check":
                    duration_days = duration_days * 0.7
                elif self.ai_review == "full_review":
                    duration_days = duration_days * 0.1
            else:
                # Recheck uses shorter time
                duration_days = self.sample_stage_duration("planning", 1, 0.5)
                if self.ai_review == "full_review":
                    duration_days = duration_days * 0.1

            yield self.env.timeout(duration_days)

            service_end_time = self.env.now
            if is_initial:
                permit.planning_initial_service += (service_end_time - service_start_time)
            else:
                permit.planning_recheck_service += (service_end_time - service_start_time)
        finally:
            if planning_staff_id is not None and planning_staff_id >= 0:
                self.planning_staff_pool.release(planning_staff_id)

            pid = permit.permit_id
            if self._active_reviews.get(pid, 0) > 0:
                self._active_reviews[pid] = self._active_reviews.get(pid, 1) - 1
            if self._active_reviews.get(pid, 0) <= 0:
                self._active_reviews[pid] = 0
                no_evt = self._no_active_events.get(pid)
                if no_evt is not None and not no_evt.triggered:
                    no_evt.succeed()
        
        if permit.planning_rechecks == 0:
            # 10% approved, 90% need re-check
            approved = random.random() < 0.1
            is_initial = False
        else:
            # 90% approved, 10% need re-check if has already been rechecked
            approved = random.random() < 0.9

        if approved:
            permit.planning_end = self.env.now
        else:
            permit.planning_rechecks += 1

        return approved

    def agency_referral(self, permit: Permit):
        """Agency referral permits administered by various other departments.
        Segments 1, 3, and 5 (like-for-like) skip this step entirely.
        """
        if permit.segment in [Segment.PRE_APPROVED_LIKE, Segment.CUSTOM_LIKE, Segment.SELF_CERT_LIKE]:
            # Skip agency referral if like-for-like
            return
        
        permit.agency_referral_request = self.env.now
        permit.agency_referral_service_start = self.env.now
        duration_days = self.sample_lognormal(30, 0.7)
        duration_days *= self.review_duration_multipliers.get("agency_referral", 1.0)
        yield self.env.timeout(duration_days)
        permit.agency_referral_end = self.env.now

    def special_zoning_review(self, permit: Permit):
        """Special zoning review step for permits that require additional zoning checks.

        Currently applies only to non-like-for-like segments (2, 4, 6) and is modeled
        as a single service interval with no queueing.
        """
        if permit.segment not in [
            Segment.PRE_APPROVED_NON_LIKE,
            Segment.CUSTOM_NON_LIKE,
            Segment.SELF_CERT_NON_LIKE,
        ]:
            return

        permit.zoning_start = self.env.now
        # Placeholder duration: lognormal with median 45 days, sigma 0.7
        duration_days = self.sample_lognormal(45, 0.7)
        duration_days *= self.review_duration_multipliers.get("special_zoning", 1.0)
        yield self.env.timeout(duration_days)
        permit.zoning_end = self.env.now
    
    def public_works(self, permit: Permit):
        """Public works (Building & Safety) Initial Check.
        Segments 3-6 (non-pre-approved) take longer.
        Sets permit.public_works_approved to True if approved, False if needs re-check.
        """
        # Pause if an applicant revision is in progress.
        rev_evt = self._revision_events.get(permit.permit_id)
        if rev_evt is not None and not rev_evt.triggered:
            yield rev_evt

        is_initial = permit.public_works_rechecks == 0
        if is_initial and permit.public_works_request is None:
            permit.public_works_request = self.env.now
        request_time = self.env.now

        priority = 1 if permit.public_works_rechecks == 0 else 0
        public_works_staff_id: Optional[int] = None
        try:
            preferred_staff_id = permit.public_works_reviewer_staff_id if not is_initial else None
            public_works_staff_id = yield self.env.process(
                self.public_works_staff_pool.request(
                    priority=priority,
                    preferred_staff_id=preferred_staff_id,
                )
            )
            if is_initial and permit.public_works_reviewer_staff_id is None:
                permit.public_works_reviewer_staff_id = public_works_staff_id

            service_start_time = self.env.now
            # Mark review service as active for overlap control
            self._active_reviews[permit.permit_id] = self._active_reviews.get(permit.permit_id, 0) + 1

            if is_initial:
                permit.public_works_service_start = service_start_time  # Track first service start
            permit.public_works_total_waiting += (service_start_time - request_time)  # Track cumulative waiting
            if is_initial:
                permit.public_works_initial_waiting += (service_start_time - request_time)
            else:
                permit.public_works_recheck_waiting += (service_start_time - request_time)
            duration_days = self.sample_stage_duration("public_works", 8, 2)
            duration_days_pre_approved = self.sample_stage_duration("public_works", 1, 0.5)
            duration_days_recheck = self.sample_stage_duration("public_works", 1, 0.5)
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
        finally:
            if public_works_staff_id is not None and public_works_staff_id >= 0:
                self.public_works_staff_pool.release(public_works_staff_id)

            pid = permit.permit_id
            if self._active_reviews.get(pid, 0) > 0:
                self._active_reviews[pid] = self._active_reviews.get(pid, 1) - 1
            if self._active_reviews.get(pid, 0) <= 0:
                self._active_reviews[pid] = 0
                no_evt = self._no_active_events.get(pid)
                if no_evt is not None and not no_evt.triggered:
                    no_evt.succeed()

        if permit.public_works_rechecks == 0:
            # 10% approved, 90% need re-check
            approved = random.random() < 0.1
            is_initial = False
        else:
            # 90% approved, 10% need re-check if has already been rechecked
            approved = random.random() < 0.9

        if approved:
            permit.public_works_end = self.env.now
        else:
            permit.public_works_rechecks += 1

        return approved

    def public_works_until_approved(self, permit: Permit):
        """Loop public works until approved (used for parallel flow).

        Agency referral (non-like segments) is not inside the PW server block. It starts
        after the first failed PW attempt so it runs in parallel with applicant revisions
        and PW rechecks; if PW approves on the first try, agency referral runs after that.
        """
        needs_agency_referral = permit.segment not in [
            Segment.PRE_APPROVED_LIKE,
            Segment.CUSTOM_LIKE,
            Segment.SELF_CERT_LIKE,
        ]
        agency_referral_proc = None
        public_works_approved = False
        while not public_works_approved:
            public_works_approved = yield self.env.process(self.public_works(permit))
            if not public_works_approved:
                if needs_agency_referral and agency_referral_proc is None:
                    agency_referral_proc = self.env.process(self.agency_referral(permit))
                yield self.env.process(self.applicant_revision(permit))
        if needs_agency_referral:
            if agency_referral_proc is not None:
                yield agency_referral_proc
            else:
                yield self.env.process(self.agency_referral(permit))

    def planning_until_approved(self, permit: Permit):
        """Loop planning department until approved."""
        planning_approved = False
        while not planning_approved:
            planning_approved = yield self.env.process(self.planning_department(permit))
            if not planning_approved:
                yield self.env.process(self.applicant_revision(permit))

    def fire_review_until_approved(self, permit: Permit):
        """Loop fire review until approved."""
        fire_approved = False
        while not fire_approved:
            fire_approved = yield self.env.process(self.fire_review(permit))
            if not fire_approved:
                yield self.env.process(self.applicant_revision(permit))
    
    def fire_review(self, permit: Permit):
        """Fire department review (all permits) with approval/recheck logic.
        70% take ~1 day, 30% take ~13 days.
        """
        # Pause if an applicant revision is in progress.
        rev_evt = self._revision_events.get(permit.permit_id)
        if rev_evt is not None and not rev_evt.triggered:
            yield rev_evt

        is_initial = permit.fire_rechecks == 0
        if is_initial and permit.fire_review_request is None:
            permit.fire_review_request = self.env.now
        request_time = self.env.now

        priority = 1 if permit.fire_rechecks == 0 else 0
        fire_staff_id: Optional[int] = None
        try:
            preferred_staff_id = permit.fire_reviewer_staff_id if not is_initial else None
            fire_staff_id = yield self.env.process(
                self.fire_staff_pool.request(
                    priority=priority,
                    preferred_staff_id=preferred_staff_id,
                )
            )
            if is_initial and permit.fire_reviewer_staff_id is None:
                permit.fire_reviewer_staff_id = fire_staff_id

            service_start_time = self.env.now
            # Mark review service as active
            self._active_reviews[permit.permit_id] = self._active_reviews.get(permit.permit_id, 0) + 1

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
                    duration_days = self.sample_stage_duration("fire", 1, 0.2)
                else:
                    # Detailed review: ~13 days (normal distribution around 13 days)
                    duration_days = self.sample_stage_duration("fire", 8, 2)
            else:
                # Recheck uses shorter time
                duration_days = self.sample_stage_duration("fire", 2, 0.5)
            yield self.env.timeout(duration_days)

            service_end_time = self.env.now
            if is_initial:
                permit.fire_initial_service += (service_end_time - service_start_time)
            else:
                permit.fire_recheck_service += (service_end_time - service_start_time)
        finally:
            if fire_staff_id is not None and fire_staff_id >= 0:
                self.fire_staff_pool.release(fire_staff_id)

            # Mark end of active review time and notify revisions if no reviews remain
            pid = permit.permit_id
            if self._active_reviews.get(pid, 0) > 0:
                self._active_reviews[pid] = self._active_reviews.get(pid, 1) - 1
            if self._active_reviews.get(pid, 0) <= 0:
                self._active_reviews[pid] = 0
                no_evt = self._no_active_events.get(pid)
                if no_evt is not None and not no_evt.triggered:
                    no_evt.succeed()
        
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

    def applicant_revision(self, permit: Permit):
        """Applicant revisions when a plan is returned but not yet approved. Time N(30, 10) days."""
        pid = permit.permit_id
        # If a revision is already in progress for this permit, just wait for it.
        existing_event = self._revision_events.get(pid)
        if existing_event is not None and not existing_event.triggered:
            yield existing_event
            return

        # Start a new shared revision interval for this permit and block any
        # new review work until it completes.
        evt = self.env.event()
        self._revision_events[pid] = evt

        # Ensure we don't overlap applicant revisions with any in-progress
        # review service time. If there are active reviews, wait until they
        # all finish before starting the revision clock.
        active = self._active_reviews.get(pid, 0)
        if active > 0:
            no_evt = self._no_active_events.get(pid)
            if no_evt is None or no_evt.triggered:
                no_evt = self.env.event()
                self._no_active_events[pid] = no_evt
            yield no_evt

        start_time = self.env.now
        duration_days = self.sample_normal(30, 10)
        permit.applicant_revision_count += 1
        yield self.env.timeout(duration_days)
        end_time = self.env.now
        actual_duration = end_time - start_time
        permit.applicant_revisions_total_time += actual_duration
        permit.applicant_revision_intervals.append((start_time, end_time))

        # Resume any review processes waiting on this revision.
        evt.succeed()
    
    def permit_process(self, permit: Permit):
        """Main process flow for a single permit."""
        # Two parallel paths from fire event:
        # Path 1: Debris removal
        debris_process = self.env.process(self.debris_removal_path(permit))
        
        # Path 2: Authorization and plan preparation
        plan_process = self.env.process(self.pre_application_activities(permit))
        
        yield plan_process
        
        # Planning department (skipped for segments 5&6) - loop until approved
        yield self.env.process(self.planning_until_approved(permit))
        
        # Special zoning review (for subset of permits)
        yield self.env.process(self.special_zoning_review(permit))
        
        # Parallel processes: Building & Safety (Public Works), Fire Review, and Public Health Review
        parallel_processes = []
        
        # Public Works (Building & Safety) - loop until approved
        parallel_processes.append(self.env.process(self.public_works_until_approved(permit)))
        
        # Fire review: all permits go through fire review - loop until approved
        parallel_processes.append(self.env.process(self.fire_review_until_approved(permit)))
        
        
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
        
        # Then combined pre-application activities (authorization + plan preparation)
        yield self.env.process(self.pre_application_activities(permit))
        
        # Planning department (skipped for segments 5&6) - loop until approved
        yield self.env.process(self.planning_until_approved(permit))
        
        # Special zoning review
        yield self.env.process(self.special_zoning_review(permit))
        
        # Building & Safety (Public Works) - loop until approved
        yield self.env.process(self.public_works_until_approved(permit))
        
        # Fire review: all permits go through fire review (sequential) - loop until approved
        yield self.env.process(self.fire_review_until_approved(permit))
        
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
        parallel_processes.append(self.env.process(self.parallel_plan_reviews(permit)))
        yield simpy.AllOf(self.env, parallel_processes)
        
        # Ready for construction
        permit.ready_for_construction = self.env.now
        self.completed_permits.append(permit)
        if permit.permit_id in self.in_progress_permits:
            del self.in_progress_permits[permit.permit_id]
    
    def debris_removal_path(self, permit: Permit):
        """Debris removal path: EPA → USACE."""
        yield self.env.timeout(23) # 23 day wait for debris removal to start
        yield self.env.process(self.epa_debris_removal(permit))
        yield self.env.process(self.usace_debris_removal(permit))

    def parallel_plan_reviews(self, permit: Permit):
        """Parallel reviews path after combined pre-application activities."""
        yield self.env.process(self.pre_application_activities(permit))
        parallel_processes = []
        parallel_processes.append(self.env.process(self.planning_until_approved(permit)))
        parallel_processes.append(self.env.process(self.special_zoning_review(permit)))
        parallel_processes.append(self.env.process(self.public_works_until_approved(permit)))
        parallel_processes.append(self.env.process(self.fire_review_until_approved(permit)))
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

        # Applicant revisions (when plan returned but not yet approved); N(30, 10) days per occurrence
        applicant_revision_times = [p.applicant_revisions_total_time for p in self.completed_permits]
        applicant_revision_counts = [p.applicant_revision_count for p in self.completed_permits]
        stats["applicant_revisions"] = {
            "total_time_mean": statistics.mean(applicant_revision_times) if applicant_revision_times else 0,
            "total_time_median": statistics.median(applicant_revision_times) if applicant_revision_times else 0,
            "revision_count_mean": statistics.mean(applicant_revision_counts) if applicant_revision_counts else 0,
            "revision_count_max": max(applicant_revision_counts) if applicant_revision_counts else 0,
            "permits_with_revisions": sum(1 for c in applicant_revision_counts if c > 0),
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

        epa_cal = epa_debris_calendar_metrics(self.completed_permits)
        stats["debris_removal_epa"] = {
            "waiting_mean": statistics.mean(epa_waiting) if epa_waiting else 0,
            "waiting_median": statistics.median(epa_waiting) if epa_waiting else 0,
            "service_mean": statistics.mean(epa_service) if epa_service else 0,
            "service_median": statistics.median(epa_service) if epa_service else 0,
            **epa_cal,
        }
        usace_cal = usace_debris_calendar_metrics(self.completed_permits)
        stats["debris_removal_usace"] = {
            "waiting_mean": statistics.mean(usace_waiting) if usace_waiting else 0,
            "waiting_median": statistics.median(usace_waiting) if usace_waiting else 0,
            "service_mean": statistics.mean(usace_service) if usace_service else 0,
            "service_median": statistics.median(usace_service) if usace_service else 0,
            **usace_cal,
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
            )
            if p.agency_referral_request is not None and p.agency_referral_service_start is not None:
                waiting += p.agency_referral_service_start - p.agency_referral_request
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
            service += p.applicant_revisions_total_time
            if p.agency_referral_end is not None and p.agency_referral_service_start is not None:
                service += p.agency_referral_end - p.agency_referral_service_start
            if p.zoning_end is not None and p.zoning_start is not None:
                service += p.zoning_end - p.zoning_start
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

        county_days = [_permit_county_review_days(p) for p in self.completed_permits]
        applicant_days = [_permit_applicant_days(p) for p in self.completed_permits]
        debris_only_days = []
        for p in self.completed_permits:
            d = p.epa_debris_total_waiting + p.usace_debris_total_waiting
            if p.epa_debris_end is not None and p.epa_debris_service_start is not None:
                d += p.epa_debris_end - p.epa_debris_service_start
            if p.usace_debris_end is not None and p.usace_debris_service_start is not None:
                d += p.usace_debris_end - p.usace_debris_service_start
            debris_only_days.append(d)

        stats["county_review_vs_applicant"] = {
            "county_review_mean": statistics.mean(county_days) if county_days else 0,
            "county_review_median": statistics.median(county_days) if county_days else 0,
            "county_review_std": statistics.stdev(county_days) if len(county_days) > 1 else 0,
            "applicant_mean": statistics.mean(applicant_days) if applicant_days else 0,
            "applicant_median": statistics.median(applicant_days) if applicant_days else 0,
            "applicant_std": statistics.stdev(applicant_days) if len(applicant_days) > 1 else 0,
            "debris_mean": statistics.mean(debris_only_days) if debris_only_days else 0,
            "definition": (
                "County = planning + public works + fire + special zoning + agency referral "
                "(waiting + review service). Applicant = pre-application (plan prep) + applicant "
                "revisions. Debris (EPA/USACE) separate. Public works and fire overlap in "
                "'standard' flow (double-counts calendar). 'Standard' may finish before debris "
                "completes, so sums can exceed (ready_for_construction - created_at)."
            ),
        }

        return stats

