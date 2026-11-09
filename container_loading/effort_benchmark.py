"""Compare fixed work and wall-clock budgets on the existing held-out cases."""

import argparse
import csv
import json
from math import inf, prod
from pathlib import Path
from random import Random
from statistics import mean
from time import perf_counter

from baseline import knapsack_first_fit_report, multistart_report, packing_report, payload_order
from heldout_benchmark import PROTOCOL, generate_case, hybrid_report, summarize
from hybrid import build_qubo, generate_candidates
from reference_solver import _optimize


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def highs_report(instance, budget, trial_seed, cap):
    """Give HiGHS a single hybrid-equivalent pool and an end-to-end deadline."""
    started = perf_counter()
    pool_seed = Random(trial_seed).getrandbits(32)
    candidates = generate_candidates(instance, cap, pool_seed, varied_corners=True)
    qubo = build_qubo(candidates)
    remaining = budget - (perf_counter() - started)
    reserve = min(.025, budget * .2)
    reference = None
    if remaining > reserve:
        reference = _optimize(candidates, qubo, instance, time_limit=remaining - reserve)
    selected = tuple(candidates[i] for i in reference["selected"]) if reference else ()
    report = packing_report(instance, selected, started)
    finished = perf_counter()
    if not report["valid"]:
        raise RuntimeError("HiGHS incumbent failed validation")
    accepted = reference is not None and finished - started <= budget
    if not accepted:
        report = packing_report(instance, (), started)
    return {
        **report, "completed_attempts": int(accepted), "elapsed_seconds": finished - started,
        "pool_seed": pool_seed, "candidate_count": len(candidates),
        "solver_status": reference["solver_status"] if reference else None,
        "pool_upper_bound_mm3": reference["upper_bound"] if reference else None,
        "accepted": accepted,
    }


def run(output, *, fixed_only=False, followup=False):
    output.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(PROTOCOL.read_text())
    settings = protocol["hybrid"]
    trial_seeds = protocol["trial_seeds"] if followup else protocol["trial_seeds"][:1]
    if followup:
        settings = {**settings, "varied_corners": True}
        # Warm imports before any timed HiGHS call. Pool construction stays timed.
        from scipy.optimize import milp  # noqa: F401
    rows = []
    packings = []
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
                for seed in trial_seeds:
                    methods = {
                        "first_fit": lambda: multistart_report(instance, budget, seed,
                                                              weight_aware=True, max_attempts=attempts),
                        "hybrid": lambda: hybrid_report(instance, budget, seed, settings,
                                                        require_support=False, max_attempts=attempts),
                    }
                    if followup and family == "mixed" and budget != inf:
                        methods["highs"] = lambda: highs_report(instance, budget, seed, settings["cap"])
                    order = tuple(methods)
                    shift = (generator_seed + seed if followup else generator_seed) % len(order)
                    for method in (*order[shift:], *order[:shift]):
                        report = methods[method]()
                        if not report["valid"] or (not followup and not report["completed_attempts"]):
                            raise RuntimeError(f"Invalid result for {generator_seed}/{mode}/{method}")
                        row = {
                            "mode": mode, "budget_seconds": None if budget == inf else budget,
                            "attempt_limit": attempts, "family": family, "generator_seed": generator_seed,
                            "trial_seed": seed, "method": method,
                            "utilization": report["metrics"]["utilization"],
                            "completed_attempts": report["completed_attempts"],
                            "elapsed_seconds": report["elapsed_seconds"],
                        }
                        rows.append(row)
                        packings.append({**row, "report": report})
            print(f"{family} {generator_seed} complete", flush=True)
    write_csv(output / "runs.csv", rows)
    (output / "packings.json").write_text(json.dumps({
        "settings": settings, "trial_seeds": trial_seeds, "runs": packings
    }, separators=(",", ":")) + "\n", encoding="utf-8")
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
            "cases": len({r["generator_seed"] for r in group}),
            "trials": len(group), "utilization_mean": mean(r["utilization"] for r in group),
            "attempts_mean": mean(counts), "attempts_min": min(counts), "attempts_max": max(counts),
            "elapsed_seconds_mean": mean(r["elapsed_seconds"] for r in group),
        })
    write_csv(output / "summary.csv", summary)

    if followup:
        intervals = []
        rng = Random(protocol["bootstrap_seed"])
        for mode, budget, limit, family, method in groups:
            if method != "hybrid":
                continue
            key = (mode, budget, limit, family)
            hybrid = groups[(*key, "hybrid")]
            for comparator in ("first_fit", "highs"):
                if (*key, comparator) not in groups or (comparator == "highs" and family != "mixed"):
                    continue
                baseline = groups[(*key, comparator)]
                instance_rows = []
                for generator_seed in sorted({row["generator_seed"] for row in hybrid}):
                    left = mean(row["utilization"] for row in baseline if row["generator_seed"] == generator_seed)
                    right = mean(row["utilization"] for row in hybrid if row["generator_seed"] == generator_seed)
                    instance_rows.append({"first_fit_mean": left, "hybrid_mean": right,
                                          "paired_difference_pp": 100 * (right - left)})
                result = summarize(instance_rows, rng, protocol["bootstrap_draws"])
                low, high = result.pop("bootstrap_95_interval_pp")
                result["comparator_mean"] = result.pop("first_fit_mean")
                intervals.append({
                    "mode": mode, "budget_seconds": budget, "family": family, "comparator": comparator,
                    **result, "interval_lower_pp": low, "interval_upper_pp": high,
                })
        write_csv(output / "intervals.csv", intervals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--followup", action="store_true")
    parser.add_argument("--fixed-only", action="store_true")
    args = parser.parse_args()
    output = args.output or Path("results/effort_v4" if args.followup else "results/effort")
    run(output, fixed_only=args.fixed_only, followup=args.followup)
