"""Load a dataset and validate a proposed packing from JSON."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from feasibility import Container, Instance, Package, Placement, validate_packing


def load_instance(path: Path) -> Instance:
    data = json.loads(path.read_text(encoding="utf-8"))
    container = data["container"]
    return Instance(
        Container(tuple(container["dimensions"]), container["max_payload"]),
        tuple(
            Package(
                record["id"], tuple(record["dimensions"]), record["weight"], record["allow_rotation"]
            )
            for record in data["packages"]
        ),
    )


def load_placements(path: Path) -> tuple[Placement, ...]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        Placement(record["package_id"], tuple(record["position"]), tuple(record["dimensions"]))
        for record in records
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("packing", type=Path)
    parser.add_argument("--require-support", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_packing(load_instance(args.dataset), load_placements(args.packing),
                                  require_support=args.require_support)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps({"valid": result.valid, **asdict(result)}, indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
