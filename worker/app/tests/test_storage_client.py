from uuid import uuid4

import pytest

from shared.python.storage_paths import artifact_path
from app.services.storage_client import WorkerStorage


def test_worker_storage_round_trips_shared_artifact_path(tmp_path) -> None:
    storage = WorkerStorage(str(tmp_path))
    relative_path = artifact_path("originals", uuid4(), "png")
    content = b"normalized image bytes"

    assert storage.write_bytes(relative_path, content) == relative_path
    assert storage.read_bytes(relative_path) == content


def test_worker_storage_rejects_paths_outside_root(tmp_path) -> None:
    storage = WorkerStorage(str(tmp_path))

    with pytest.raises(ValueError, match="escapes configured root"):
        storage.write_bytes("../outside/artifact.png", b"unsafe")
