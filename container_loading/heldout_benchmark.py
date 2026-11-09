"""Compare randomized First-Fit and hybrid search on a frozen held-out set."""

import argparse
import csv
from dataclasses import asdict
import json
from math import prod
from pathlib import Path
from platform import machine, python_version, system
from random import Random
from statistics import mean
from time import perf_counter

from baseline import baseline_report, multistart_report, packing_report
from feasibility import Container, Instance, Package, Placement, validate_packing
from hybrid import solve


PROTOCOL = Path(__file__).resolve().parent / "data" / "heldout_protocol.json"


def generate_case(family: str, count: int, seed: int):
    rng = Random(seed)
    if family == "geometry":
        regions = [((0, 0, 0), (12, 10, 8))]
        while len(regions) < count:
            index = rng.choice([i for i, (_, dimensions) in enumerate(regions) if max(dimensions) > 1])
            position, dimensions = regions.pop(index)
            axis = rng.choice([i for i, size in enumerate(dimensions) if size > 1])
            split = rng.randrange(1, dimensions[axis])
            left, right, offset = list(dimensions), list(dimensions), list(position)
            left[axis] = split
            right[axis] -= split
            offset[axis] += split
            regions.extend(((position, tuple(left)), (tuple(offset), tuple(right))))
        rng.shuffle(regions)
        packages = tuple(
            Package(f"B{i:02}", tuple(v * 100 for v in dimensions), 1000, rng.random() < .75)
            for i, (_, dimensions) in enumerate(regions)
        )
        instance = Instance(Container((1200, 1000, 800), count * 1000), packages)
        witness = tuple(
            Placement(package.id, tuple(v * 100 for v in position), package.dimensions)
            for package, (position, _) in zip(packages, regions)
        )
        return instance, witness

    bounds = (1200, 1000, 800)
    if family == "payload":
        packages = tuple(
            Package(f"B{i:02}", tuple(rng.randint(2, 4) * 100 for _ in bounds),
                    rng.randint(1, 21) * 1000, True)
            for i in range(count)
        )
        fraction = .45
    elif family == "mixed":
        # Screen only by total offered volume, before either solver runs.
        while True:
            packages = tuple(
                Package(f"B{i:02}", tuple(rng.randint(3, 6) * 100 for _ in bounds),
                        rng.randint(3, 16) * 1000, rng.random() < .55)
                for i in range(count)
            )
            if 1.05 <= sum(prod(p.dimensions) for p in packages) / prod(bounds) <= 1.65:
                break
        fraction = .72
    else:
        raise ValueError(f"Unknown family: {family}")
    payload = int(sum(p.weight for p in packages) * fraction)
    return Instance(Container(bounds, payload), packages), ()


def hybrid_report(instance, seconds, seed, settings, *, require_support, support_during_search=False, max_attempts=None):
    started = perf_counter()
    deadline = started + seconds
    best = packing_report(instance, (), started, require_support)
    rng = Random(seed)
    attempts = 0
    upper_bound = min(prod(instance.container.dimensions), sum(prod(p.dimensions) for p in instance.packages))
    while perf_counter() < deadline and (max_attempts is None or attempts < max_attempts):
        report = solve(instance, seed=seed, pool_seed=rng.getrandbits(32), anneal_seed=rng.getrandbits(32),
                       exact_slack=True, require_support=require_support,
                       support_during_search=support_during_search, **settings)
        finished = perf_counter()
        if finished > deadline:
            break
        attempts += 1
        if report["valid"] and report["metrics"]["packed_volume"] > best["metrics"]["packed_volume"]:
            best = {**report, "runtime_seconds": finished - started}
        if best["metrics"]["packed_volume"] == upper_bound:
            break
    return {**best, "completed_attempts": attempts, "elapsed_seconds": perf_counter() - started}


def summarize(rows, rng, draws):
    differences = [row["paired_difference_pp"] for row in rows]
    samples = sorted(mean(rng.choices(differences, k=len(differences))) for _ in range(draws))
    wins = sum(value > 1e-9 for value in differences)
    losses = sum(value < -1e-9 for value in differences)
    return {
        "instances": len(rows), "wins": wins, "ties": len(rows) - wins - losses, "losses": losses,
        "mean_difference_pp": mean(differences),
        "bootstrap_95_interval_pp": [samples[int(.025 * draws)], samples[int(.975 * draws)]],
        "first_fit_mean": mean(row["first_fit_mean"] for row in rows),
        "hybrid_mean": mean(row["hybrid_mean"] for row in rows),
    }


def run(output: Path, *, support_search: bool = False):
    protocol = json.loads(PROTOCOL.read_text())
    output.mkdir(parents=True, exist_ok=True)
    rng = Random(protocol["bootstrap_seed"])
    rows, cases = [], []
    seconds = protocol["budget_seconds_per_method"]
    modes = ("support_during_search",) if support_search else ("brief", "full_support")
    for family, seeds in protocol["generator_seeds"].items():
        for count, seed in zip(protocol["counts"], seeds, strict=True):
            instance, witness = generate_case(family, count, seed)
            if witness:
                result = validate_packing(instance, witness, require_support=True)
                if not result.valid or result.metrics.utilization != 1:
                    raise RuntimeError(f"Invalid optimum witness for {family}/{seed}")
            case = {"family": family, "seed": seed, "instance": asdict(instance),
                    "optimum_witness": [asdict(p) for p in witness], "modes": {}}
            for mode in modes:
                support = mode != "brief"
                baseline = baseline_report(instance, require_support=support)
                trials = []
                for index, trial_seed in enumerate(protocol["trial_seeds"]):
                    methods = {
                        "first_fit": lambda: multistart_report(instance, seconds, trial_seed, require_support=support),
                        "hybrid": lambda: hybrid_report(instance, seconds, trial_seed, protocol["hybrid"],
                                                        require_support=support, support_during_search=support_search),
                    }
                    order = tuple(methods)
                    if (seed + index) % 2:
                        order = order[::-1]
                    trial = {name: methods[name]() for name in order}
                    if not all(report["valid"] and report["runtime_seconds"] <= seconds
                               and report["completed_attempts"] for report in trial.values()):
                        raise RuntimeError(f"No validated result before deadline for {family}/{seed}/{mode}")
                    trials.append({"seed": trial_seed, **trial})
                first_fit = mean(trial["first_fit"]["metrics"]["utilization"] for trial in trials)
                hybrid = mean(trial["hybrid"]["metrics"]["utilization"] for trial in trials)
                rows.append({
                    "family": family, "generator_seed": seed, "packages": count, "mode": mode,
                    "deterministic_first_fit": baseline["metrics"]["utilization"],
                    "first_fit_mean": first_fit, "hybrid_mean": hybrid,
                    "paired_difference_pp": (hybrid - first_fit) * 100,
                })
                case["modes"][mode] = {"deterministic": baseline, "trials": trials}
            cases.append(case)
            print(f"{family} {seed} complete", flush=True)

    summaries = {
        mode: {
            family: summarize([row for row in rows if row["mode"] == mode
                               and (family == "all" or row["family"] == family)],
                              rng, protocol["bootstrap_draws"])
            for family in ("all", *protocol["generator_seeds"])
        }
        for mode in modes
    }
    (output / "heldout.json").write_text(json.dumps({
        "protocol": protocol, "environment": {"system": system(), "machine": machine(),
                                                "python": python_version()},
        "summaries": summaries, "cases": cases
    }, indent=2) + "\n", encoding="utf-8")
    with (output / "instances.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--support-search", action="store_true")
    args = parser.parse_args()
    output = args.output or Path("results/support_search" if args.support_search else "results/heldout")
    run(output, support_search=args.support_search)
