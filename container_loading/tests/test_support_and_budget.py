import unittest
from pathlib import Path

from baseline import first_fit_decreasing, multistart_report
from check_packing import load_instance
from feasibility import Container, Instance, Package, Placement, fully_supported, validate_packing
from hybrid import build_qubo, compound_anneal, exact_weight_unit, remove_unsupported, repair, solve


class SupportAndBudgetTests(unittest.TestCase):
    def test_floor_floating_partial_and_shared_support(self):
        left = Placement("L", (0, 0, 0), (1, 2, 1))
        right = Placement("R", (1, 0, 0), (1, 2, 1))
        top = Placement("T", (0, 0, 1), (2, 2, 1))
        self.assertTrue(fully_supported(left, ()))
        self.assertFalse(fully_supported(top, ()))
        self.assertFalse(fully_supported(top, (left,)))
        self.assertTrue(fully_supported(top, (left, right)))
        instance = Instance(Container((2, 2, 2), 3), tuple(
            Package(p.package_id, p.dimensions, 1, False) for p in (left, right, top)
        ))
        self.assertTrue(validate_packing(instance, (left, right, top), require_support=True).valid)
        self.assertEqual(validate_packing(instance, (left, top), require_support=True).violations,
                         ("Insufficient base support: T",))
        baseline = first_fit_decreasing(instance, require_support=True)
        self.assertTrue(validate_packing(instance, baseline, require_support=True).valid)

    def test_repair_cascades_when_bottom_is_removed(self):
        stack = (
            Placement("B", (0, 0, 0), (2, 2, 1)),
            Placement("M", (0, 0, 1), (2, 2, 1)),
            Placement("T", (0, 0, 2), (2, 2, 1)),
        )
        instance = Instance(Container((2, 2, 3), 2), tuple(
            Package(p.package_id, p.dimensions, weight, False)
            for p, weight in zip(stack, (3, 1, 1))
        ))
        repaired = repair(instance, stack)
        self.assertEqual(repaired, stack[1:])
        self.assertEqual(remove_unsupported(repaired), ())

    def test_support_aware_search_keeps_the_floor_of_a_stack(self):
        candidates = (
            Placement("floor", (0, 0, 0), (2, 1, 1)),
            Placement("top", (0, 0, 1), (2, 1, 1)),
            Placement("unsupported", (2, 0, 1), (3, 1, 1)),
        )
        bits = compound_anneal(build_qubo(candidates), seed=0, sweeps=40, reads=4,
                               support_candidates=candidates)
        self.assertEqual(bits, (1, 1, 0))

    def test_exact_slack_retains_all_fifteen_light_boxes(self):
        instance = Instance(Container((15, 1, 1), 100_000), tuple(
            Package(str(i), (1, 1, 1), 1000, False) for i in range(15)
        ))
        result = solve(instance, cap=15, seed=0, sweeps=40, reads=4, exact_slack=True)
        self.assertEqual(result["slack_weight_unit_g"], 1000)
        self.assertTrue(result["raw_valid"])
        self.assertEqual(result["metrics"]["packed_count"], 15)

    def test_exact_capacity_and_one_gram_over(self):
        package = Package("A", (1, 1, 1), 1001, False)
        placement = Placement("A", (0, 0, 0), package.dimensions)
        exact = Instance(Container((1, 1, 1), 1001), (package,))
        over = Instance(Container((1, 1, 1), 1000), (package,))
        self.assertEqual(exact_weight_unit(over), 1)
        self.assertTrue(validate_packing(exact, (placement,)).valid)
        self.assertFalse(validate_packing(over, (placement,)).valid)
        self.assertEqual(solve(exact, 1, 0, 2, 1, exact_slack=True)["metrics"]["packed_count"], 1)
        self.assertEqual(solve(over, 1, 0, 2, 1, exact_slack=True)["metrics"]["packed_count"], 0)

    def test_multistart_keeps_a_validated_result_within_budget(self):
        path = Path(__file__).resolve().parents[1] / "data" / "packages_10.json"
        instance = load_instance(path)
        report = multistart_report(instance, seconds=.2, seed=0, require_support=True)
        self.assertTrue(report["valid"])
        self.assertGreater(report["completed_attempts"], 0)
        self.assertLessEqual(report["runtime_seconds"], .2)
