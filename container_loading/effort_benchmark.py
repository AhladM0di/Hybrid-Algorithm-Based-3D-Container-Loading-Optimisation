"""Compare fixed work and wall-clock budgets on the existing held-out cases."""

import argparse
import csv
import json
from math import inf, prod
from pathlib import Path
from statistics import mean

from baseline import knapsack_first_fit_report, multistart_report, payload_order
from heldout_benchmark import PROTOCOL, generate_case, hybrid_report


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(output, *, fixed_only=False):
    output.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(PROTOCOL.read_text())
    settings = protocol["hybrid"]
    seed = protocol["trial_seeds"][0]
    rows = []
    controls = []
    for family, seeds in protocol["generator_seeds"].items():
        for index, (count, generator_seed) in enumerate(zip(protocol["counts"], seeds, strict=True)):
            instance, _ = generate_case(family, count, generator_seed)
            control = knapsack_first_fit_report(instance)
            if not control["valid"]:
                raise RuntimeError("Invalid weight-only baseline")
            container_volume = prod(instance.container.dimensions)
            controls.append({
                "family": family, "generator_seed": generator_seed,
                "knapsack_first_fit_utilization": control["metrics"]["utilization"],
                "weight_volume_upper_bound": min(1, sum(prod(p.dimensions) for p in payload_order(instance))
                                                / container_volume),
                "runtime_seconds": control["runtime_seconds"],
            })
            modes = [("fixed_work", inf, 4)]
            if not fixed_only:
                modes.extend(("wall_clock", seconds, None) for seconds in (.15, .5, 1.5))
                if index < 3:
                    modes.append(("wall_clock_subset", 5, None))
            for mode, budget, attempts in modes:
                methods = {
                    "first_fit": lambda: multistart_report(instance, budget, seed,
                                                          weight_aware=True, max_attempts=attempts),
                    "hybrid": lambda: hybrid_report(instance, budget, seed, settings,
                                                    require_support=False, max_attempts=attempts),
                }
                order = tuple(methods)
                if generator_seed % 2:
                    order = order[::-1]
                for method in order:
                    report = methods[method]()
                    if not report["valid"] or not report["completed_attempts"]:
                        raise RuntimeError(f"No valid result for {generator_seed}/{mode}/{method}")
                    rows.append({
                        "mode": mode, "budget_seconds": None if budget == inf else budget,
                        "attempt_limit": attempts, "family": family, "generator_seed": generator_seed,
                        "trial_seed": seed, "method": method,
                        "utilization": report["metrics"]["utilization"],
                        "completed_attempts": report["completed_attempts"],
                        "elapsed_seconds": report["elapsed_seconds"],
                    })
            print(f"{family} {generator_seed} complete", flush=True)
    write_csv(output / "runs.csv", rows)
    write_csv(output / "weight_only_control.csv", controls)
    groups = {}
    for row in rows:
        for family in ("all", row["family"]):
            key = (row["mode"], row["budget_seconds"], row["attempt_limit"], family, row["method"])
            groups.setdefault(key, []).append(row)
    summary = []
    for (mode, budget, limit, family, method), group in groups.items():
        counts = [r["completed_attempts"] for r in group]
        summary.append({
            "mode": mode, "budget_seconds": budget, "attempt_limit": limit, "family": family, "method": method,
            "cases": len(group), "utilization_mean": mean(r["utilization"] for r in group),
            "attempts_mean": mean(counts), "attempts_min": min(counts), "attempts_max": max(counts),
            "elapsed_seconds_mean": mean(r["elapsed_seconds"] for r in group),
        })
    write_csv(output / "summary.csv", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/effort"))
    parser.add_argument("--fixed-only", action="store_true")
    args = parser.parse_args()
    run(args.output, fixed_only=args.fixed_only)
