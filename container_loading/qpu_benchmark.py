"""Submit or resume the Stage 4 IBM Quantum hardware benchmark."""

import argparse
from collections import Counter
from math import prod
import json
from pathlib import Path
from time import perf_counter

from feasibility import validate_packing
from hardware_fixtures import decode_bitstring, fixtures, mapping_circuit, qaoa_circuit
from hybrid import annealing_reads, repair


def evaluate(fixture, reference, frequencies):
    energies = {}
    feasible = {}
    best_repaired_volume = 0
    removed = 0
    for bits, frequency in frequencies.items():
        selected = tuple(candidate for candidate, bit in zip(fixture.candidates, bits) if bit)
        energies[bits] = fixture.qubo.energy(bits)
        feasible[bits] = validate_packing(fixture.instance, selected).valid
        repaired = repair(fixture.instance, selected)
        result = validate_packing(fixture.instance, repaired)
        if not result.valid:
            raise RuntimeError(f"Invalid repaired packing for {bits}")
        best_repaired_volume = max(best_repaired_volume, result.metrics.packed_volume)
        removed += frequency * (len(selected) - len(repaired))
    total = sum(frequencies.values())
    return {
        "samples": {"".join(map(str, bits)): frequency for bits, frequency in frequencies.items()},
        "optimum_hit_rate": sum(frequencies[bits] for bits in frequencies
                                if energies[bits] == reference["exact_qubo_energy"]) / total,
        "raw_feasibility_rate": sum(frequencies[bits] for bits in frequencies if feasible[bits]) / total,
        "best_raw_energy": min(energies.values()),
        "energy_gap": min(energies.values()) - reference["exact_qubo_energy"],
        "best_repaired_volume_mm3": best_repaired_volume,
        "best_repaired_utilization": best_repaired_volume / prod(fixture.instance.container.dimensions),
        "feasible_volume_gap_mm3": reference["exact_feasible_volume"] - best_repaired_volume,
        "mean_removed_by_repair": removed / total,
    }


def run(output: Path, repetitions: int, shots: int, backend_name: str | None, timeout: int):
    from qiskit.quantum_info import Statevector
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    reference = json.loads((Path(__file__).resolve().parent / "data/hardware_reference.json").read_text())
    cases = fixtures()
    for name, fixture in cases.items():
        for key, value in json.loads(json.dumps(fixture.manifest())).items():
            if value != reference[name][key]:
                raise RuntimeError(f"{name} differs from frozen hardware reference")

    if output.exists():
        report = json.loads(output.read_text())
        if shots != report["shots"] or (backend_name and backend_name != report["backend"]):
            raise ValueError("Existing report uses different shots or backend")
        backend_name = report["backend"]
    else:
        report = {"shots": shots, "jobs": {}, "local": {}}
    service = QiskitRuntimeService()
    backend = (service.backend(backend_name) if backend_name else
               service.least_busy(operational=True, simulator=False, min_num_qubits=12))
    report["backend"] = backend.name
    sampler = SamplerV2(mode=backend)
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=2, seed_transpiler=0)

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, default=str) + "\n")
        temporary.replace(output)

    circuits = {"H0": mapping_circuit()}
    for name, fixture in cases.items():
        angles = reference[name]
        circuit = qaoa_circuit(fixture.qubo, angles["gamma"], angles["beta"])
        if name not in report["local"]:
            ideal = {
                decode_bitstring(bits): probability
                for bits, probability in Statevector.from_instruction(circuit).probabilities_dict().items()
            }
            annealing = Counter(annealing_reads(fixture.qubo, seed=0, sweeps=200, reads=shots))
            report["local"][name] = {
                "ideal": evaluate(fixture, angles, ideal),
                "annealing": evaluate(fixture, angles, annealing),
            }
        circuit.measure_all()
        circuits[name] = circuit
    save()

    def submit(label, names):
        if label in report["jobs"]:
            return
        started = perf_counter()
        isa_circuits = [pass_manager.run(circuits[name]) for name in names]
        job = sampler.run(isa_circuits, shots=shots)
        report["jobs"][label] = {
            "id": job.job_id(),
            "fixtures": names,
            "submission_seconds": perf_counter() - started,
            "circuits": {
                name: {
                    "depth": circuit.depth(),
                    "two_qubit_gates": sum(len(instruction.qubits) == 2 for instruction in circuit.data),
                }
                for name, circuit in zip(names, isa_circuits)
            },
        }
        save()
        print(f"{label} submitted to {backend.name} as {job.job_id()}", flush=True)

    def retrieve(label):
        record = report["jobs"][label]
        if "results" in record:
            return record["results"]
        job = service.job(record["id"])
        result = job.result(timeout=timeout)
        results = {}
        for name, pub_result in zip(record["fixtures"], result, strict=True):
            counts = pub_result.data.meas.get_counts()
            if sum(counts.values()) != shots:
                raise RuntimeError(f"{name} returned a different shot count")
            if name == "H0":
                expected = reference[name]["expected_register"]
                expected_count = counts.get(expected, 0)
                results[name] = {
                    "counts": counts,
                    "passed": expected_count > max(
                        (count for bits, count in counts.items() if bits != expected), default=0
                    ) and decode_bitstring(expected) == tuple(reference[name]["expected_bits"]),
                }
            else:
                decoded = {decode_bitstring(bits): count for bits, count in counts.items()}
                results[name] = evaluate(cases[name], reference[name], decoded)
        record["results"] = results
        metrics = job.metrics()
        record["job_metrics"] = {key: metrics[key] for key in ("timestamps", "usage") if key in metrics}
        save()
        print(f"{label} complete", flush=True)
        return results

    submit("mapping", ["H0"])
    if not retrieve("mapping")["H0"]["passed"]:
        raise RuntimeError("Physical H0 measurement mapping failed")

    submit("packing_0", ["H1", "H2"])
    retrieve("packing_0")
    submit("reduced_0", ["H3"])
    for repeat in range(1, repetitions):
        submit(f"packing_{repeat}", ["H1", "H2", "H3"])
    retrieve("reduced_0")
    for repeat in range(1, repetitions):
        retrieve(f"packing_{repeat}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/hardware.json"))
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--backend")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if min(args.shots, args.repetitions, args.timeout) < 1:
        parser.error("shots, repetitions and timeout must be positive")
    run(args.output, args.repetitions, args.shots, args.backend, args.timeout)
