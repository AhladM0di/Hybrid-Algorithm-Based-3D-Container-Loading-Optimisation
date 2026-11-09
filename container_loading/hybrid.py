"""Generate placements, sample a QUBO and repair the selected packing."""

import argparse
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
from functools import partial
from itertools import combinations, permutations, product
import json
from math import exp, gcd, log, prod
from statistics import median
from pathlib import Path
from random import Random
from time import perf_counter

from check_packing import load_instance
from feasibility import Instance, Package, Placement, fully_supported, overlaps, supported_area, validate_packing


@dataclass(frozen=True)
class Qubo:
    rewards: tuple[int, ...]
    conflicts: tuple[tuple[int, int], ...]
    penalty: int
    pair_penalties: tuple[int, ...] = ()

    @property
    def couplings(self) -> tuple[tuple[int, int, int], ...]:
        penalties = self.pair_penalties or (self.penalty,) * len(self.conflicts)
        return tuple((i, j, penalty) for (i, j), penalty in zip(self.conflicts, penalties))

    def energy(self, bits: Sequence[int]) -> int:
        return -sum(reward * bit for reward, bit in zip(self.rewards, bits)) + sum(
            penalty * bits[i] * bits[j] for i, j, penalty in self.couplings
        )

    def ising(self) -> tuple[float, tuple[float, ...], tuple[tuple[int, int, float], ...]]:
        """Return the offset, Z fields and ZZ couplings using x = (1 - Z) / 2."""
        offset = -sum(self.rewards) / 2
        fields = [reward / 2 for reward in self.rewards]
        couplings = []
        for i, j, penalty in self.couplings:
            coupling = penalty / 4
            couplings.append((i, j, coupling))
            offset += coupling
            fields[i] -= coupling
            fields[j] -= coupling
        return offset, tuple(fields), tuple(couplings)


def _layout(instance: Instance, packages: Sequence[Package], rng: Random | None, require_support: bool = False, priority=(2, 1, 0)):
    """Build one geometric layout using corners created within this run."""
    placed = []
    points = {(0, 0, 0)}
    bounds = instance.container.dimensions
    if priority == (2, 1, 0):
        position_key = lambda point: (point[2], point[1], point[0])
    else:
        position_key = lambda point: tuple(point[axis] for axis in priority)
    for package in packages:
        orientations = list(package.orientations)
        positions = sorted(points, key=position_key)
        if rng is not None:
            rng.shuffle(orientations)
            rng.shuffle(positions)
        for position, dimensions in product(positions, orientations):
            candidate = Placement(package.id, position, dimensions)
            if any(end > bound for end, bound in zip(candidate.end, bounds)):
                continue
            if any(overlaps(candidate, other) for other in placed):
                continue
            if require_support and not fully_supported(candidate, placed):
                continue
            placed.append(candidate)
            for axis in range(3):
                point = list(position)
                point[axis] = candidate.end[axis]
                if point[axis] < bounds[axis]:
                    points.add(tuple(point))
            yield candidate
            break


def generate_candidates(instance: Instance, cap: int, seed: int = 0, *,
                        require_support: bool = False, varied_corners: bool = False,
                        layout_count: int | None = None) -> tuple[Placement, ...]:
    """Mix independently constructed layouts without seeding from the baseline."""
    if cap < 1 or (layout_count is not None and layout_count < 1):
        raise ValueError("Candidate cap and layout count must be positive")
    rng = Random(seed)
    packages = sorted(
        (package for package in instance.packages
         if package.weight <= instance.container.max_payload),
        key=lambda package: package.id,
    )
    longest_first = sorted(packages, key=lambda package: -max(package.dimensions))
    small_first = sorted(packages, key=lambda package: prod(package.dimensions))
    candidates = {}
    priority = (2, 1, 0)
    orders = [(longest_first, None, priority), (small_first, None, priority)]
    if varied_corners:
        orders.extend((order, None, axes) for axes in permutations(range(3)) if axes != priority
                      for order in (longest_first, small_first))
    limit = layout_count if layout_count is not None else (
        len(orders) + max(12, cap // max(1, len(packages)) * 3)
    )
    for _ in range(max(0, limit - len(orders))):
        order = packages.copy()
        rng.shuffle(order)
        orders.append((order, Random(rng.getrandbits(64)), priority))
    for order, layout_rng, axes in orders[:limit]:
        for candidate in _layout(instance, order, layout_rng, require_support, axes):
            candidates[candidate] = None
            if len(candidates) == cap:
                return tuple(candidates)
    return tuple(candidates)


def build_qubo(candidates: Sequence[Placement], penalty: int | None = None, *,
               rewards: tuple[int, ...] | None = None, pairwise: bool = False) -> Qubo:
    if rewards is None:
        rewards = tuple(prod(candidate.dimensions) for candidate in candidates)
    largest = max(0, max(rewards, default=0))
    if penalty is None:
        penalty = largest + 1
    if penalty <= largest:
        raise ValueError("Conflict penalty must exceed the largest volume reward")
    conflicts = tuple(
        (i, j)
        for (i, first), (j, second) in combinations(enumerate(candidates), 2)
        if first.package_id == second.package_id or overlaps(first, second)
    )
    pairs = tuple(max(0, min(rewards[i], rewards[j])) + 1 for i, j in conflicts) if pairwise else ()
    return Qubo(rewards, conflicts, penalty, pairs)


def annealing_reads(qubo: Qubo, seed: int, sweeps: int, reads: int) -> Iterator[tuple[int, ...]]:
    if sweeps < 1 or reads < 1:
        raise ValueError("Sweeps and reads must be positive")
    rng = Random(seed)
    neighbors = [[] for _ in qubo.rewards]
    for i, j, penalty in qubo.couplings:
        neighbors[i].append((j, penalty))
        neighbors[j].append((i, penalty))

    order = list(range(len(qubo.rewards)))
    for _ in range(reads):
        bits = [0 for _ in order]
        best_bits = tuple(bits)
        best_energy = energy = 0
        fields = [-reward for reward in qubo.rewards]
        for sweep in range(sweeps):
            fraction = sweep / max(1, sweeps - 1)
            temperature = qubo.penalty * 2 * 0.005 ** fraction
            rng.shuffle(order)
            for i in order:
                change = 1 - 2 * bits[i]
                delta = change * fields[i]
                if delta <= 0 or rng.random() < exp(-delta / temperature):
                    bits[i] ^= 1
                    for j, penalty in neighbors[i]:
                        fields[j] += change * penalty
                    energy += delta
                    if energy < best_energy:
                        best_energy = energy
                        best_bits = tuple(bits)
        yield best_bits


def anneal(qubo: Qubo, seed: int, sweeps: int, reads: int) -> tuple[int, ...]:
    return min(annealing_reads(qubo, seed, sweeps, reads), key=qubo.energy)


@dataclass(frozen=True)
class PayloadSlack:
    """Squared payload residual in ticks, with binary slack minimized analytically."""

    weights: tuple[int, ...]
    capacity: int
    penalty: int

    @property
    def bits(self) -> int:
        return self.capacity.bit_length()

    def energy(self, weight: int) -> int:
        # Slack bits represent every integer from zero through capacity.
        # The optimal slack is capacity - weight below capacity and zero above it.
        return self.penalty * max(0, weight - self.capacity) ** 2


def compound_anneal(qubo: Qubo, seed: int, sweeps: int, reads: int, *,
                    payload: PayloadSlack | None = None,
                    support_candidates: tuple[Placement, ...] | None = None) -> tuple[int, ...]:
    """Search conflict-free states with insertions, removals and compound swaps."""
    if sweeps < 1 or reads < 1:
        raise ValueError("Sweeps and reads must be positive")
    rng = Random(seed)
    order = list(range(len(qubo.rewards)))
    neighbors = [set() for _ in order]
    for i, j in qubo.conflicts:
        neighbors[i].add(j)
        neighbors[j].add(i)

    support_areas = {}
    if support_candidates is not None:
        for i, placement in enumerate(support_candidates):
            if placement.position[2] > 0:
                contacts = {}
                for j, other in enumerate(support_candidates):
                    area = supported_area(placement, (other,))
                    if area:
                        contacts[j] = area
                support_areas[i] = (placement.dimensions[0] * placement.dimensions[1], contacts)

    def preserves_support(selected, blocking, inserted):
        if support_candidates is None:
            return True
        proposed = selected - blocking
        if inserted is not None:
            proposed.add(inserted)
        return all(
            sum(area for j, area in support_areas[i][1].items() if j in proposed) == support_areas[i][0]
            for i in proposed if i in support_areas
        )

    def move(i, blocking, inserting, weight):
        delta = sum(qubo.rewards[j] for j in blocking)
        if inserting:
            delta -= qubo.rewards[i]
        if payload is None:
            return delta, weight
        new_weight = weight - sum(payload.weights[j] for j in blocking)
        if inserting:
            new_weight += payload.weights[i]
        return delta + payload.energy(new_weight) - payload.energy(weight), new_weight

    # Probe moves in randomized feasible states to calibrate the cooling range.
    costs = []
    for _ in range(8):
        selected = set()
        weight = 0
        rng.shuffle(order)
        for i in order:
            blocking = neighbors[i] & selected
            delta, new_weight = move(i, blocking, True, weight)
            if delta:
                costs.append(abs(delta))
            if not blocking and delta < 0 and preserves_support(selected, blocking, i):
                selected.add(i)
                weight = new_weight
    hot = median(costs) / -log(.8) if costs else 1.0
    cold = min(costs) / -log(.01) if costs else .01

    best_energy = 0
    best = set()
    best_weight = 0
    for _ in range(reads):
        selected = set()
        energy = weight = 0
        for sweep in range(sweeps):
            temperature = hot * (cold / hot) ** (sweep / max(1, sweeps - 1))
            rng.shuffle(order)
            for i in order:
                removing = i in selected
                blocking = {i} if removing else neighbors[i] & selected
                delta, new_weight = move(i, blocking, not removing, weight)
                if delta <= 0 or rng.random() < exp(-delta / temperature):
                    if not preserves_support(selected, blocking, None if removing else i):
                        continue
                    selected.difference_update(blocking)
                    if not removing:
                        selected.add(i)
                    energy += delta
                    weight = new_weight
                    if energy < best_energy:
                        best_energy = energy
                        best = selected.copy()
                        best_weight = weight
    # Strict descent terminates because every accepted swap improves integer energy.
    while True:
        for i in range(len(order)):
            removing = i in best
            blocking = {i} if removing else neighbors[i] & best
            delta, new_weight = move(i, blocking, not removing, best_weight)
            if delta < 0 and preserves_support(best, blocking, None if removing else i):
                best.difference_update(blocking)
                if not removing:
                    best.add(i)
                best_weight = new_weight
                break
        else:
            return tuple(int(i in best) for i in range(len(order)))


def critical_weight_price(instance: Instance) -> Fraction:
    """Return the marginal volume per gram in the fractional knapsack."""
    weighted = sorted(
        ((Fraction(prod(p.dimensions), p.weight), p.weight) for p in instance.packages if p.weight),
        reverse=True,
    )
    remaining = instance.container.max_payload
    for ratio, weight in weighted:
        if weight > remaining:
            return ratio
        remaining -= weight
    return Fraction(0)


def greedy_repair(instance: Instance, selected: Sequence[Placement]) -> tuple[Placement, ...]:
    """Keep feasible placements greedily by decreasing volume, retaining ties in input order."""
    kept: tuple[Placement, ...] = ()
    for candidate in sorted(selected, key=lambda placement: -prod(placement.dimensions)):
        trial = (*kept, candidate)
        if validate_packing(instance, trial).valid:
            kept = trial
    return kept


def repair(instance: Instance, selected: Sequence[Placement]) -> tuple[Placement, ...]:
    """Resolve geometric conflicts, then maximize volume within the payload."""
    weights = {package.id: package.weight for package in instance.packages}
    relaxed = replace(instance, container=replace(instance.container, max_payload=sum(weights.values())))
    eligible = greedy_repair(relaxed, selected)
    capacity = instance.container.max_payload
    if sum(weights[p.package_id] for p in eligible) <= capacity:
        return eligible

    states: dict[int, tuple[int, tuple[Placement, ...]]] = {0: (0, ())}
    for placement in eligible:
        weight = weights[placement.package_id]
        value = prod(placement.dimensions)
        for used, (volume, chosen) in list(states.items()):
            new_weight = used + weight
            if new_weight <= capacity and volume + value > states.get(new_weight, (-1, ()))[0]:
                states[new_weight] = (volume + value, (*chosen, placement))
        # A heavier state with no greater value cannot improve any later choice.
        frontier = {}
        best = -1
        for used, state in sorted(states.items()):
            if state[0] > best:
                frontier[used] = state
                best = state[0]
        states = frontier
    return max(states.values(), key=lambda state: state[0])[1]


def exact_weight_unit(instance: Instance) -> int:
    """Largest unit that represents all original gram weights exactly."""
    return gcd(instance.container.max_payload, *(p.weight for p in instance.packages)) or 1


def remove_unsupported(placements: Sequence[Placement]) -> tuple[Placement, ...]:
    kept = []
    for placement in sorted(placements, key=lambda p: p.position[2]):
        if fully_supported(placement, kept):
            kept.append(placement)
    return tuple(kept)


def solve(instance: Instance, cap: int, seed: int, sweeps: int, reads: int,
          penalty_factor: float = 1.0, sampler=compound_anneal, *,
          pool_seed: int | None = None, anneal_seed: int | None = None,
          weight_multiplier: float = 0, repairer=repair, pairwise: bool = False,
          slack_weight_unit: int | None = None, exact_slack: bool = False,
          require_support: bool = False, support_during_search: bool = False) -> dict:
    started = perf_counter()
    pool_seed = seed if pool_seed is None else pool_seed
    anneal_seed = seed if anneal_seed is None else anneal_seed
    if weight_multiplier < 0:
        raise ValueError("Weight multiplier must be nonnegative")
    candidates = generate_candidates(instance, cap, pool_seed, require_support=require_support)
    price = critical_weight_price(instance) * Fraction(str(weight_multiplier))
    weights = {package.id: package.weight for package in instance.packages}
    rewards = tuple(round(prod(p.dimensions) - price * weights[p.package_id]) for p in candidates)
    largest_reward = max(rewards, default=0)
    qubo = build_qubo(candidates, int(max(0, largest_reward) * penalty_factor) + 1,
                      rewards=rewards, pairwise=pairwise)
    payload = None
    if support_during_search and (not require_support or sampler is not compound_anneal):
        raise ValueError("Support-aware search requires support mode and compound search")
    if exact_slack:
        slack_weight_unit = exact_weight_unit(instance)
    if slack_weight_unit is not None:
        if slack_weight_unit < 1 or sampler is not compound_anneal or weight_multiplier:
            raise ValueError("Slack requires a positive weight unit and unpriced compound search")
        payload = PayloadSlack(
            tuple((weights[p.package_id] + slack_weight_unit - 1) // slack_weight_unit for p in candidates),
            instance.container.max_payload // slack_weight_unit,
            max(0, largest_reward) + 1,
        )
        sampler = partial(sampler, payload=payload)
    if support_during_search:
        sampler = partial(sampler, support_candidates=candidates)
    anneal_started = perf_counter()
    bits = sampler(qubo, anneal_seed, sweeps, reads)
    annealing_seconds = perf_counter() - anneal_started

    raw = tuple(candidate for candidate, bit in zip(candidates, bits) if bit)
    raw_result = validate_packing(instance, raw, require_support=require_support)
    final = repairer(instance, raw)
    removed_by_repair = len(raw) - len(final)
    before_support = len(final)
    if require_support:
        final = remove_unsupported(final)
    result = validate_packing(instance, final, require_support=require_support)
    return {
        "valid": result.valid,
        **asdict(result),
        "runtime_seconds": perf_counter() - started,
        "annealing_seconds": annealing_seconds,
        "seed": seed,
        "pool_seed": pool_seed,
        "anneal_seed": anneal_seed,
        "weight_multiplier": weight_multiplier,
        "weight_price_mm3_per_g": float(price),
        "pairwise_penalties": pairwise,
        "sweeps": sweeps,
        "reads": reads,
        "candidate_cap": cap,
        "penalty_factor": penalty_factor,
        "qubo_variables": len(candidates),
        "qubo_conflicts": len(qubo.conflicts),
        "conflict_penalty": qubo.penalty,
        "slack_weight_unit_g": slack_weight_unit,
        "slack_bits": payload.bits if payload else 0,
        "slack_penalty": payload.penalty if payload else None,
        "raw_energy": qubo.energy(bits) + (
            payload.energy(sum(weight * bit for weight, bit in zip(payload.weights, bits))) if payload else 0
        ),
        "raw_valid": raw_result.valid,
        "raw_violations": raw_result.violations,
        "raw_placements": [asdict(placement) for placement in raw],
        "removed_by_repair": removed_by_repair,
        "removed_by_support": before_support - len(final),
        "support_during_search": support_during_search,
        "placements": [asdict(placement) for placement in final],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--cap", type=int, default=240)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--sweeps", type=int, default=200)
    parser.add_argument("--reads", type=int, default=16)
    parser.add_argument("--penalty-factor", type=float, default=1.0)
    parser.add_argument("--pool-seed", type=int)
    parser.add_argument("--anneal-seed", type=int)
    parser.add_argument("--weight-multiplier", type=float, default=0)
    slack = parser.add_mutually_exclusive_group()
    slack.add_argument("--slack-weight-unit", type=int)
    slack.add_argument("--exact-slack", action="store_true")
    parser.add_argument("--require-support", action="store_true")
    parser.add_argument("--support-during-search", action="store_true")
    args = parser.parse_args()
    try:
        report = solve(load_instance(args.dataset), args.cap, args.seed, args.sweeps, args.reads,
                       args.penalty_factor, pool_seed=args.pool_seed, anneal_seed=args.anneal_seed,
                       weight_multiplier=args.weight_multiplier, slack_weight_unit=args.slack_weight_unit,
                       exact_slack=args.exact_slack, require_support=args.require_support,
                       support_during_search=args.support_during_search)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
