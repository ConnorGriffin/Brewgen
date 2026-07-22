"""Flask-independent fermentables solver built on a bounded PuLP MILP.

One shared constraint model backs these operations:

* :meth:`FermentableSolver.is_valid` -- does any grain bill satisfy the model?
* :meth:`FermentableSolver.feasibility` -- is one complete brief (sensory,
  color, category, cardinality, gravity and equipment) feasible?
* :meth:`FermentableSolver.sensory_range` -- the exact achievable min/max for
  one named descriptor, holding every other configured constraint fixed.
* :meth:`FermentableSolver.generate` -- up to five deterministic, meaningfully
  different grain bills inside exact SRM bounds and a hard deadline.

The public interactive editor asks only for one focused descriptor range or one
full-brief feasibility check at a time; it never triggers an all-descriptor
sweep. :meth:`FermentableSolver.sensory_ranges` computes every descriptor at
once and is retained only as the transitional equivalence reference for the
focused path -- no public request reaches it.

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


class CheckStatus(str, Enum):
    """Outcome of a focused range or full-brief feasibility check. Stable and
    solver-agnostic: no CBC/PuLP internals leak through these names."""

    FEASIBLE = "feasible"            # the constraints admit at least one bill
    INFEASIBLE = "infeasible"       # the constraints admit no bill
    INVALID = "invalid"             # the request itself is malformed
    DEADLINE_EXCEEDED = "deadline_exceeded"  # ran out of budget before a proof


@dataclass(frozen=True)
class SolverConfig:
    """Deadlines and diversity limits. These are configuration, never caller
    controlled per request. Defaults are issue #29's public compute envelope:
    1.8 seconds of solver budget under a 2.0-second end-to-end deadline, shared
    across every solve performed for one request."""

    max_bills: int = 5
    min_pairwise_distance: int = 10
    solver_time_limit_seconds: float = 1.8
    request_deadline_seconds: float = 2.0


@dataclass(frozen=True)
class ColorContext:
    """The gravity/equipment/SRM inputs that turn a bill into an exact color.

    Supplying one to :meth:`FermentableSolver.feasibility` or
    :meth:`FermentableSolver.sensory_range` holds color fixed while the check
    runs, so the returned answer respects the brief's color band."""

    original_sg: float
    target_volume_gallons: float
    mash_efficiency: float
    min_srm: float
    max_srm: float


class _Budget:
    """A shared monotonic budget across every solve in one request.

    Enforces two ceilings at once: a wall-clock end-to-end deadline and a
    cumulative solver-time cap. Each solve is granted the smaller of what is
    left of either; a non-positive grant means the request is already spent.
    Both ceilings are server config, never caller-set, and the clock is
    injectable so deadline behavior is testable without real waiting."""

    def __init__(self, config, clock):
        self._clock = clock
        self._deadline = clock() + config.request_deadline_seconds
        self._solver_remaining = config.solver_time_limit_seconds

    @property
    def clock(self):
        return self._clock

    def next_limit(self):
        """Seconds the next solve may run; <= 0 means no budget remains."""
        return min(self._solver_remaining, self._deadline - self._clock())

    def charge(self, seconds):
        """Debit the cumulative solver budget by an elapsed solve."""
        self._solver_remaining -= seconds


@dataclass
class RangeResult:
    """Result of a focused sensory-range check: a stable status plus, when
    feasible, the exact achievable min/max for the named descriptor."""

    status: CheckStatus
    name: str
    minimum: float = None
    maximum: float = None


@dataclass
class FeasibilityResult:
    """Result of a full-brief feasibility check: just a stable status."""

    status: CheckStatus


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

    def feasibility(self, color_context=None, clock=time.monotonic):
        """Check whether one complete brief is feasible under a shared budget.

        Applies every configured constraint at once -- sensory bounds, category
        usage, global and per-category cardinality, and (when ``color_context``
        is supplied) the exact gravity/equipment/SRM color band -- and asks only
        whether any grain bill satisfies all of them.

        Returns a :class:`FeasibilityResult` whose status is ``FEASIBLE``,
        ``INFEASIBLE`` or ``DEADLINE_EXCEEDED``. No solver internals leak out.
        """
        budget = _Budget(self.config, clock)
        limit = budget.next_limit()
        if limit <= 0:
            return FeasibilityResult(CheckStatus.DEADLINE_EXCEEDED)
        prob, x, _used = self._base_problem("feasibility")
        if color_context is not None:
            self._add_color_constraints(prob, x, color_context)
        prob += 0  # feasibility only, no objective
        prob.solve(self._solver(limit))
        return FeasibilityResult(self._check_status(prob))

    def sensory_range(self, name, color_context=None, clock=time.monotonic):
        """Return the exact achievable min/max for one named descriptor.

        Every other configured constraint is held fixed, but the target
        descriptor's own sensory bound is excluded so the returned span is its
        full editable range rather than the slice a stale bound would allow.
        Both the minimize and maximize solves draw from one shared budget.

        Returns a :class:`RangeResult`. ``INVALID`` means the descriptor is not
        a known sensory keyword; ``FEASIBLE`` carries ``minimum``/``maximum``;
        ``INFEASIBLE`` and ``DEADLINE_EXCEEDED`` carry neither.
        """
        if name not in self.sensory_keywords:
            return RangeResult(CheckStatus.INVALID, name)
        budget = _Budget(self.config, clock)
        coeffs = [self.grains[i]["sensory_data"].get(name, 0) for i in self._range]
        low_status, low = self._extreme(
            coeffs, pulp.LpMinimize, name, color_context, budget)
        if low_status is not CheckStatus.FEASIBLE:
            return RangeResult(low_status, name)
        high_status, high = self._extreme(
            coeffs, pulp.LpMaximize, name, color_context, budget)
        if high_status is not CheckStatus.FEASIBLE:
            return RangeResult(high_status, name)
        # Divided-down integer sums carry tiny float noise; trim it.
        return RangeResult(CheckStatus.FEASIBLE, name,
                           round(low, 6), round(high, 6))

    def sensory_ranges(self):
        """Return achievable ``{name, min, max}`` for every sensory descriptor.

        Retained only as the transitional equivalence reference for
        :meth:`sensory_range`; no public request reaches this all-descriptor
        sweep. Cardinality-preserving MILP with no invented color constraints.
        Returns an empty list if the underlying model is infeasible.
        """
        ranges = []
        budget = _Budget(SolverConfig(request_deadline_seconds=float("inf"),
                                      solver_time_limit_seconds=float("inf")),
                         time.monotonic)
        for key in self.sensory_keywords:
            coeffs = [self.grains[i]["sensory_data"].get(key, 0) for i in self._range]
            min_status, minimum = self._extreme(
                coeffs, pulp.LpMinimize, None, None, budget)
            if min_status is not CheckStatus.FEASIBLE:
                return []
            _max_status, maximum = self._extreme(
                coeffs, pulp.LpMaximize, None, None, budget)
            ranges.append({
                "name": key,
                # Divided-down integer sums carry tiny float noise; trim it.
                "min": round(minimum, 6),
                "max": round(maximum, 6),
            })
        return ranges

    def sensory_values(self, percents):
        """Return the usage-weighted sensory value of every descriptor for a bill.

        ``percents`` is a slug->whole-percent mapping (summing to 100). Each
        value is the same usage-weighted average the range search optimizes,
        evaluated at a fixed bill, so a displayed grain bill's tastes read back
        from the real sensory model rather than being invented downstream."""
        values = {}
        for key in self.sensory_keywords:
            total = sum(grain["sensory_data"].get(key, 0) * percents.get(grain["slug"], 0)
                        for grain in self.grains)
            values[key] = round(total / 100, 6)
        return values

    def _extreme(self, coeffs, sense, exclude_sensory, color_context, budget):
        """Minimize or maximize one descriptor over a fresh copy of the model.

        A fresh problem per solve avoids CBC's trouble with re-solving the same
        problem object dozens of times. ``exclude_sensory`` drops that
        descriptor's own bound so a focused range spans its full editable width.
        Returns ``(status, value)`` where ``value`` is the descriptor's sensory
        value (usage-weighted average) only when the status is ``FEASIBLE``."""
        limit = budget.next_limit()
        if limit <= 0:
            return CheckStatus.DEADLINE_EXCEEDED, None
        prob, x, _used = self._base_problem("sensory", exclude_sensory=exclude_sensory)
        if color_context is not None:
            self._add_color_constraints(prob, x, color_context)
        prob.sense = sense
        prob.setObjective(pulp.lpSum(coeffs[i] * x[i] for i in self._range))
        start = budget.clock()
        prob.solve(self._solver(limit))
        budget.charge(budget.clock() - start)
        status = self._check_status(prob)
        if status is not CheckStatus.FEASIBLE:
            return status, None
        # Read straight from the integer percentages rather than the PuLP
        # objective, whose .value() is None for an all-zero descriptor.
        value = sum(coeffs[i] * (x[i].value() or 0) for i in self._range) / 100
        return status, value

    @staticmethod
    def _check_status(prob):
        """Map a solved problem onto a stable, solver-agnostic CheckStatus."""
        name = pulp.LpStatus[prob.status]
        if name == "Optimal":
            return CheckStatus.FEASIBLE
        if name == "Infeasible":
            return CheckStatus.INFEASIBLE
        # Undefined/Not Solved: CBC hit the time limit without a proof.
        return CheckStatus.DEADLINE_EXCEEDED

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
        ctx = ColorContext(original_sg, target_volume_gallons, mash_efficiency,
                           min_srm, max_srm)
        self._add_color_constraints(prob, x, ctx)
        colors = [g["color"] for g in self.grains]
        ppgs = [g["ppg"] for g in self.grains]
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

    def _add_color_constraints(self, prob, x, ctx):
        """Constrain the bill's exact Morey SRM into ``ctx``'s color band.

        The two half-plane coefficient rows come straight from the shared color
        math generation uses, so validity, focused ranges and generation all
        judge color identically."""
        colors = [g["color"] for g in self.grains]
        ppgs = [g["ppg"] for g in self.grains]
        lower, upper = color.color_bound_coefficients(
            colors, ppgs, ctx.original_sg, ctx.target_volume_gallons,
            ctx.mash_efficiency, ctx.min_srm, ctx.max_srm)
        prob += pulp.lpSum(lower[i] * x[i] for i in self._range) >= 0
        prob += pulp.lpSum(upper[i] * x[i] for i in self._range) >= 0

    def _base_problem(self, name, exclude_sensory=None):
        """Build the shared model: total==100, per-grain min/max linked to a
        used binary, category usage bounds, global and per-category cardinality,
        and any sensory bounds. ``exclude_sensory`` drops the bound with that
        descriptor name so a focused range is not clipped by its own stale
        bound. Returns (problem, x_vars, used_vars)."""
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
            if key == exclude_sensory:
                continue
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
