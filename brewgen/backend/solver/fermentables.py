"""Flask-independent fermentables solver built on a bounded PuLP MILP.

One shared constraint model backs three operations:

* :meth:`FermentableSolver.is_valid` -- does any grain bill satisfy the model?
* :meth:`FermentableSolver.sensory_ranges` -- achievable min/max of each
  sensory descriptor, preserving the same grain-count limits as generation.
* :meth:`FermentableSolver.generate` -- up to five deterministic, meaningfully
  different grain bills inside exact SRM bounds and a hard deadline.

Percentages are integer points 0-100 that sum to exactly 100; a binary
used/not-used variable links each grain's zero/min/max usage and drives the
global and per-category grain-count caps. Sensory coefficients stay real
numbers -- there is no fixed-point scaling. Only generation adds color
constraints; validity and sensory-range invent none.
"""

import time
from dataclasses import dataclass, field
from enum import Enum

import pulp

from . import color


class GenerationStatus(str, Enum):
    """Outcome of a generation request."""

    COMPLETE = "complete"            # found five, or exhausted the diverse space
    PARTIAL = "partial"             # deadline hit with at least one bill in hand
    INFEASIBLE = "infeasible"       # the model admits no bill at all
    DEADLINE_EXCEEDED = "deadline_exceeded"  # deadline hit before any bill


@dataclass(frozen=True)
class SolverConfig:
    """Deadlines and diversity limits. These are configuration, never caller
    controlled per request."""

    max_bills: int = 5
    min_pairwise_distance: int = 10
    solver_time_limit_seconds: float = 5.0
    request_deadline_seconds: float = 15.0


@dataclass
class Bill:
    """One grain bill: whole-percentage usage keyed by grain slug, plus the
    independently computed SRM the model accepted it at."""

    percents: dict
    srm: float


@dataclass
class GenerationResult:
    """Result of a generation request: a bounded, unranked set of alternatives
    and an explicit completion status."""

    status: GenerationStatus
    alternatives: list = field(default_factory=list)


class FermentableSolver:
    """Builds and solves the shared fermentables MILP.

    Args:
        grains (list): grain dicts with keys ``slug``, ``category``,
            ``min_percent``, ``max_percent``, ``color``, ``ppg`` and
            ``sensory_data`` (a name->value dict of real numbers).
        categories (list): category dicts with ``name``, ``min_percent``,
            ``max_percent`` and optional ``unique_fermentable_count``.
        max_unique_grains (int): global cap on distinct grains in a bill.
        sensory_keywords (list): every descriptor name (used by sensory ranges).
        sensory_bounds (list): optional descriptor bound dicts
            ``{name, min, max}`` applied as constraints in every operation.
        config (SolverConfig): deadlines and diversity limits.
    """

    def __init__(self, grains, categories, max_unique_grains=4,
                 sensory_keywords=None, sensory_bounds=None, config=None):
        # Sort by slug so a given set of inputs always produces the same model,
        # which is what makes generation deterministic.
        self.grains = sorted(grains, key=lambda g: g["slug"])
        self.categories = list(categories or [])
        self.max_unique_grains = (
            len(self.grains) if max_unique_grains is None else int(max_unique_grains))
        self.sensory_keywords = list(sensory_keywords or [])
        self.sensory_bounds = list(sensory_bounds or [])
        self.config = config or SolverConfig()
        self._range = range(len(self.grains))

    # -- public operations -------------------------------------------------

    def is_valid(self):
        """Return True if the constraints admit at least one grain bill."""
        prob, _x, _used = self._base_problem("validity")
        prob += 0  # feasibility only
        prob.solve(self._solver())
        return pulp.LpStatus[prob.status] == "Optimal"

    def sensory_ranges(self):
        """Return achievable ``{name, min, max}`` for each sensory descriptor.

        Cardinality-preserving MILP with no invented color constraints. Returns
        an empty list if the underlying model is infeasible.
        """
        ranges = []
        for key in self.sensory_keywords:
            coeffs = [self.grains[i]["sensory_data"].get(key, 0) for i in self._range]
            minimum = self._extreme(coeffs, pulp.LpMinimize)
            if minimum is None:
                return []
            maximum = self._extreme(coeffs, pulp.LpMaximize)
            ranges.append({
                "name": key,
                # Divided-down integer sums carry tiny float noise; trim it.
                "min": round(minimum, 6),
                "max": round(maximum, 6),
            })
        return ranges

    def _extreme(self, coeffs, sense):
        """Minimize or maximize one descriptor over a fresh copy of the model.

        A fresh problem per solve avoids CBC's trouble with re-solving the same
        problem object dozens of times. Returns the descriptor's sensory value
        (usage-weighted average), or None if the model is infeasible."""
        prob, x, _used = self._base_problem("sensory")
        prob.sense = sense
        prob.setObjective(pulp.lpSum(coeffs[i] * x[i] for i in self._range))
        prob.solve(self._solver())
        if pulp.LpStatus[prob.status] != "Optimal":
            return None
        # Read straight from the integer percentages rather than the PuLP
        # objective, whose .value() is None for an all-zero descriptor.
        return sum(coeffs[i] * (x[i].value() or 0) for i in self._range) / 100

    def generate(self, original_sg, target_volume_gallons, mash_efficiency,
                 min_srm, max_srm, clock=time.monotonic):
        """Generate up to ``config.max_bills`` diverse bills within SRM bounds.

        Exact decimal SRM bounds are enforced in-model. Each accepted bill adds
        an L1-distance cut so every later bill differs by at least
        ``config.min_pairwise_distance`` summed absolute percentage points.

        Args:
            original_sg (float): target starting gravity (1.xxx).
            target_volume_gallons (float): target kettle volume.
            mash_efficiency (float): whole-number mash efficiency (e.g. 75).
            min_srm, max_srm (float): exact SRM acceptance bounds.
            clock (callable): monotonic seconds source; injectable for tests.
        """
        prob, x, _used = self._base_problem("generation")
        colors = [g["color"] for g in self.grains]
        ppgs = [g["ppg"] for g in self.grains]
        lower, upper = color.color_bound_coefficients(
            colors, ppgs, original_sg, target_volume_gallons, mash_efficiency,
            min_srm, max_srm)
        prob += pulp.lpSum(lower[i] * x[i] for i in self._range) >= 0
        prob += pulp.lpSum(upper[i] * x[i] for i in self._range) >= 0
        prob += 0  # unranked: feasibility only, no brewing preference objective

        alternatives = []
        vectors = []
        start = clock()
        deadline = start + self.config.request_deadline_seconds

        while len(alternatives) < self.config.max_bills:
            now = clock()
            if now >= deadline:
                status = (GenerationStatus.PARTIAL if alternatives
                          else GenerationStatus.DEADLINE_EXCEEDED)
                return GenerationResult(status, alternatives)

            time_limit = min(self.config.solver_time_limit_seconds, deadline - now)
            prob.solve(self._solver(time_limit))
            status_name = pulp.LpStatus[prob.status]

            if status_name == "Infeasible":
                status = (GenerationStatus.COMPLETE if alternatives
                          else GenerationStatus.INFEASIBLE)
                return GenerationResult(status, alternatives)
            if status_name != "Optimal":
                # Timed out without a proof either way.
                status = (GenerationStatus.PARTIAL if alternatives
                          else GenerationStatus.DEADLINE_EXCEEDED)
                return GenerationResult(status, alternatives)

            vector = [int(round(x[i].value())) for i in self._range]
            srm = color.morey_srm(color.mash_color_units(
                colors, ppgs, vector, original_sg, target_volume_gallons,
                mash_efficiency))
            percents = {self.grains[i]["slug"]: vector[i]
                        for i in self._range if vector[i] > 0}
            alternatives.append(Bill(percents=percents, srm=srm))
            vectors.append(vector)
            self._add_distance_cut(prob, x, vector, len(vectors) - 1)

        return GenerationResult(GenerationStatus.COMPLETE, alternatives)

    # -- model construction ------------------------------------------------

    def _base_problem(self, name):
        """Build the shared model: total==100, per-grain min/max linked to a
        used binary, category usage bounds, global and per-category cardinality,
        and any sensory bounds. Returns (problem, x_vars, used_vars)."""
        prob = pulp.LpProblem(name, pulp.LpMinimize)
        x = [pulp.LpVariable("x_%d" % i, lowBound=0, upBound=100, cat="Integer")
             for i in self._range]
        used = [pulp.LpVariable("u_%d" % i, cat="Binary") for i in self._range]

        prob += pulp.lpSum(x) == 100

        for i in self._range:
            grain = self.grains[i]
            # used == 0 forces x == 0; used == 1 forces min..max (>=1 so a used
            # grain is really present even when its declared minimum is 0).
            prob += x[i] <= grain["max_percent"] * used[i]
            prob += x[i] >= used[i]
            prob += x[i] >= grain["min_percent"] * used[i]

        prob += pulp.lpSum(used) <= self.max_unique_grains

        for cat in self.categories:
            members = [i for i in self._range
                       if self.grains[i]["category"] == cat["name"]]
            if not members:
                continue
            usage = pulp.lpSum(x[i] for i in members)
            prob += usage >= cat["min_percent"]
            prob += usage <= cat["max_percent"]
            cap = cat.get("unique_fermentable_count")
            if cap is not None:
                prob += pulp.lpSum(used[i] for i in members) <= cap

        for bound in self.sensory_bounds:
            key = bound["name"]
            expr = pulp.lpSum(
                self.grains[i]["sensory_data"].get(key, 0) * x[i] for i in self._range)
            prob += expr >= bound["min"] * 100
            prob += expr <= bound["max"] * 100

        return prob, x, used

    def _add_distance_cut(self, prob, x, accepted, tag):
        """Require every future bill to differ from ``accepted`` by at least
        ``config.min_pairwise_distance`` summed absolute percentage points.

        The absolute deviation of each grain is split into a positive and a
        negative part whose sum equals |x_i - accepted_i| exactly (a binary
        keeps only one part active), then the total is bounded below."""
        pos = [pulp.LpVariable("p_%d_%d" % (tag, i), lowBound=0) for i in self._range]
        neg = [pulp.LpVariable("n_%d_%d" % (tag, i), lowBound=0) for i in self._range]
        pick = [pulp.LpVariable("b_%d_%d" % (tag, i), cat="Binary") for i in self._range]
        for i in self._range:
            prob += x[i] - accepted[i] == pos[i] - neg[i]
            prob += pos[i] <= 100 * pick[i]
            prob += neg[i] <= 100 * (1 - pick[i])
        prob += (pulp.lpSum(pos[i] + neg[i] for i in self._range)
                 >= self.config.min_pairwise_distance)

    def _solver(self, time_limit=None):
        """One deterministic CBC configuration for every solve."""
        if time_limit is None:
            time_limit = self.config.solver_time_limit_seconds
        return pulp.PULP_CBC_CMD(msg=0, threads=1, timeLimit=time_limit)
