"""Run the deterministic First-Fit Decreasing packing baseline."""

import argparse
from dataclasses import asdict
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


def multistart_report(instance: Instance, seconds: float, seed: int, *, require_support=False) -> dict:
    started = perf_counter()
    deadline = started + seconds
    rng = Random(seed)
    best = packing_report(instance, (), started, require_support)
    attempts = 0
    packages = list(instance.packages)
    upper_bound = min(prod(instance.container.dimensions), sum(prod(p.dimensions) for p in packages))
    while perf_counter() < deadline:
        if attempts == 0:
            placements = first_fit_decreasing(instance, require_support=require_support)
        else:
            if attempts == 1:
                packages.sort(key=lambda p: (-max(p.dimensions), p.id))
            else:
                rng.shuffle(packages)
            def orientations(package):
                return rng.sample(package.orientations, len(package.orientations))
            placements = first_fit(instance, packages, orientations, require_support=require_support)
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
