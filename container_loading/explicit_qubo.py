"""Expand the payload slack expression for an independent binary sampler."""

import argparse
import csv
import json
from pathlib import Path

from feasibility import Container, Instance, Package, validate_packing
from hybrid import PayloadSlack, build_qubo, exact_weight_unit, generate_candidates, repair


def expand(qubo, payload: PayloadSlack):
    """Return upper-triangular QUBO coefficients and the constant offset."""
    weights = (*payload.weights, *(1 << i for i in range(payload.bits)))
    coefficients = {}
    for i, weight in enumerate(weights):
        reward = qubo.rewards[i] if i < len(qubo.rewards) else 0
        coefficients[i, i] = payload.penalty * weight * (weight - 2 * payload.capacity) - reward
        for j in range(i + 1, len(weights)):
            coefficients[i, j] = 2 * payload.penalty * weight * weights[j]
    for i, j, penalty in qubo.couplings:
        coefficients[i, j] += penalty
    return coefficients, payload.penalty * payload.capacity**2


def run(output: Path):
    import neal

    data = json.loads(Path("results/heldout/heldout.json").read_text())
    rows = []
    for case in data["cases"]:
        if case["seed"] not in (4200, 4201, 4202, 4300, 4301, 4302):
            continue
        record = case["instance"]
        c = record["container"]
        instance = Instance(
            Container(tuple(c["dimensions"]), c["max_payload"]),
            tuple(Package(p["id"], tuple(p["dimensions"]), p["weight"], p["allow_rotation"])
                  for p in record["packages"]),
        )
        trial = case["modes"]["brief"]["trials"][0]["hybrid"]
        candidates = generate_candidates(instance, trial["candidate_cap"], trial["pool_seed"])
        qubo = build_qubo(candidates)
        unit = exact_weight_unit(instance)
        weights = {p.id: p.weight for p in instance.packages}
        payload = PayloadSlack(tuple(weights[p.package_id] // unit for p in candidates),
                               instance.container.max_payload // unit, qubo.penalty)
        coefficients, _ = expand(qubo, payload)
        scale = max(abs(v) for v in coefficients.values())
        samples = neal.SimulatedAnnealingSampler().sample_qubo(
            {key: value / scale for key, value in coefficients.items()},
            seed=301, num_reads=32, num_sweeps=500,
        )
        best_volume = 0
        raw_valid = 0
        for sample in samples:
            raw = tuple(p for i, p in enumerate(candidates) if sample[i])
            raw_valid += validate_packing(instance, raw).valid
            result = validate_packing(instance, repair(instance, raw))
            if not result.valid:
                raise RuntimeError("Explicit-QUBO sample repair failed")
            best_volume = max(best_volume, result.metrics.utilization)
        rows.append({
            "case": case["seed"], "family": case["family"], "pool_seed": trial["pool_seed"],
            "placement_bits": len(candidates), "slack_bits": payload.bits, "weight_unit_g": unit,
            "reads": 32, "sweeps": 500, "raw_valid_reads": raw_valid,
            "neal_best_after_repair": best_volume, "recorded_compound": trial["metrics"]["utilization"],
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/effort/explicit_qubo.csv"))
    run(parser.parse_args().output)
