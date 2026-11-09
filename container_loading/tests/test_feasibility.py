import unittest

from feasibility import Container, Instance, Package, Placement, validate_packing


class FeasibilityTests(unittest.TestCase):
    def setUp(self):
        self.cube = (2, 2, 2)
        self.packages = tuple(Package(name, self.cube, 6000, False) for name in ("A", "B"))
        self.instance = Instance(Container((4, 2, 2), 12000), self.packages)
        self.first = Placement("A", (0, 0, 0), self.cube)
        self.second = Placement("B", (2, 0, 0), self.cube)

    def test_exact_fill_face_contact_and_exact_payload(self):
        result = validate_packing(self.instance, (self.first, self.second))
        self.assertTrue(result.valid)
        self.assertEqual(result.metrics.packed_count, 2)
        self.assertEqual(result.metrics.packed_volume, 16)
        self.assertEqual(result.metrics.utilization, 1)
        self.assertEqual(result.metrics.total_weight, 12000)

    def test_positive_volume_overlap(self):
        result = validate_packing(self.instance, (self.first, Placement("B", (1, 0, 0), self.cube)))
        self.assertEqual(result.violations, ("Overlap: A and B",))
        self.assertIsNone(result.metrics)

    def test_out_of_bounds_in_both_directions(self):
        for x in (-1, 3):
            with self.subTest(x=x):
                result = validate_packing(self.instance, (Placement("B", (x, 0, 0), self.cube),))
                self.assertEqual(result.violations, ("Out of bounds: B",))

    def test_rotation_permission(self):
        container = Container((2, 3, 1), 1)
        placement = Placement("A", (0, 0, 0), (2, 3, 1))
        allowed = Instance(container, (Package("A", (3, 2, 1), 1, True),))
        forbidden = Instance(container, (Package("A", (3, 2, 1), 1, False),))
        self.assertTrue(validate_packing(allowed, (placement,)).valid)
        self.assertEqual(validate_packing(forbidden, (placement,)).violations,
                         ("Forbidden orientation: A",))

    def test_payload_limited_partial_packing(self):
        instance = Instance(Container((4, 2, 2), 10000), self.packages)
        self.assertEqual(validate_packing(instance, (self.first,)).metrics.utilization, 0.5)
        self.assertEqual(validate_packing(instance, (self.first, self.second)).violations,
                         ("Over payload limit: 12000 g",))

    def test_duplicate_placement(self):
        duplicate = Placement("A", self.second.position, self.cube)
        self.assertEqual(validate_packing(self.instance, (self.first, duplicate)).violations,
                         ("Duplicate package ID: A",))

    def test_duplicate_dataset_id(self):
        with self.assertRaisesRegex(ValueError, "duplicate package IDs"):
            Instance(self.instance.container, (self.packages[0], self.packages[0]))

    def test_unknown_package(self):
        unknown = Placement("C", self.first.position, self.cube)
        self.assertEqual(validate_packing(self.instance, (unknown,)).violations,
                         ("Unknown package ID: C",))
