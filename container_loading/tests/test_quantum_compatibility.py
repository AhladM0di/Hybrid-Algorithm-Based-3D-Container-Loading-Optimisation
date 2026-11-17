"""Optional quantum regression tests; all execution is local, without accounts."""

from importlib.util import find_spec
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from hardware_fixtures import decode_bitstring, fixtures, ideal_reference, mapping_circuit, qaoa_circuit
from qpu_benchmark import evaluate


@unittest.skipUnless(find_spec("qiskit") and find_spec("qiskit_ibm_runtime"),
                     "Install requirements-hardware.txt for local quantum tests")
class QuantumCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(
            (Path(__file__).resolve().parents[1] / "data/hardware_reference.json").read_text()
        )
        cls.cases = fixtures()

    def test_full_ideal_reference_matches_frozen_experiment(self):
        actual = ideal_reference()
        self.assertEqual(actual.keys(), self.reference.keys())
        for name, expected in self.reference.items():
            with self.subTest(fixture=name):
                record = json.loads(json.dumps(actual[name]))
                for key in ("gamma", "beta", "ideal_optimum_probability"):
                    if key in expected:
                        self.assertAlmostEqual(record.pop(key), expected[key], delta=1e-12)
                self.assertEqual(record, {k: v for k, v in expected.items()
                                          if k not in ("gamma", "beta", "ideal_optimum_probability")})

    def test_transpilation_preserves_logical_probabilities(self):
        import numpy as np
        from qiskit.providers.fake_provider import GenericBackendV2
        from qiskit.quantum_info import Statevector
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

        for name, fixture in self.cases.items():
            with self.subTest(fixture=name):
                angles = self.reference[name]
                circuit = qaoa_circuit(fixture.qubo, angles["gamma"], angles["beta"])
                n = circuit.num_qubits
                edges = [(i, i + 1) for i in range(n - 1)]
                backend = GenericBackendV2(n, basis_gates=["rz", "sx", "x", "cx"],
                                           coupling_map=edges, seed=0, noise_info=False)
                manager = generate_preset_pass_manager(
                    backend=backend, optimization_level=2, seed_transpiler=0
                )
                compiled = manager.run(circuit)
                logical = Statevector.from_instruction(compiled).probabilities(
                    qargs=compiled.layout.final_index_layout()
                )
                np.testing.assert_allclose(logical, Statevector.from_instruction(circuit).probabilities(),
                                           atol=1e-10, rtol=1e-8)

    def test_runtime_sampler_local_counts_and_evaluation(self):
        from qiskit.providers.fake_provider import GenericBackendV2
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import SamplerV2

        # Explicit local backend; fail if this test ever tries to construct a cloud service.
        with patch("qiskit_ibm_runtime.QiskitRuntimeService", side_effect=AssertionError("Cloud disabled")):
            backend = GenericBackendV2(12, seed=0, noise_info=False)
            backend.set_options(seed_simulator=0)
            sampler = SamplerV2(mode=backend)
            manager = generate_preset_pass_manager(
                backend=backend, optimization_level=2, seed_transpiler=0
            )
            circuits = [mapping_circuit()]
            for name, fixture in self.cases.items():
                angles = self.reference[name]
                circuit = qaoa_circuit(fixture.qubo, angles["gamma"], angles["beta"])
                circuit.measure_all()
                circuits.append(circuit)
            result = sampler.run([manager.run(c) for c in circuits], shots=1024).result()
            self.assertEqual(len(result), 4)
            self.assertEqual(result[0].data.meas.get_counts(), {"01": 1024})
            for (name, fixture), pub in zip(self.cases.items(), result[1:], strict=True):
                with self.subTest(fixture=name):
                    counts = pub.data.meas.get_counts()
                    self.assertEqual(sum(counts.values()), 1024)
                    self.assertTrue(all(len(bits) == len(fixture.candidates) for bits in counts))
                    metrics = evaluate(fixture, self.reference[name],
                                       {decode_bitstring(k): v for k, v in counts.items()})
                    self.assertGreaterEqual(metrics["energy_gap"], 0)
                    self.assertGreaterEqual(metrics["feasible_volume_gap_mm3"], 0)
                    self.assertTrue(0 <= metrics["raw_feasibility_rate"] <= 1)


if __name__ == "__main__":
    unittest.main()
