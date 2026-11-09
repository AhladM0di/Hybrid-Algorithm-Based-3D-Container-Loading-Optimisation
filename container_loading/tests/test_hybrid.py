from fractions import Fraction
from itertools import product
import unittest

from feasibility import Container, Instance, Package, Placement, validate_packing
from hardware_fixtures import decode_bitstring, exact_reference, fixtures
from hybrid import (PayloadSlack, anneal, build_qubo, compound_anneal, critical_weight_price,
                    generate_candidates, greedy_repair, repair, solve)
from reference_solver import _optimize


class HybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = fixtures()

    def test_overlap_tradeoff_and_ising_energy(self):
        qubo = self.fixtures["H1"].qubo
        energies = {bits: qubo.energy(bits) for bits in product((0, 1), repeat=3)}
        self.assertEqual([bits for bits in energies if energies[bits] == min(energies.values())],
                         [(0, 1, 1)])
        self.assertEqual(min(energies.values()), -6)

        for name, fixture in self.fixtures.items():
            with self.subTest(fixture=name):
                qubo = fixture.qubo
                offset, fields, couplings = qubo.ising()
                for bits in product((0, 1), repeat=len(fields)):
                    z = tuple(1 - 2 * bit for bit in bits)
                    energy = offset + sum(field * value for field, value in zip(fields, z))
                    energy += sum(coupling * z[i] * z[j] for i, j, coupling in couplings)
                    self.assertEqual(energy, qubo.energy(bits))

    def test_duplicate_and_rotation_fixture(self):
        fixture = self.fixtures["H2"]
        qubo = fixture.qubo
        self.assertIn((0, 1), qubo.conflicts)
        self.assertEqual(exact_reference(fixture), (-12, 12))
        self.assertEqual([bits for bits in product((0, 1), repeat=4) if qubo.energy(bits) == -12],
                         [(1, 0, 1, 0)])

    def test_candidates_are_capped_and_individually_feasible(self):
        instance = self.fixtures["H3"].instance
        candidates = generate_candidates(instance, 24, seed=2)
        self.assertEqual(len(candidates), 24)
        self.assertEqual(candidates, generate_candidates(instance, 24, seed=2))
        self.assertNotEqual(candidates, generate_candidates(instance, 24, seed=3))
        self.assertEqual(len(set(candidates)), len(candidates))
        self.assertTrue(all(validate_packing(instance, (candidate,)).valid for candidate in candidates))
        with self.assertRaisesRegex(ValueError, "positive"):
            generate_candidates(instance, 0)

    def test_repair_removes_duplicate_overlap_and_overweight(self):
        dimensions = (2, 2, 2)
        instance = Instance(Container((8, 2, 2), 10), (
            Package("A", dimensions, 6, False),
            Package("B", dimensions, 4, False),
            Package("C", dimensions, 6, False),
        ))
        first = Placement("A", (0, 0, 0), dimensions)
        self.assertEqual(repair(instance, (first, Placement("A", (2, 0, 0), dimensions))), (first,))
        self.assertEqual(repair(instance, (first, Placement("B", (1, 0, 0), dimensions))), (first,))
        self.assertEqual(repair(instance, (first, Placement("C", (2, 0, 0), dimensions))), (first,))

    def test_independent_reference_with_payload(self):
        dimensions = (2, 2, 2)
        instance = Instance(Container((4, 2, 2), 10), (
            Package("A", dimensions, 6, False),
            Package("B", dimensions, 6, False),
        ))
        candidates = (
            Placement("A", (0, 0, 0), dimensions),
            Placement("B", (2, 0, 0), dimensions),
        )
        qubo = build_qubo(candidates)
        geometry_only = _optimize(candidates, qubo)
        payload_aware = _optimize(candidates, qubo, instance)
        self.assertTrue(geometry_only["optimal"])
        self.assertTrue(payload_aware["optimal"])
        self.assertEqual(geometry_only["volume"], 16)
        self.assertEqual(payload_aware["volume"], 8)

    def test_exact_payload_repair_beats_largest_first(self):
        packages = (
            Package("A", (5, 1, 1), 6, False),
            Package("B", (4, 1, 1), 5, False),
            Package("C", (4, 1, 1), 5, False),
        )
        instance = Instance(Container((13, 1, 1), 10), packages)
        placements = tuple(
            Placement(package.id, (x, 0, 0), package.dimensions)
            for x, package in zip((0, 5, 9), packages)
        )
        self.assertEqual(greedy_repair(instance, placements), placements[:1])
        self.assertEqual(repair(instance, placements), placements[1:])
        self.assertEqual(critical_weight_price(instance), Fraction(4, 5))

    def test_compound_search_and_pairwise_ising(self):
        fixture = self.fixtures["H1"]
        qubo = build_qubo(fixture.candidates, pairwise=True)
        self.assertEqual(qubo.pair_penalties, (4, 4))
        self.assertEqual(compound_anneal(qubo, 0, 40, 4), (0, 1, 1))
        offset, fields, couplings = qubo.ising()
        for bits in product((0, 1), repeat=3):
            z = [1 - 2 * bit for bit in bits]
            self.assertEqual(
                qubo.energy(bits),
                offset + sum(field * value for field, value in zip(fields, z))
                + sum(coupling * z[i] * z[j] for i, j, coupling in couplings),
            )

    def test_slack_residual_matches_binary_minimum(self):
        payload = PayloadSlack((2, 3), 4, 7)
        self.assertEqual(payload.bits, 3)
        for used in range(8):
            explicit = min(7 * (used + slack - 4) ** 2 for slack in range(2 ** payload.bits))
            self.assertEqual(payload.energy(used), explicit)

    def test_seeded_solver_and_measurement_order(self):
        self.assertEqual(decode_bitstring("01"), (1, 0))
        fixture = self.fixtures["H1"]
        self.assertEqual(anneal(fixture.qubo, seed=2, sweeps=100, reads=8), (0, 1, 1))
        instance = self.fixtures["H3"].instance
        first = solve(instance, cap=24, seed=2, sweeps=50, reads=4)
        second = solve(instance, cap=24, seed=2, sweeps=50, reads=4)
        self.assertTrue(first["valid"])
        self.assertEqual(first["placements"], second["placements"])
        self.assertEqual(first["raw_energy"], second["raw_energy"])
