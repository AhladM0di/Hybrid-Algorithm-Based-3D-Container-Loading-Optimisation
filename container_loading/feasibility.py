"""Axis-aligned packing models and shared feasibility checks."""

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations, permutations
from math import prod

Vector = tuple[int, int, int]


def _check_vector(values: Vector, minimum: int) -> None:
    if len(values) != 3 or any(type(value) is not int or value < minimum for value in values):
        raise ValueError(f"Expected three integers greater than or equal to {minimum}")


def _check_weight(value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError("Expected a nonnegative integer weight in grams")


@dataclass(frozen=True)
class Container:
    dimensions: Vector
    max_payload: int

    def __post_init__(self) -> None:
        _check_vector(self.dimensions, 1)
        _check_weight(self.max_payload)


@dataclass(frozen=True)
class Package:
    id: str
    dimensions: Vector
    weight: int
    allow_rotation: bool

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Package ID must be a nonempty string")
        _check_vector(self.dimensions, 1)
        _check_weight(self.weight)
        if type(self.allow_rotation) is not bool:
            raise ValueError("allow_rotation must be a boolean")

    @property
    def orientations(self) -> tuple[Vector, ...]:
        if self.allow_rotation:
            return tuple(dict.fromkeys(permutations(self.dimensions)))
        return (self.dimensions,)


@dataclass(frozen=True)
class Instance:
    container: Container
    packages: tuple[Package, ...]

    def __post_init__(self) -> None:
        if len({package.id for package in self.packages}) != len(self.packages):
            raise ValueError("Dataset contains duplicate package IDs")


@dataclass(frozen=True)
class Placement:
    package_id: str
    position: Vector
    dimensions: Vector

    def __post_init__(self) -> None:
        _check_vector(self.dimensions, 1)
        if len(self.position) != 3 or any(type(value) is not int for value in self.position):
            raise ValueError("Expected three integer position coordinates")

    @property
    def end(self) -> Vector:
        x, y, z = self.position
        length, width, height = self.dimensions
        return x + length, y + width, z + height


@dataclass(frozen=True)
class PackingMetrics:
    packed_count: int
    packed_volume: int
    utilization: float
    total_weight: int


@dataclass(frozen=True)
class ValidationResult:
    violations: tuple[str, ...]
    metrics: PackingMetrics | None

    @property
    def valid(self) -> bool:
        return not self.violations


def overlaps(first: Placement, second: Placement) -> bool:
    """Only a positive-length intersection on all three axes is an overlap."""
    return all(
        max(first_start, second_start) < min(first_end, second_end)
        for first_start, second_start, first_end, second_end in zip(
            first.position, second.position, first.end, second.end
        )
    )


def supported_area(placement: Placement, others: Iterable[Placement]) -> int:
    """Area touching the floor or the tops of non-overlapping boxes below."""
    x, y, z = placement.position
    end_x, end_y, _ = placement.end
    if z == 0:
        return placement.dimensions[0] * placement.dimensions[1]
    area = 0
    for below in others:
        bx, by, _ = below.position
        right, back, top = below.end
        if top == z:
            area += max(0, min(end_x, right) - max(x, bx)) * max(0, min(end_y, back) - max(y, by))
    return area


def fully_supported(placement: Placement, others: Iterable[Placement]) -> bool:
    return supported_area(placement, others) == placement.dimensions[0] * placement.dimensions[1]


def validate_packing(instance: Instance, placements: tuple[Placement, ...], *,
                     require_support: bool = False) -> ValidationResult:
    packages = {package.id: package for package in instance.packages}
    seen = set()
    violations = []
    total_weight = packed_volume = 0

    for placement in placements:
        package_id = placement.package_id
        if package_id in seen:
            violations.append(f"Duplicate package ID: {package_id}")
        seen.add(package_id)

        package = packages.get(package_id)
        if package is None:
            violations.append(f"Unknown package ID: {package_id}")
        else:
            if placement.dimensions not in package.orientations:
                violations.append(f"Forbidden orientation: {package_id}")
            total_weight += package.weight
            packed_volume += prod(package.dimensions)

        if any(
            start < 0 or end > limit
            for start, end, limit in zip(
                placement.position, placement.end, instance.container.dimensions
            )
        ):
            violations.append(f"Out of bounds: {package_id}")

    for first, second in combinations(placements, 2):
        if overlaps(first, second):
            violations.append(f"Overlap: {first.package_id} and {second.package_id}")

    if total_weight > instance.container.max_payload:
        violations.append(f"Over payload limit: {total_weight} g")

    if require_support and not violations:
        for placement in placements:
            if not fully_supported(placement, placements):
                violations.append(f"Insufficient base support: {placement.package_id}")

    if violations:
        return ValidationResult(tuple(violations), None)

    return ValidationResult(
        (),
        PackingMetrics(
            len(seen),
            packed_volume,
            packed_volume / prod(instance.container.dimensions),
            total_weight,
        ),
    )
