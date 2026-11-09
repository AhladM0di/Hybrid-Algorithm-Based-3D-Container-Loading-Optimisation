"""Diagnose candidate coverage and search gaps in the recorded geometry trials."""

import argparse
import csv
import json
from math import prod
from pathlib import Path

from feasibility import Container, Instance, Package, Placement, validate_packing
from hybrid import build_qubo, generate_candidates
from reference_solver import _optimize


def placements(records):
    return tuple(Placement(p["package_id"], tuple(p["position"]), tuple(p["dimensions"])) for p in records)


def run(source: Path, output: Path, time_limit: float) -> None:
    recorded = json.loads(source.read_text())
    rows = []
    for case in recorded["cases"]:
        if case["family"] != "geometry":
            continue
        data = case["instance"]
        container = data["container"]
        instance = Instance(
            Container(tuple(container["dimensions"]), container["max_payload"]),
            tuple(Package(p["id"], tuple(p["dimensions"]), p["weight"], p["allow_rotation"])
                  for p in data["packages"]),
        )
        volume = prod(instance.container.dimensions)
        witness = validate_packing(instance, placements(case["optimum_witness"]))
        if not witness.valid or witness.metrics.packed_volume != volume:
            raise RuntimeError("Full-container tiling failed validation")

        for trial in case["modes"]["brief"]["trials"]:
            hybrid = trial["hybrid"]
            candidates = generate_candidates(instance, hybrid["candidate_cap"], hybrid["pool_seed"])
            final = placements(hybrid["placements"])
            raw = placements(hybrid["raw_placements"])
            if len(candidates) != hybrid["qubo_variables"] or not set(raw).issubset(candidates):
                raise RuntimeError("Reconstructed pool differs from the recorded run")
            result = validate_packing(instance, final)
            if (not result.valid or not set(final).issubset(candidates)
                    or result.metrics.packed_volume != hybrid["metrics"]["packed_volume"]):
                raise RuntimeError("Recorded hybrid packing failed verification")

            qubo = build_qubo(candidates)
            reference = _optimize(candidates, qubo, instance, time_limit=time_limit)
            if len(qubo.conflicts) != hybrid["qubo_conflicts"]:
                raise RuntimeError("Reconstructed conflict count differs from the recorded run")
            selected = tuple(candidates[i] for i in reference["selected"])
            checked = validate_packing(instance, selected)
            if not checked.valid or checked.metrics.packed_volume != reference["volume"]:
                raise RuntimeError("HiGHS incumbent failed validation")

            hybrid_volume = result.metrics.packed_volume
            incumbent = reference["volume"]
            if reference["optimal"] and incumbent < hybrid_volume:
                raise RuntimeError("Recorded packing beats the reported optimum")
            lower = max(hybrid_volume, incumbent)
            upper = min(volume, reference["upper_bound"] or volume)
            if reference["optimal"]:
                upper = incumbent
            if lower > upper:
                raise RuntimeError("Inconsistent pool bounds")
            proven = lower == upper
            rows.append({
                "instance_seed": case["seed"], "packages": len(instance.packages),
                "trial_seed": trial["seed"], "pool_seed": hybrid["pool_seed"],
                "anneal_seed": hybrid["anneal_seed"], "candidates": len(candidates),
                "solver_status": reference["solver_status"], "highs_proven_optimal": reference["optimal"],
                "pool_optimum_proven": proven, "hybrid_utilization": hybrid_volume / volume,
                "highs_incumbent_utilization": incumbent / volume,
                "pool_lower_bound": lower / volume, "pool_upper_bound": upper / volume,
                "coverage_gap_lower_pp": 100 * (volume - upper) / volume,
                "coverage_gap_upper_pp": 100 * (volume - lower) / volume,
                "search_gap_lower_pp": 100 * (lower - hybrid_volume) / volume,
                "search_gap_upper_pp": 100 * (upper - hybrid_volume) / volume,
            })
            print(f"{case['seed']}/{trial['seed']}: {lower / volume:.2%}–{upper / volume:.2%}", flush=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("results/heldout/heldout.json"))
    parser.add_argument("--output", type=Path, default=Path("results/heldout/geometry_pool_check.csv"))
    parser.add_argument("--seconds", type=float, default=12)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("Time limit must be positive")
    run(args.source, args.output, args.seconds)
