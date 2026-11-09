"""Run the five-trial v4 comparison at the shared scoring cutoff."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from random import Random
from statistics import mean

from baseline import baseline_report, multistart_report
from effort_benchmark import write_csv
from feasibility import Placement, validate_packing
from heldout_benchmark import PROTOCOL, generate_case, hybrid_report, summarize
from provenance import environment


def run(output: Path):
    run_environment = environment()
    protocol = json.loads(PROTOCOL.with_name("main_comparison_protocol.json").read_text())
    cases = json.loads(PROTOCOL.with_name(protocol["instances"]).read_text())
    cutoff = protocol["scoring_cutoff_seconds"]
    methods = ("first_fit", "hybrid")
    records = []
    instance_rows = []
    reference_rows = []
    for family, seeds in cases["generator_seeds"].items():
        for case, count in zip(seeds, cases["counts"], strict=True):
            instance, _ = generate_case(family, count, case)
            reference = baseline_report(instance)
            reference_rows.append({"family": family, "case": case,
                                   **reference["metrics"],
                                   "runtime_seconds": reference["runtime_seconds"],
                                   "final_violations": len(reference["violations"])})
            trials = []
            for trial_seed in protocol["trial_seeds"]:
                solvers = {
                    "first_fit": lambda: multistart_report(instance, cutoff, trial_seed, **protocol["first_fit"]),
                    "hybrid": lambda: hybrid_report(instance, cutoff, trial_seed, protocol["hybrid"],
                                                    require_support=False),
                }
                order = methods if (case + trial_seed) % 2 == 0 else methods[::-1]
                result = {method: solvers[method]() for method in order}
                for report in result.values():
                    placements = tuple(
                        Placement(p["package_id"], tuple(p["position"]), tuple(p["dimensions"]))
                        for p in report["placements"]
                    )
                    verified = validate_packing(instance, placements)
                    if (not verified.valid or not report["valid"] or report["violations"]
                            or report["runtime_seconds"] > cutoff
                            or verified.metrics.utilization != report["metrics"]["utilization"]):
                        raise RuntimeError(f"Invalid result for {case}/{trial_seed}")
                trials.append({"seed": trial_seed, **result})
            records.append({"family": family, "case": case, "count": count,
                            "instance": asdict(instance), "deterministic_reference": reference,
                            "trials": trials})
            for method in methods:
                runs = [trial[method] for trial in trials]
                scores = [r["metrics"]["utilization"] for r in runs]
                instance_rows.append({
                    "family": family, "case": case, "method": method,
                    "mean_utilization": mean(scores), "best_utilization": max(scores),
                    "best_seed": trials[scores.index(max(scores))]["seed"],
                })
            print(f"{family} {case} complete", flush=True)

    rng = Random(protocol["bootstrap_seed"])
    table = []
    intervals = []
    for family in ("all", *cases["generator_seeds"]):
        chosen = [r for r in records if family == "all" or r["family"] == family]
        by_method = {
            method: [row for row in instance_rows if row["method"] == method
                     and (family == "all" or row["family"] == family)]
            for method in methods
        }
        for method in methods:
            trials = [trial[method] for record in chosen for trial in record["trials"]]
            table.append({
                "family": family, "method": method, "cases": len(chosen), "trials": len(trials),
                "mean_utilization": mean(row["mean_utilization"] for row in by_method[method]),
                "mean_case_best_utilization": mean(row["best_utilization"] for row in by_method[method]),
                "mean_packed_count": mean(r["metrics"]["packed_count"] for r in trials),
                "mean_packed_volume_mm3": mean(r["metrics"]["packed_volume"] for r in trials),
                "mean_elapsed_ms": 1000 * mean(r["elapsed_seconds"] for r in trials),
                "max_elapsed_ms": 1000 * max(r["elapsed_seconds"] for r in trials),
                "final_violations": sum(len(r["violations"]) for r in trials),
            })
        for metric in ("mean_utilization", "best_utilization"):
            paired = [
                {"first_fit_mean": a[metric], "hybrid_mean": b[metric],
                 "paired_difference_pp": (b[metric] - a[metric]) * 100}
                for a, b in zip(by_method["first_fit"], by_method["hybrid"], strict=True)
            ]
            result = summarize(paired, rng, protocol["bootstrap_draws"])
            lower, upper = result.pop("bootstrap_95_interval_pp")
            intervals.append({"family": family, "metric": metric, **result,
                              "interval_lower_pp": lower, "interval_upper_pp": upper})

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "summary.csv", table)
    write_csv(output / "intervals.csv", intervals)
    write_csv(output / "instances.csv", instance_rows)
    write_csv(output / "deterministic_reference.csv", reference_rows)
    (output / "packings.json").write_text(json.dumps({
        "protocol": protocol, "instance_protocol": cases,
        "environment": run_environment,
        "evaluation_scope": "Reused development cases; exploratory comparison, not a fresh held-out test.",
        "cases": records,
    }, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/main_v4"))
    run(parser.parse_args().output)
