from pathlib import PurePosixPath
from uuid import UUID


def artifact_path(category: str, artifact_id: UUID, suffix: str) -> str:
    if category not in {"originals", "masks", "cutouts", "control", "outputs", "diagnostics"}:
        raise ValueError(f"Unsupported storage category: {category}")
    if not suffix or "/" in suffix or "\\" in suffix:
        raise ValueError("Storage suffix must be a simple filename suffix")
    return str(PurePosixPath(category) / str(artifact_id) / f"artifact.{suffix.lstrip('.')}" )
