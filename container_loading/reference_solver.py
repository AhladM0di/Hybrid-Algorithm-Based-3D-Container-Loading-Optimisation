"""Independent HiGHS integer-programming reference for a fixed candidate pool."""

from math import prod

from hybrid import build_qubo, generate_candidates


def _optimize(candidates, qubo, instance=None):
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    count = len(candidates)
    if count == 0:
        return {"volume": 0, "upper_bound": 0, "optimal": True, "selected": []}
    # The QUBO's penalty exceeds every reward, so no optimum selects a conflict.
    row, col, values, limits = [], [], [], []
    for index, (i, j) in enumerate(qubo.conflicts):
        row.extend((index, index))
        col.extend((i, j))
        values.extend((1, 1))
        limits.append(1)
    if instance is not None:
        weights = {package.id: package.weight for package in instance.packages}
        row.extend([len(limits)] * count)
        col.extend(range(count))
        values.extend(weights[candidate.package_id] for candidate in candidates)
        limits.append(instance.container.max_payload)
    matrix = coo_matrix((values, (row, col)), shape=(len(limits), count)).tocsc()
    scale = max(qubo.rewards)
    result = milp(
        -np.array(qubo.rewards, dtype=float) / scale,
        integrality=np.ones(count),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(matrix, -np.inf, limits),
        options={"time_limit": 4.0, "mip_rel_gap": 0},
    )
    selected = [] if result.x is None else [index for index, value in enumerate(result.x) if value > .5]
    volume = sum(qubo.rewards[index] for index in selected)
    bound = getattr(result, "mip_dual_bound", None)
    return {
        "volume": volume,
        "upper_bound": max(volume, round(-bound * scale)) if bound is not None else None,
        "optimal": result.status == 0,
        "selected": selected,
    }


def compare_pool(instance, cap, seed, raw_energy):
    candidates = generate_candidates(instance, cap, seed)
    qubo = build_qubo(candidates)
    unconstrained = _optimize(candidates, qubo)
    payload = _optimize(candidates, qubo, instance)
    if unconstrained["optimal"] and -unconstrained["volume"] > raw_energy:
        raise RuntimeError("Annealer energy beats the independent optimum")
    return {
        "seed": seed,
        "cap": cap,
        "annealer_energy": raw_energy,
        "geometry_only": unconstrained,
        "with_payload": payload,
        "container_volume": prod(instance.container.dimensions),
    }
