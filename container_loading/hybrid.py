"""Generate placements, sample a QUBO and repair the selected packing."""

import argparse
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations, product
import json
from math import exp, prod
from pathlib import Path
from random import Random
from time import perf_counter

from check_packing import load_instance
from feasibility import Instance, Package, Placement, overlaps, validate_packing


@dataclass(frozen=True)
class Qubo:
    rewards: tuple[int, ...]
    conflicts: tuple[tuple[int, int], ...]
    penalty: int

    def energy(self, bits: Sequence[int]) -> int:
        return -sum(reward * bit for reward, bit in zip(self.rewards, bits)) + sum(
            self.penalty * bits[i] * bits[j] for i, j in self.conflicts
        )

    def ising(self) -> tuple[float, tuple[float, ...], tuple[tuple[int, int, float], ...]]:
        """Return the offset, Z fields and ZZ couplings using x = (1 - Z) / 2."""
        offset = -sum(self.rewards) / 2
        fields = [reward / 2 for reward in self.rewards]
        coupling = self.penalty / 4
        for i, j in self.conflicts:
            offset += coupling
            fields[i] -= coupling
            fields[j] -= coupling
        return offset, tuple(fields), tuple((i, j, coupling) for i, j in self.conflicts)


def _layout(instance: Instance, packages: Sequence[Package], rng: Random | None):
    """Build one geometric layout using corners created within this run."""
    placed = []
    points = {(0, 0, 0)}
    bounds = instance.container.dimensions
    for package in packages:
        orientations = list(package.orientations)
        positions = sorted(points, key=lambda point: (point[2], point[1], point[0]))
        if rng is not None:
            rng.shuffle(orientations)
            rng.shuffle(positions)
        for position, dimensions in product(positions, orientations):
            candidate = Placement(package.id, position, dimensions)
            if any(end > bound for end, bound in zip(candidate.end, bounds)):
                continue
            if any(overlaps(candidate, other) for other in placed):
                continue
            placed.append(candidate)
            for axis in range(3):
                point = list(position)
                point[axis] = candidate.end[axis]
                if point[axis] < bounds[axis]:
                    points.add(tuple(point))
            yield candidate
            break


def generate_candidates(instance: Instance, cap: int, seed: int = 0) -> tuple[Placement, ...]:
    """Mix independently constructed layouts without seeding from the baseline."""
    if cap < 1:
        raise ValueError("Candidate cap must be positive")
    rng = Random(seed)
    packages = sorted(
        (package for package in instance.packages
         if package.weight <= instance.container.max_payload),
        key=lambda package: package.id,
    )
    longest_first = sorted(packages, key=lambda package: -max(package.dimensions))
    small_first = sorted(packages, key=lambda package: prod(package.dimensions))
    candidates = {}
    orders = [(longest_first, None), (small_first, None)]
    for _ in range(max(12, cap // max(1, len(packages)) * 3)):
        order = packages.copy()
        rng.shuffle(order)
        orders.append((order, Random(rng.getrandbits(64))))
    for order, layout_rng in orders:
        for candidate in _layout(instance, order, layout_rng):
            candidates[candidate] = None
            if len(candidates) == cap:
                return tuple(candidates)
    return tuple(candidates)


def build_qubo(candidates: Sequence[Placement], penalty: int | None = None) -> Qubo:
    rewards = tuple(prod(candidate.dimensions) for candidate in candidates)
    largest = max(rewards, default=0)
    if penalty is None:
        penalty = largest + 1
    if penalty <= largest:
        raise ValueError("Conflict penalty must exceed the largest volume reward")
    conflicts = tuple(
        (i, j)
        for (i, first), (j, second) in combinations(enumerate(candidates), 2)
        if first.package_id == second.package_id or overlaps(first, second)
    )
    return Qubo(rewards, conflicts, penalty)


def annealing_reads(qubo: Qubo, seed: int, sweeps: int, reads: int) -> Iterator[tuple[int, ...]]:
    if sweeps < 1 or reads < 1:
        raise ValueError("Sweeps and reads must be positive")
    rng = Random(seed)
    neighbors = [[] for _ in qubo.rewards]
    for i, j in qubo.conflicts:
        neighbors[i].append(j)
        neighbors[j].append(i)

    order = list(range(len(qubo.rewards)))
    for _ in range(reads):
        bits = [0 for _ in order]
        best_bits = tuple(bits)
        best_energy = energy = 0
        for sweep in range(sweeps):
            fraction = sweep / max(1, sweeps - 1)
            temperature = qubo.penalty * 2 * 0.005 ** fraction
            rng.shuffle(order)
            for i in order:
                delta = (1 - 2 * bits[i]) * (
                    -qubo.rewards[i] + qubo.penalty * sum(bits[j] for j in neighbors[i])
                )
                if delta <= 0 or rng.random() < exp(-delta / temperature):
                    bits[i] ^= 1
                    energy += delta
                    if energy < best_energy:
                        best_energy = energy
                        best_bits = tuple(bits)
        yield best_bits


def anneal(qubo: Qubo, seed: int, sweeps: int, reads: int) -> tuple[int, ...]:
    return min(annealing_reads(qubo, seed, sweeps, reads), key=qubo.energy)


def repair(instance: Instance, selected: Sequence[Placement]) -> tuple[Placement, ...]:
    """Keep feasible placements greedily by decreasing volume, retaining ties in input order."""
    kept: tuple[Placement, ...] = ()
    for candidate in sorted(selected, key=lambda placement: -prod(placement.dimensions)):
        trial = (*kept, candidate)
        if validate_packing(instance, trial).valid:
            kept = trial
    return kept


def solve(instance: Instance, cap: int, seed: int, sweeps: int, reads: int,
          penalty_factor: float = 1.0, sampler=anneal) -> dict:
    started = perf_counter()
    candidates = generate_candidates(instance, cap, seed)
    largest_reward = max((prod(candidate.dimensions) for candidate in candidates), default=0)
    qubo = build_qubo(candidates, int(largest_reward * penalty_factor) + 1)
    anneal_started = perf_counter()
    bits = sampler(qubo, seed, sweeps, reads)
    annealing_seconds = perf_counter() - anneal_started

    raw = tuple(candidate for candidate, bit in zip(candidates, bits) if bit)
    raw_result = validate_packing(instance, raw)
    final = repair(instance, raw)
    result = validate_packing(instance, final)
    return {
        "valid": result.valid,
        **asdict(result),
        "runtime_seconds": perf_counter() - started,
        "annealing_seconds": annealing_seconds,
        "seed": seed,
        "sweeps": sweeps,
        "reads": reads,
        "candidate_cap": cap,
        "penalty_factor": penalty_factor,
        "qubo_variables": len(candidates),
        "qubo_conflicts": len(qubo.conflicts),
        "conflict_penalty": qubo.penalty,
        "raw_energy": qubo.energy(bits),
        "raw_valid": raw_result.valid,
        "raw_violations": raw_result.violations,
        "raw_placements": [asdict(placement) for placement in raw],
        "removed_by_repair": len(raw) - len(final),
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
    args = parser.parse_args()
    try:
        report = solve(load_instance(args.dataset), args.cap, args.seed, args.sweeps, args.reads, args.penalty_factor)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
