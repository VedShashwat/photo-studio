from contextlib import nullcontext
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from PIL import Image

from shared.python.storage_paths import artifact_path
from app.pipelines.background_removal import (
    BackgroundRemovalProcessor,
    BiRefNetAdapter,
    create_cutout,
    refine_mask,
)
from app.services.db_client import ClaimedJob
from app.services.storage_client import WorkerStorage


def test_refine_mask_returns_metrics_and_feathered_mask() -> None:
    mask = Image.new("L", (100, 80), 0)
    for x in range(20, 80):
        for y in range(15, 65):
            mask.putpixel((x, y), 255)
    refined, metrics = refine_mask(mask)
    assert refined.size == mask.size
    assert 0.02 < metrics.coverage < 0.95
    assert metrics.bbox is not None


def test_create_cutout_preserves_rgb_and_adds_alpha() -> None:
    image = Image.new("RGB", (4, 4), "red")
    mask = Image.new("L", (4, 4), 255)
    cutout = create_cutout(image, mask)
    assert cutout.mode == "RGBA"
    assert cutout.getpixel((0, 0)) == (255, 0, 0, 255)


class FakeTensor:
    def __init__(self, values: list[list[int]] | None = None) -> None:
        self.values = values or [[0, 255], [255, 0]]

    def to(self, _: str) -> "FakeTensor":
        return self

    def squeeze(self) -> "FakeTensor":
        return self

    def float(self) -> "FakeTensor":
        return self

    def clamp(self, _: int, __: int) -> "FakeTensor":
        return self

    def mul(self, _: int) -> "FakeTensor":
        return self

    def byte(self) -> "FakeTensor":
        return self

    def detach(self) -> "FakeTensor":
        return self

    def cpu(self) -> "FakeTensor":
        return self

    def tolist(self) -> list[list[int]]:
        return self.values


class FakeTorch:
    @staticmethod
    def inference_mode():
        return nullcontext()

    @staticmethod
    def sigmoid(value: FakeTensor) -> FakeTensor:
        return value


def test_birefnet_adapter_returns_mask_with_input_dimensions() -> None:
    adapter = BiRefNetAdapter("example/birefnet", device="cpu", torch_dtype="float32")
    adapter._processor = lambda **_: {"pixel_values": FakeTensor()}
    adapter._model = lambda **_: SimpleNamespace(logits=FakeTensor())
    adapter._torch = FakeTorch()
    image = Image.new("RGB", (6, 4), "white")

    mask = adapter.predict_mask(image)

    assert mask.mode == "L"
    assert mask.size == image.size


class FakeRemovalModel:
    def __init__(self) -> None:
        self.released = False

    def predict_mask(self, _: Image.Image) -> Image.Image:
        mask = Image.new("L", (100, 80), 0)
        for x in range(20, 80):
            for y in range(15, 65):
                mask.putpixel((x, y), 255)
        return mask

    def release(self) -> None:
        self.released = True


class FakeWorkerDatabase:
    def __init__(self, original_path: str) -> None:
        self.original_path = original_path
        self.completed: tuple | None = None

    def get_image(self, _: object) -> dict[str, object]:
        return {"original_path": self.original_path}

    def complete_background_removal(self, *values: object) -> None:
        self.completed = values


def test_background_removal_processor_writes_mask_and_cutout_artifacts(tmp_path) -> None:
    image_id = uuid4()
    job_id = uuid4()
    storage = WorkerStorage(str(tmp_path))
    original_path = artifact_path("originals", image_id, "png")
    original = Image.new("RGB", (100, 80), "red")
    original_buffer = BytesIO()
    original.save(original_buffer, format="PNG")
    storage.write_bytes(original_path, original_buffer.getvalue())
    database = FakeWorkerDatabase(original_path)
    job = ClaimedJob(
        id=job_id,
        image_id=image_id,
        job_type="background_removal",
        scene_preset=None,
        prompt=None,
        negative_prompt=None,
        variation_count=None,
        base_seed=None,
        settings={},
    )

    model = FakeRemovalModel()
    BackgroundRemovalProcessor(database, storage, model).process(job)

    assert database.completed is not None
    assert database.completed[0] == job_id
    mask_path = artifact_path("masks", image_id, "png")
    cutout_path = artifact_path("cutouts", image_id, "png")
    assert storage.read_bytes(mask_path)
    cutout = Image.open(BytesIO(storage.read_bytes(cutout_path)))
    assert cutout.mode == "RGBA"
    assert cutout.size == original.size
    assert model.released is True
