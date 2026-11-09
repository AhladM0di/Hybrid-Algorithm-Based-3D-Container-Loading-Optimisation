"""Run the deterministic First-Fit Decreasing packing baseline."""

import argparse
from dataclasses import asdict
from itertools import product
import json
from math import prod
from pathlib import Path
from time import perf_counter

from check_packing import load_instance
from feasibility import Instance, Placement, overlaps, validate_packing


def first_fit_decreasing(instance: Instance) -> tuple[Placement, ...]:
    """Try larger packages first, breaking volume ties by package ID."""
    placements = []
    coordinates = [{0}, {0}, {0}]
    remaining_payload = instance.container.max_payload
    packages = sorted(instance.packages, key=lambda package: (-prod(package.dimensions), package.id))

    for package in packages:
        if package.weight > remaining_payload:
            continue

        # Try lower z first, then y and x. At each position try the original
        # orientation before the remaining distinct permutations.
        orientations = package.orientations
        x_values, y_values, z_values = map(sorted, coordinates)
        for z, y, x in product(z_values, y_values, x_values):
            position = (x, y, z)
            for dimensions in orientations:
                candidate = Placement(package.id, position, dimensions)
                if any(end > limit for end, limit in zip(candidate.end, instance.container.dimensions)):
                    continue
                if any(overlaps(candidate, placed) for placed in placements):
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


def baseline_report(instance: Instance) -> dict:
    started = perf_counter()
    placements = first_fit_decreasing(instance)
    result = validate_packing(instance, placements)
    runtime_seconds = perf_counter() - started
    return {
        "valid": result.valid,
        **asdict(result),
        "runtime_seconds": runtime_seconds,
        "placements": [asdict(placement) for placement in placements],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    try:
        instance = load_instance(args.dataset)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))

    report = baseline_report(instance)
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
