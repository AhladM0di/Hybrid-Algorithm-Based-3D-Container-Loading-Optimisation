"""Run the matched repair and search ablations on fixed candidate pools."""

import argparse
import csv
from importlib.metadata import version
import json
from math import prod
from pathlib import Path
from statistics import mean

from baseline import baseline_report
from check_packing import load_instance, load_placements
from feasibility import validate_packing
from hybrid import anneal, compound_anneal, greedy_repair, repair, solve
from reference_solver import compare_pool


VARIANTS = (
    ("single_greedy", anneal, greedy_repair, 0, False, None),
    ("single_exact", anneal, repair, 0, False, None),
    ("single_exact_pairwise", anneal, repair, 0, True, None),
    ("compound_exact", compound_anneal, repair, 0, False, None),
    ("compound_price_0.5", compound_anneal, repair, 0.5, False, None),
    ("compound_price_0.75", compound_anneal, repair, 0.75, False, None),
    ("compound_price_1.0", compound_anneal, repair, 1, False, None),
    ("compound_slack", compound_anneal, repair, 0, False, 10_000),
)


def weight_only_bound(instance):
    states = {0: 0}
    for package in instance.packages:
        for weight, volume in list(states.items()):
            total = weight + package.weight
            if total <= instance.container.max_payload:
                states[total] = max(states.get(total, 0), volume + prod(package.dimensions))
    return min(max(states.values()), prod(instance.container.dimensions))


def run(output: Path, pool_count: int, seed_count: int, sweeps: int, reads: int, *,
        exact_slack_only: bool = False) -> None:
    variants = (("compound_slack_exact", compound_anneal, repair, 0, False, None),) if exact_slack_only else VARIANTS
    output.mkdir(parents=True, exist_ok=True)
    data = Path(__file__).resolve().parent / "data"
    cases = {}
    summary = []
    for case in ("packages_20", "geometry_10", "geometry_15"):
        instance = load_instance(data / f"{case}.json")
        bound = weight_only_bound(instance)
        witness = data / f"{case}_witness.json"
        if witness.exists():
            result = validate_packing(instance, load_placements(witness))
            if not result.valid or result.metrics.packed_volume != bound:
                raise RuntimeError(f"Invalid optimum witness for {case}")
        baseline = baseline_report(instance)
        pools = []
        for pool_seed in range(pool_count):
            runs = []
            for anneal_seed in range(seed_count):
                for label, sampler, repairer, multiplier, pairwise, slack_unit in variants:
                    report = solve(instance, cap=240, seed=0, pool_seed=pool_seed, anneal_seed=anneal_seed,
                                   sweeps=sweeps, reads=reads, sampler=sampler, repairer=repairer,
                                   weight_multiplier=multiplier, pairwise=pairwise, slack_weight_unit=slack_unit,
                                   exact_slack=exact_slack_only)
                    if not report["valid"]:
                        raise RuntimeError(f"Invalid repaired packing for {case}/{label}")
                    runs.append({"variant": label, **report})
            reference = compare_pool(instance, 240, pool_seed, runs[0]["raw_energy"])
            ceiling = reference["with_payload"]
            for report in runs:
                volume = report["metrics"]["packed_volume"]
                if ceiling["optimal"] and volume > ceiling["volume"]:
                    raise RuntimeError("Annealer beat the certified pool optimum")
                report["search_quality"] = (
                    volume / ceiling["volume"] if ceiling["optimal"] and ceiling["volume"] else None
                )
            pools.append({
                "pool_seed": pool_seed,
                "reference": reference,
                "pool_quality": ceiling["volume"] / bound if ceiling["optimal"] and bound else None,
                "runs": runs,
            })
            print(f"{case} pool {pool_seed + 1}/{pool_count}", flush=True)
        cases[case] = {"baseline": baseline, "full_instance_upper_bound_mm3": bound, "pools": pools}
        for label, *_ in variants:
            runs = [run for pool in pools for run in pool["runs"] if run["variant"] == label]
            ratios = [run["search_quality"] for run in runs if run["search_quality"] is not None]
            summary.append({
                "case": case, "variant": label, "runs": len(runs),
                "utilization_mean": mean(run["metrics"]["utilization"] for run in runs),
                "utilization_best": max(run["metrics"]["utilization"] for run in runs),
                "runtime_seconds_mean": mean(run["runtime_seconds"] for run in runs),
                "raw_invalid": sum(not run["raw_valid"] for run in runs),
                "repair_removals": sum(run["removed_by_repair"] for run in runs),
                "certified_search_ratios": len(ratios),
                "search_quality_mean": mean(ratios) if ratios else None,
            })

    report = {
        "configuration": {"pool_seeds": list(range(pool_count)), "anneal_seeds": list(range(seed_count)),
                          "sweeps": sweeps, "reads": reads, "cap": 240, "scipy": version("scipy")},
        "cases": cases,
    }
    (output / "ablation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (output / "ablation.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--exact-slack-only", action="store_true")
    parser.add_argument("--pools", type=int, default=5)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--sweeps", type=int, default=80)
    parser.add_argument("--reads", type=int, default=8)
    args = parser.parse_args()
    if min(args.pools, args.seeds, args.sweeps, args.reads) < 1:
        parser.error("Pool count, seed count, sweeps and reads must be positive")
    output = args.output or Path("results/exact_slack" if args.exact_slack_only else "results/payload_ablation")
    run(output, args.pools, args.seeds, args.sweeps, args.reads, exact_slack_only=args.exact_slack_only)
