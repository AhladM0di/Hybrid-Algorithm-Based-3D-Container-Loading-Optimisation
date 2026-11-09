"""Probe corner order, layout count and cap on three geometry cases."""

import argparse
import csv
import json
from math import prod
from pathlib import Path

from feasibility import validate_packing
from heldout_benchmark import generate_case
from hybrid import build_qubo, generate_candidates
from reference_solver import _optimize


def run(output: Path):
    recorded = json.loads(Path("results/heldout/heldout.json").read_text())
    rows = []
    for case in recorded["cases"]:
        if case["seed"] not in (4100, 4101, 4102):
            continue
        seed = case["seed"]
        trial = case["modes"]["brief"]["trials"][0]["hybrid"]
        instance, witness = generate_case("geometry", len(case["instance"]["packages"]), seed)
        assert validate_packing(instance, witness).metrics.utilization == 1
        volume = prod(instance.container.dimensions)
        for cap, layouts, varied in ((160, 16, False), (160, 32, False),
                                     (160, 32, True), (320, 32, True)):
            candidates = generate_candidates(instance, cap, trial["pool_seed"],
                                             varied_corners=varied, layout_count=layouts)
            result = _optimize(candidates, build_qubo(candidates), instance, time_limit=4)
            selected = tuple(candidates[i] for i in result["selected"])
            if not validate_packing(instance, selected).valid:
                raise RuntimeError("Invalid coverage reference")
            rows.append({
                "case": seed, "pool_seed": trial["pool_seed"], "cap": cap, "layout_limit": layouts,
                "varied_corners": varied, "candidates": len(candidates), "solver_status": result["solver_status"],
                "utilization_lower": result["volume"] / volume,
                "utilization_upper": min(volume, result["upper_bound"] if result["upper_bound"] is not None else volume) / volume,
            })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/effort/coverage.csv"))
    run(parser.parse_args().output)
