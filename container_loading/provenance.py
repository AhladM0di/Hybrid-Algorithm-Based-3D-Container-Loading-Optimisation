"""Record the environment and source fingerprints for a benchmark run."""

from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
import sys


def environment():
    packages = {}
    for name in ("matplotlib", "scipy", "dwave-neal"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    root = Path(__file__).resolve().parent
    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "packages": packages,
        "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest()
                          for p in sorted(root.glob("*.py"))},
    }
