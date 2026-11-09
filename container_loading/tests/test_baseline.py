from pathlib import Path
import unittest

from baseline import first_fit_decreasing, knapsack_first_fit_report, multistart_report
from check_packing import load_instance
from feasibility import Container, Instance, Package, Placement, validate_packing


class BaselineTests(unittest.TestCase):
    def test_knapsack_control_and_fixed_work(self):
        instance = Instance(Container((13, 1, 1), 10), (
            Package("A", (5, 1, 1), 6, False),
            Package("B", (4, 1, 1), 5, False),
            Package("C", (4, 1, 1), 5, False),
        ))
        control = knapsack_first_fit_report(instance)
        self.assertTrue(control["valid"])
        self.assertEqual(control["metrics"]["packed_volume"], 8)
        first = multistart_report(instance, float("inf"), 301, weight_aware=True, max_attempts=4)
        second = multistart_report(instance, float("inf"), 301, weight_aware=True, max_attempts=4)
        self.assertEqual(first["completed_attempts"], 4)
        self.assertEqual(first["placements"], second["placements"])

    def test_exact_fill_and_deterministic_tie_break(self):
        dimensions = (2, 2, 2)
        packages = tuple(Package(name, dimensions, 6, False) for name in ("B", "A"))
        instance = Instance(Container((4, 2, 2), 12), packages)
        expected = (
            Placement("A", (0, 0, 0), dimensions),
            Placement("B", (2, 0, 0), dimensions),
        )
        for _ in range(3):
            self.assertEqual(first_fit_decreasing(instance), expected)
        self.assertEqual(validate_packing(instance, expected).metrics.utilization, 1)

    def test_rotation_required(self):
        container = Container((2, 3, 1), 1)
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                instance = Instance(container, (Package("A", (3, 2, 1), 1, allowed),))
                placements = first_fit_decreasing(instance)
                expected = (Placement("A", (0, 0, 0), (2, 3, 1)),) if allowed else ()
                self.assertEqual(placements, expected)
                self.assertTrue(validate_packing(instance, placements).valid)

    def test_payload_limited(self):
        packages = tuple(Package(name, (2, 2, 2), 6000, False) for name in ("A", "B"))
        instance = Instance(Container((4, 2, 2), 10000), packages)
        result = validate_packing(instance, first_fit_decreasing(instance))
        self.assertTrue(result.valid)
        self.assertEqual(result.metrics.packed_count, 1)
        self.assertEqual(result.metrics.utilization, 0.5)

    def test_skips_failed_packages_and_continues(self):
        instance = Instance(Container((4, 2, 2), 10), (
            Package("oversized", (5, 2, 2), 1, True),
            Package("overweight", (4, 2, 2), 11, False),
            Package("fits", (2, 2, 2), 10, False),
        ))
        placements = first_fit_decreasing(instance)
        self.assertEqual([placement.package_id for placement in placements], ["fits"])
        self.assertTrue(validate_packing(instance, placements).valid)

    def test_ten_package_dataset(self):
        dataset = Path(__file__).resolve().parents[1] / "data" / "packages_10.json"
        instance = load_instance(dataset)
        placements = first_fit_decreasing(instance)
        self.assertEqual(first_fit_decreasing(instance), placements)
        result = validate_packing(instance, placements)
        self.assertTrue(result.valid)
        self.assertEqual(result.metrics.packed_count, 10)
