"""Benchmark both methods and save comparable 3D packing views."""

import argparse
import csv
from itertools import cycle, product
import json
from pathlib import Path
from statistics import mean, stdev

from math import prod

from baseline import baseline_report
from check_packing import load_instance, load_placements
from feasibility import validate_packing
from hybrid import solve
from reference_solver import compare_pool


def support_fractions(placements):
    """Measure the bottom-face area touching the floor or boxes directly beneath it."""
    fractions = {}
    for box in placements:
        x, y, z = box["position"]
        length, width, _ = box["dimensions"]
        supported = 0
        for below in placements:
            bx, by, bz = below["position"]
            bl, bw, bh = below["dimensions"]
            if bz + bh == z:
                dx = max(0, min(x + length, bx + bl) - max(x, bx))
                dy = max(0, min(y + width, by + bw) - max(y, by))
                supported += dx * dy
        fractions[box["package_id"]] = 1.0 if z == 0 else supported / (length * width)
    return fractions


def plot_comparison(path, instance, baseline, hybrid):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    dimensions = instance.container.dimensions
    colors = dict(zip(sorted(package.id for package in instance.packages), cycle(plt.get_cmap("tab20").colors)))
    figure = plt.figure(figsize=(13, 9), layout="constrained")
    for index, (name, report) in enumerate((("Classical baseline", baseline), ("Best hybrid", hybrid)), 1):
        axis = figure.add_subplot(2, 2, index, projection="3d")
        for endpoints in product((0, 1), repeat=3):
            start = [value * bound for value, bound in zip(endpoints, dimensions)]
            for direction, endpoint in enumerate(endpoints):
                if endpoint == 0:
                    end = start.copy()
                    end[direction] = dimensions[direction]
                    axis.plot(*zip(start, end), color="0.35", linewidth=0.7)
        for placement in report["placements"]:
            x, y, z = placement["position"]
            length, width, height = placement["dimensions"]
            label = placement["package_id"]
            axis.bar3d(x, y, z, length, width, height, color=colors[label], alpha=0.45,
                       edgecolor="0.3", linewidth=0.4)
            axis.text(x + length / 2, y + width / 2, z + height, label,
                      ha="center", va="bottom", fontsize=7, zorder=20)
        axis.set(xlim=(0, dimensions[0]), ylim=(0, dimensions[1]), zlim=(0, dimensions[2]),
                 xlabel="Length (mm)", ylabel="Width (mm)", zlabel="Height (mm)")
        axis.set_box_aspect(dimensions)
        metrics = report["metrics"]
        axis.set_title(f'{name} · {metrics["utilization"]:.2%} · {metrics["packed_count"]} packages')
        section = figure.add_subplot(2, 2, index + 2)
        section_height = dimensions[2] / 2
        section.set_facecolor("#dceffa")
        for box in report["placements"]:
            x, y, z = box["position"]
            length, width, height = box["dimensions"]
            if z <= section_height < z + height:
                section.add_patch(Rectangle((x, y), length, width, facecolor=colors[box["package_id"]],
                                            edgecolor="0.3", alpha=0.75))
                section.text(x + length / 2, y + width / 2, box["package_id"],
                             ha="center", va="center", fontsize=7)
        section.set(xlim=(0, dimensions[0]), ylim=(0, dimensions[1]), aspect="equal",
                    xlabel="Length (mm)", ylabel="Width (mm)",
                    title=f"Slice at z = {section_height:g} mm · pale blue is free space")
    figure.savefig(path, dpi=180, bbox_inches="tight", pad_inches=0.25)
    plt.close(figure)


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    rows = []
    tuning_rows = []
    data = Path(__file__).resolve().parent / "data"
    names = ("packages_10", "packages_15", "packages_20", "geometry_10", "geometry_15")
    for name in names:
        instance = load_instance(data / f"{name}.json")
        witness = data / f"{name}_witness.json"
        optimum = None
        if witness.exists():
            result = validate_packing(instance, load_placements(witness))
            if not result.valid or result.metrics.utilization != 1:
                raise RuntimeError(f"Invalid full-volume witness for {name}")
            optimum = result.metrics.packed_volume

        baselines = [baseline_report(instance) for _ in range(20)]
        baseline = baselines[0]
        hybrid_runs = [solve(instance, cap=240, seed=seed, sweeps=200, reads=16) for seed in range(5)]
        for report in (*baselines, *hybrid_runs):
            if not report["valid"]:
                raise RuntimeError(f"Invalid final packing in {name}")
            metrics = report["metrics"]
            ids = {placement["package_id"] for placement in report["placements"]}
            volume = sum(prod(placement["dimensions"]) for placement in report["placements"])
            if (metrics["packed_count"] != len(ids) or metrics["packed_volume"] != volume
                    or metrics["utilization"] != volume / prod(instance.container.dimensions)):
                raise RuntimeError(f"Inconsistent metrics in {name}")
            report["support_fractions"] = support_fractions(report["placements"])

        best = max(hybrid_runs, key=lambda report: report["metrics"]["packed_volume"])
        repeated = solve(instance, cap=best["candidate_cap"], seed=best["seed"],
                         sweeps=best["sweeps"], reads=best["reads"])
        for field in ("placements", "raw_placements", "raw_energy", "metrics"):
            if repeated[field] != best[field]:
                raise RuntimeError(f"Could not reproduce {field} for {name}")
        seed_zero = hybrid_runs[0]
        reference = compare_pool(instance, seed_zero["candidate_cap"], 0, seed_zero["raw_energy"])
        results[name] = {
            "baseline": baseline, "baseline_timings": [run["runtime_seconds"] for run in baselines],
            "hybrid_runs": hybrid_runs, "best_seed": best["seed"],
            "known_full_instance_optimum_mm3": optimum, "fixed_pool_reference_seed_0": reference,
        }
        plot_comparison(output / f"packing_{name}.png", instance, baseline, best)
        for method, reports in (("baseline", baselines), ("hybrid", hybrid_runs)):
            utilizations = [report["metrics"]["utilization"] for report in reports]
            timings = [report["runtime_seconds"] for report in reports]
            rows.append({
                "case": name,
                "method": method,
                "runs": len(reports),
                "packed_count_mean": mean(report["metrics"]["packed_count"] for report in reports),
                "packed_volume_mm3_mean": mean(report["metrics"]["packed_volume"] for report in reports),
                "utilization_mean": mean(utilizations),
                "utilization_sd": stdev(utilizations),
                "utilization_min": min(utilizations),
                "utilization_best": max(utilizations),
                "runtime_seconds_mean": mean(timings),
                "runtime_seconds_sd": stdev(timings),
                "runtime_seconds_min": min(timings),
                "runtime_seconds_max": max(timings),
                "annealing_seconds_mean": mean(report.get("annealing_seconds", 0) for report in reports),
                "raw_violations": sum(len(report.get("raw_violations", ())) for report in reports),
                "repair_removals": sum(report.get("removed_by_repair", 0) for report in reports),
                "final_violations": sum(len(report["violations"]) for report in reports),
                "minimum_support_fraction": min(
                    min(report["support_fractions"].values(), default=1) for report in reports
                ),
            })
        if name in {"packages_20", "geometry_10"}:
            settings = ((120, 1.0, 200, 16), (240, 1.0, 200, 16), (320, 1.0, 200, 16),
                        (240, 1.5, 200, 16), (240, 2.0, 200, 16),
                        (240, 1.0, 400, 16), (240, 1.0, 200, 32))
            for cap, penalty, sweeps, reads in settings:
                run = solve(instance, cap=cap, seed=0, sweeps=sweeps, reads=reads,
                            penalty_factor=penalty)
                tuning_rows.append({
                    "case": name, "cap": cap, "penalty_factor": penalty, "sweeps": sweeps, "reads": reads,
                    "utilization": run["metrics"]["utilization"], "runtime_seconds": run["runtime_seconds"],
                    "raw_violations": len(run["raw_violations"]), "repair_removals": run["removed_by_repair"],
                    "raw_energy": run["raw_energy"], "final_violations": len(run["violations"]),
                })

    with (output / "tuning.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(tuning_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(tuning_rows)

    (output / "benchmark.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    with (output / "benchmark.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/revised"))
    run(parser.parse_args().output)
