"""Package the current project with a SHA-256 inventory, excluding local caches."""

from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build():
    root = Path(__file__).resolve().parent
    output = root.parent / "container-loading-submission-v4-five-trial.zip"
    prefix = "container-loading-submission-v4"
    excluded = {"__pycache__", ".venv", ".git", ".cache", ".matplotlib"}
    files = {"README.md": root.parent / "README.md"}
    for path in sorted(root.rglob("*")):
        if (path.is_file() and not excluded.intersection(path.relative_to(root).parts)
                and path.name != ".DS_Store" and path.suffix != ".pyc"):
            files[str(Path(root.name) / path.relative_to(root))] = path
    inventory = {name: sha256(path.read_bytes()).hexdigest() for name, path in files.items()}
    temporary = output.with_suffix(".tmp")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
        for name, path in files.items():
            archive.write(path, f"{prefix}/{name}")
        archive.writestr(f"{prefix}/MANIFEST.sha256.json", json.dumps(inventory, indent=2) + "\n")
    with ZipFile(temporary) as archive:
        assert archive.testzip() is None
        for name, digest in inventory.items():
            assert sha256(archive.read(f"{prefix}/{name}")).hexdigest() == digest
    temporary.replace(output)
    print(f"Verified {len(files)} files in {output}")


if __name__ == "__main__":
    build()
