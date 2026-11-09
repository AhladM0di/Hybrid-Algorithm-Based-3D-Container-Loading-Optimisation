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

from baseline import first_fit_decreasing
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


def _package_candidates(
    instance: Instance, package: Package, axes: tuple[tuple[int, ...], ...]
) -> Iterator[Placement]:
    for dimensions in package.orientations:
        limits = tuple(bound - size for bound, size in zip(instance.container.dimensions, dimensions))
        if min(limits) < 0:
            continue
        x_values, y_values, z_values = (
            sorted({limit, *(value for value in axis if value <= limit)})
            for axis, limit in zip(axes, limits)
        )
        for z, y, x in product(z_values, y_values, x_values):
            yield Placement(package.id, (x, y, z), dimensions)


def generate_candidates(instance: Instance, cap: int) -> tuple[Placement, ...]:
    baseline = first_fit_decreasing(instance)
    if cap < max(1, len(baseline)):
        raise ValueError("Candidate cap must be positive and fit all baseline placements")

    axes = tuple(tuple(sorted({0, *(placement.end[i] for placement in baseline)})) for i in range(3))
    candidates = dict.fromkeys(baseline)
    active = [
        _package_candidates(instance, package, axes)
        for package in sorted(instance.packages, key=lambda package: package.id)
        if package.weight <= instance.container.max_payload
    ]
    while active and len(candidates) < cap:
        next_round = []
        for options in active:
            for candidate in options:
                if candidate not in candidates:
                    candidates[candidate] = None
                    next_round.append(options)
                    break
            if len(candidates) == cap:
                break
        active = next_round
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


def solve(instance: Instance, cap: int, seed: int, sweeps: int, reads: int) -> dict:
    started = perf_counter()
    candidates = generate_candidates(instance, cap)
    qubo = build_qubo(candidates)
    anneal_started = perf_counter()
    bits = anneal(qubo, seed, sweeps, reads)
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
    parser.add_argument("--cap", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--sweeps", type=int, default=200)
    parser.add_argument("--reads", type=int, default=16)
    args = parser.parse_args()
    try:
        report = solve(load_instance(args.dataset), args.cap, args.seed, args.sweeps, args.reads)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
