"""Benchmark both methods and save comparable 3D packing views."""

import argparse
import csv
from itertools import product
import json
from pathlib import Path
from statistics import mean

from math import prod

from baseline import baseline_report
from check_packing import load_instance
from hybrid import solve


def plot_comparison(path, instance, baseline, hybrid):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dimensions = instance.container.dimensions
    colors = dict(zip(sorted(package.id for package in instance.packages), plt.get_cmap("tab20").colors))
    figure = plt.figure(figsize=(13, 5.5), layout="constrained")
    for index, (name, report) in enumerate((("Classical baseline", baseline), ("Best hybrid", hybrid)), 1):
        axis = figure.add_subplot(1, 2, index, projection="3d")
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
    figure.savefig(path, dpi=180, bbox_inches="tight", pad_inches=0.25)
    plt.close(figure)


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    rows = []
    for count in (10, 15, 20):
        instance = load_instance(Path(__file__).resolve().parent / "data" / f"packages_{count}.json")
        baseline = baseline_report(instance)
        hybrid_runs = [solve(instance, cap=100, seed=seed, sweeps=200, reads=16) for seed in range(5)]
        if not all(report["valid"] for report in (baseline, *hybrid_runs)):
            raise RuntimeError(f"Invalid final packing in {count}-package case")
        for report in (baseline, *hybrid_runs):
            metrics = report["metrics"]
            ids = {placement["package_id"] for placement in report["placements"]}
            volume = sum(prod(placement["dimensions"]) for placement in report["placements"])
            if (metrics["packed_count"] != len(ids) or metrics["packed_volume"] != volume
                    or metrics["utilization"] != volume / prod(instance.container.dimensions)):
                raise RuntimeError(f"Inconsistent metrics in {count}-package case")
        best = max(hybrid_runs, key=lambda report: report["metrics"]["packed_volume"])
        repeated = solve(instance, cap=best["candidate_cap"], seed=best["seed"],
                         sweeps=best["sweeps"], reads=best["reads"])
        for field in ("placements", "raw_placements", "raw_energy", "metrics"):
            if repeated[field] != best[field]:
                raise RuntimeError(f"Could not reproduce {field} for {count}-package case")

        results[count] = {"baseline": baseline, "hybrid_runs": hybrid_runs, "best_seed": best["seed"]}
        plot_comparison(output / f"packing_{count}.png", instance, baseline, best)
        for method, reports in (("baseline", [baseline]), ("hybrid_mean", hybrid_runs), ("hybrid_best", [best])):
            rows.append({
                "packages": count,
                "method": method,
                "packed_count": mean(report["metrics"]["packed_count"] for report in reports),
                "packed_volume_mm3": mean(report["metrics"]["packed_volume"] for report in reports),
                "utilization": mean(report["metrics"]["utilization"] for report in reports),
                "runtime_seconds": mean(report["runtime_seconds"] for report in reports),
                "annealing_seconds": mean(report.get("annealing_seconds", 0) for report in reports),
                "final_violations": sum(len(report["violations"]) for report in reports),
            })

    (output / "benchmark.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    with (output / "benchmark.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"))
    run(parser.parse_args().output)
