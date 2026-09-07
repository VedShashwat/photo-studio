from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from PIL import Image

from app import job_runner as job_runner_module
from app.job_runner import GenerationProcessor
from app.pipelines.postprocessing import compose_product_canvas
from app.pipelines.sdxl_generation import VariationResult
from app.services.db_client import ClaimedJob
from app.services.storage_client import WorkerStorage
from shared.python.storage_paths import artifact_path


class FakeGenerationDatabase:
    def __init__(self, cutout_path: str, completed_seeds: set[int] | None = None) -> None:
        self.cutout_path = cutout_path
        self.completed_seeds = completed_seeds or set()
        self.outputs: list[tuple] = []
        self.completed: tuple | None = None

    def get_image(self, _: object) -> dict[str, object]:
        return {"cutout_path": self.cutout_path}

    def get_succeeded_output_seeds(self, _: object) -> set[int]:
        return self.completed_seeds

    def save_generation_output(self, *values: object, **kwargs: object) -> None:
        self.outputs.append((values, kwargs))

    def complete_generation_job(self, *values: object, **kwargs: object) -> None:
        self.completed = (values, kwargs)


def test_generation_processor_writes_outputs_and_completes_job(tmp_path, monkeypatch) -> None:
    image_id = uuid4()
    job_id = uuid4()
    storage = WorkerStorage(str(tmp_path))
    cutout_path = artifact_path("cutouts", image_id, "png")
    cutout = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
    buffer = BytesIO()
    cutout.save(buffer, format="PNG")
    storage.write_bytes(cutout_path, buffer.getvalue())
    database = FakeGenerationDatabase(cutout_path)
    job = ClaimedJob(
        id=job_id,
        image_id=image_id,
        job_type="background_generation",
        scene_preset="luxury_studio",
        prompt="premium product",
        negative_prompt="distorted label",
        variation_count=3,
        base_seed=100,
        settings={"canvas_size": 32},
    )
    composition = compose_product_canvas(cutout, canvas_size=32, padding_ratio=0.1)
    generated = [VariationResult(seed=100 + index, image=Image.new("RGB", (32, 32), "blue")) for index in range(3)]
    canny_calls: list[dict[str, object]] = []

    def fake_canny(*_args, **kwargs):
        canny_calls.append(kwargs)
        return Image.new("L", (32, 32), 0)

    monkeypatch.setattr(job_runner_module, "create_canny_control", fake_canny)
    monkeypatch.setattr(job_runner_module, "compose_product_canvas", lambda *_args, **_kwargs: composition)
    def fake_generate(_stack, **kwargs):
        assert kwargs["skip_seeds"] == set()
        for index, result in enumerate(generated):
            kwargs["on_result"](index, result)
        return generated

    monkeypatch.setattr(job_runner_module, "generate_variations", fake_generate)

    GenerationProcessor(database, storage, SimpleNamespace()).process(job)

    assert len(database.outputs) == 3
    assert database.completed is not None
    assert database.completed[0] == (job_id, "succeeded")
    assert database.completed[1]["error_message"] is None
    assert database.completed[1]["metrics"]["completed_outputs"] == 3
    assert database.completed[1]["metrics"]["total_outputs"] == 3
    assert database.completed[1]["metrics"]["settings"] == {"canvas_size": 32}
    assert canny_calls == [{"alpha": composition.product_mask, "include_luminance": False}]
    for index, (output_values, output_kwargs) in enumerate(database.outputs):
        assert output_values[1] == job_id
        assert output_values[3] == 100 + index
        assert output_values[4:6] == (32, 32)
        assert storage.read_bytes(output_values[2])
        assert storage.read_bytes(output_kwargs["control_path"])
        assert storage.read_bytes(output_kwargs["background_path"])
        assert output_kwargs["metrics"]["variation_index"] == index
        assert output_kwargs["metrics"]["settings"] == {"canvas_size": 32}


def test_generation_processor_persists_partial_failures(tmp_path, monkeypatch) -> None:
    image_id = uuid4()
    job_id = uuid4()
    storage = WorkerStorage(str(tmp_path))
    cutout_path = artifact_path("cutouts", image_id, "png")
    buffer = BytesIO()
    Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(buffer, format="PNG")
    storage.write_bytes(cutout_path, buffer.getvalue())
    database = FakeGenerationDatabase(cutout_path)
    job = ClaimedJob(
        id=job_id,
        image_id=image_id,
        job_type="background_generation",
        scene_preset="luxury_studio",
        prompt="premium product",
        negative_prompt=None,
        variation_count=3,
        base_seed=200,
        settings={"canvas_size": 32},
    )
    composition = compose_product_canvas(Image.new("RGBA", (16, 16), (255, 0, 0, 255)), canvas_size=32)
    generated = [
        VariationResult(seed=200, image=Image.new("RGB", (32, 32), "blue")),
        VariationResult(seed=201, image=None, error_message="simulated variation failure"),
        VariationResult(seed=202, image=Image.new("RGB", (32, 32), "green")),
    ]
    monkeypatch.setattr(job_runner_module, "create_canny_control", lambda *_args, **_kwargs: Image.new("L", (32, 32), 0))
    monkeypatch.setattr(job_runner_module, "compose_product_canvas", lambda *_args, **_kwargs: composition)
    def fake_generate(_stack, **kwargs):
        assert kwargs["skip_seeds"] == set()
        for index, result in enumerate(generated):
            kwargs["on_result"](index, result)
        return generated

    monkeypatch.setattr(job_runner_module, "generate_variations", fake_generate)

    GenerationProcessor(database, storage, SimpleNamespace()).process(job)

    assert len(database.outputs) == 3
    assert database.outputs[1][0][3] == 201
    assert database.outputs[1][1]["status"] == "failed"
    assert database.outputs[1][1]["error_message"] == "simulated variation failure"
    assert database.completed is not None
    assert database.completed[0] == (job_id, "partially_succeeded")
    assert database.completed[1]["metrics"]["completed_outputs"] == 2
    assert database.completed[1]["metrics"]["total_outputs"] == 3
    assert "simulated variation failure" in database.completed[1]["error_message"]


def test_generation_processor_skips_already_persisted_variations(tmp_path, monkeypatch) -> None:
    image_id = uuid4()
    job_id = uuid4()
    storage = WorkerStorage(str(tmp_path))
    cutout_path = artifact_path("cutouts", image_id, "png")
    buffer = BytesIO()
    Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(buffer, format="PNG")
    storage.write_bytes(cutout_path, buffer.getvalue())
    database = FakeGenerationDatabase(cutout_path, {31415, 31416})
    job = ClaimedJob(
        id=job_id,
        image_id=image_id,
        job_type="background_generation",
        scene_preset="luxury_studio",
        prompt="premium product",
        negative_prompt=None,
        variation_count=3,
        base_seed=31415,
        settings={"canvas_size": 32},
    )
    composition = compose_product_canvas(Image.new("RGBA", (16, 16), (255, 0, 0, 255)), canvas_size=32)
    monkeypatch.setattr(job_runner_module, "create_canny_control", lambda *_args, **_kwargs: Image.new("L", (32, 32), 0))
    monkeypatch.setattr(job_runner_module, "compose_product_canvas", lambda *_args, **_kwargs: composition)

    def fake_generate(_stack, **kwargs):
        assert kwargs["skip_seeds"] == {31415, 31416}
        result = VariationResult(seed=31417, image=Image.new("RGB", (32, 32), "blue"))
        kwargs["on_result"](2, result)
        return [result]

    monkeypatch.setattr(job_runner_module, "generate_variations", fake_generate)

    GenerationProcessor(database, storage, SimpleNamespace()).process(job)

    assert len(database.outputs) == 1
    assert database.outputs[0][0][3] == 31417
    assert database.outputs[0][1]["metrics"]["variation_index"] == 2
    assert database.completed is not None
    assert database.completed[0] == (job_id, "succeeded")
    assert database.completed[1]["metrics"]["completed_outputs"] == 3
