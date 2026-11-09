"""Prepare small exact-solvable fixtures and depth-1 QAOA circuits for IBM QPUs."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from math import pi
from pathlib import Path

from check_packing import load_instance
from feasibility import Container, Instance, Package, Placement, validate_packing
from hybrid import Qubo, build_qubo, generate_candidates


@dataclass(frozen=True)
class Fixture:
    instance: Instance
    candidates: tuple[Placement, ...]
    qubo: Qubo


def fixtures() -> dict[str, Fixture]:
    overlap = Instance(Container((7, 1, 1), 3), (
        Package("A", (5, 1, 1), 1, False),
        Package("B", (3, 1, 1), 1, False),
        Package("C", (3, 1, 1), 1, False),
    ))
    overlap_candidates = (
        Placement("A", (1, 0, 0), (5, 1, 1)),
        Placement("B", (0, 0, 0), (3, 1, 1)),
        Placement("C", (4, 0, 0), (3, 1, 1)),
    )
    rotation = Instance(Container((4, 3, 1), 3), (
        Package("A", (2, 3, 1), 1, True),
        Package("B", (2, 3, 1), 1, False),
        Package("C", (3, 1, 1), 1, False),
    ))
    rotation_candidates = (
        Placement("A", (0, 0, 0), (2, 3, 1)),
        Placement("A", (0, 0, 0), (3, 2, 1)),
        Placement("B", (2, 0, 0), (2, 3, 1)),
        Placement("C", (0, 2, 0), (3, 1, 1)),
    )
    benchmark = load_instance(Path(__file__).resolve().parent / "data" / "packages_10.json")
    benchmark_candidates = generate_candidates(benchmark, 12)
    return {
        "H1": Fixture(overlap, overlap_candidates, build_qubo(overlap_candidates, penalty=6)),
        "H2": Fixture(rotation, rotation_candidates, build_qubo(rotation_candidates)),
        "H3": Fixture(benchmark, benchmark_candidates, build_qubo(benchmark_candidates)),
    }


def decode_bitstring(measured: str) -> tuple[int, ...]:
    """Convert a single Qiskit classical register to candidate-index order."""
    return tuple(int(bit) for bit in reversed(measured))


def mapping_circuit():
    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(2)
    circuit.x(0)
    circuit.measure_all()
    return circuit


def qaoa_circuit(qubo: Qubo, gamma: float, beta: float):
    from qiskit import QuantumCircuit

    qubits = range(len(qubo.rewards))
    circuit = QuantumCircuit(len(qubits))
    circuit.h(list(qubits))
    _, fields, couplings = qubo.ising()
    scale = qubo.penalty
    for qubit, field in enumerate(fields):
        circuit.rz(2 * gamma * field / scale, qubit)
    for i, j, coupling in couplings:
        circuit.rzz(2 * gamma * coupling / scale, i, j)
    circuit.rx(2 * beta, list(qubits))
    return circuit


def exact_reference(fixture: Fixture) -> tuple[int, int]:
    """Return minimum QUBO energy and maximum payload-feasible volume."""
    best_energy = best_volume = 0
    for bits in product((0, 1), repeat=len(fixture.candidates)):
        best_energy = min(best_energy, fixture.qubo.energy(bits))
        selected = tuple(candidate for candidate, bit in zip(fixture.candidates, bits) if bit)
        result = validate_packing(fixture.instance, selected)
        if result.metrics is not None:
            best_volume = max(best_volume, result.metrics.packed_volume)
    return best_energy, best_volume


def tune_angles(qubo: Qubo) -> tuple[float, float]:
    """Choose angles by expected energy on an ideal statevector grid."""
    from qiskit.quantum_info import Statevector

    energies: Sequence[int] = [
        qubo.energy(decode_bitstring(format(index, f"0{len(qubo.rewards)}b")))
        for index in range(2 ** len(qubo.rewards))
    ]

    def expected_energy(angles: tuple[float, float]) -> float:
        probabilities = Statevector.from_instruction(qaoa_circuit(qubo, *angles)).probabilities()
        return float(probabilities @ energies)

    grid = product(
        (step * pi / 16 for step in range(1, 25)),
        (step * pi / 16 for step in range(-8, 8)),
    )
    return min(grid, key=expected_energy)


def ideal_reference() -> dict:
    """Record the candidate order, objective, and ideal-circuit configuration."""
    from dataclasses import asdict

    from qiskit.quantum_info import Statevector

    mapping = mapping_circuit().remove_final_measurements(inplace=False)
    mapping_result = Statevector.from_instruction(mapping).probabilities_dict()
    if mapping_result != {"01": 1.0} or decode_bitstring("01") != (1, 0):
        raise RuntimeError("Ideal H0 measurement mapping failed")

    report = {"H0": {"expected_register": "01", "expected_bits": [1, 0]}}
    for name, fixture in fixtures().items():
        exact_energy, exact_volume = exact_reference(fixture)
        gamma, beta = tune_angles(fixture.qubo)
        probabilities = Statevector.from_instruction(
            qaoa_circuit(fixture.qubo, gamma, beta)
        ).probabilities_dict()
        optimum_probability = sum(
            probability for register, probability in probabilities.items()
            if fixture.qubo.energy(decode_bitstring(register)) == exact_energy
        )
        report[name] = {
            **asdict(fixture),
            "exact_qubo_energy": exact_energy,
            "exact_feasible_volume": exact_volume,
            "gamma": gamma,
            "beta": beta,
            "ideal_optimum_probability": float(optimum_probability),
        }
    return report


if __name__ == "__main__":
    import json

    print(json.dumps(ideal_reference(), indent=2))
