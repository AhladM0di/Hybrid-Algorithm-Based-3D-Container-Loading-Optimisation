"""Run the deterministic First-Fit Decreasing packing baseline."""

import argparse
from dataclasses import asdict
from fractions import Fraction
from itertools import product
import json
from math import prod
from pathlib import Path
from random import Random
from time import perf_counter

from check_packing import load_instance
from feasibility import Instance, Placement, fully_supported, overlaps, validate_packing


def first_fit(instance: Instance, packages, orientation_order=lambda p: p.orientations, *,
              require_support: bool = False) -> tuple[Placement, ...]:
    placements = []
    coordinates = [{0}, {0}, {0}]
    remaining_payload = instance.container.max_payload

    for package in packages:
        if package.weight > remaining_payload:
            continue

        # Try lower z first, then y and x. At each position try the original
        # orientation before the remaining distinct permutations.
        orientations = orientation_order(package)
        x_values, y_values, z_values = map(sorted, coordinates)
        for z, y, x in product(z_values, y_values, x_values):
            position = (x, y, z)
            for dimensions in orientations:
                candidate = Placement(package.id, position, dimensions)
                if any(end > limit for end, limit in zip(candidate.end, instance.container.dimensions)):
                    continue
                if any(overlaps(candidate, placed) for placed in placements):
                    continue
                if require_support and not fully_supported(candidate, placements):
                    continue
                break
            else:
                continue

            placements.append(candidate)
            remaining_payload -= package.weight
            for axis_coordinates, end in zip(coordinates, candidate.end):
                axis_coordinates.add(end)
            break

    return tuple(placements)


def first_fit_decreasing(instance: Instance, *, require_support: bool = False) -> tuple[Placement, ...]:
    """Try larger packages first, breaking volume ties by package ID."""
    packages = sorted(instance.packages, key=lambda package: (-prod(package.dimensions), package.id))
    return first_fit(instance, packages, require_support=require_support)


def packing_report(instance, placements, started, require_support=False):
    result = validate_packing(instance, placements, require_support=require_support)
    return {
        "valid": result.valid,
        **asdict(result),
        "runtime_seconds": perf_counter() - started,
        "placements": [asdict(placement) for placement in placements],
    }


def baseline_report(instance: Instance, *, require_support: bool = False) -> dict:
    started = perf_counter()
    placements = first_fit_decreasing(instance, require_support=require_support)
    return packing_report(instance, placements, started, require_support)


def payload_order(instance: Instance):
    """Return a volume-maximizing weight-only subset, in decreasing size order."""
    packages = sorted(instance.packages, key=lambda p: (-prod(p.dimensions), p.id))
    states = {0: (0, ())}
    for package in packages:
        volume = prod(package.dimensions)
        for used, (packed, subset) in list(states.items()):
            weight = used + package.weight
            if (weight <= instance.container.max_payload
                    and packed + volume > states.get(weight, (-1, ()))[0]):
                states[weight] = (packed + volume, (*subset, package))
        frontier = {}
        best = -1
        for weight, state in sorted(states.items()):
            if state[0] > best:
                frontier[weight] = state
                best = state[0]
        states = frontier
    return max(states.values(), key=lambda state: state[0])[1]


def knapsack_first_fit_report(instance: Instance) -> dict:
    started = perf_counter()
    return packing_report(instance, first_fit(instance, payload_order(instance)), started)


def multistart_report(instance: Instance, seconds: float, seed: int, *, require_support=False,
                      weight_aware=False, max_attempts=None) -> dict:
    started = perf_counter()
    deadline = started + seconds
    rng = Random(seed)
    best = packing_report(instance, (), started, require_support)
    attempts = 0
    packages = list(instance.packages)
    upper_bound = min(prod(instance.container.dimensions), sum(prod(p.dimensions) for p in packages))
    def orientations(package):
        return rng.sample(package.orientations, len(package.orientations))

    while perf_counter() < deadline and (max_attempts is None or attempts < max_attempts):
        if attempts == 0:
            placements = first_fit_decreasing(instance, require_support=require_support)
        else:
            if attempts == 1:
                packages.sort(key=lambda p: (-max(p.dimensions), p.id))
            elif weight_aware and attempts == 2:
                packages.sort(key=lambda p: (p.weight > 0, -Fraction(prod(p.dimensions), p.weight or 1)))
            elif weight_aware and attempts == 3:
                subset = payload_order(instance)
                chosen = set(subset)
                packages = [*subset, *(p for p in packages if p not in chosen)]
            else:
                rng.shuffle(packages)
            order = orientations if not weight_aware or attempts != 3 else lambda p: p.orientations
            placements = first_fit(instance, packages, order, require_support=require_support)
        report = packing_report(instance, placements, started, require_support)
        finished = perf_counter()
        if finished > deadline:
            break
        report["runtime_seconds"] = finished - started
        attempts += 1
        if report["valid"] and report["metrics"]["packed_volume"] > best["metrics"]["packed_volume"]:
            best = report
        if best["metrics"]["packed_volume"] == upper_bound:
            break
    return {**best, "completed_attempts": attempts, "elapsed_seconds": perf_counter() - started}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--seconds", type=float)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--require-support", action="store_true")
    args = parser.parse_args()
    try:
        instance = load_instance(args.dataset)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))

    if args.seconds is not None and args.seconds <= 0:
        parser.error("Time budget must be positive")
    report = (baseline_report(instance, require_support=args.require_support) if args.seconds is None else
              multistart_report(instance, args.seconds, args.seed, require_support=args.require_support))
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
