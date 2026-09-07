import sys
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest
from PIL import Image

from app.pipelines.sdxl_generation import SDXLModelStack, generate_single_variation, generate_variations


class FakeGenerator:
    def __init__(self, device: str) -> None:
        self.device = device
        self.seed = None

    def manual_seed(self, seed: int) -> "FakeGenerator":
        self.seed = seed
        return self


class FakeTorch:
    Generator = FakeGenerator


class FakePipeline:
    def __init__(self) -> None:
        self.arguments = None

    def __call__(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(images=[Image.new("RGB", (32, 32), "beige")])


def test_generate_single_variation_passes_seed_and_conditioning() -> None:
    pipeline = FakePipeline()
    stack = cast(SDXLModelStack, cast(object, SimpleNamespace(device="cpu", pipeline=pipeline)))
    init_image = Image.new("RGB", (32, 32), "white")
    control_image = Image.new("L", (32, 32), 0)

    result = generate_single_variation(
        stack,
        prompt="premium product on a marble surface",
        negative_prompt="distorted label",
        init_image=init_image,
        control_image=control_image,
        seed=12345,
        settings={"steps": 25, "strength": 0.5},
        torch_module=FakeTorch,
    )

    assert result.seed == 12345
    assert result.image.size == (32, 32)
    assert pipeline.arguments is not None
    assert pipeline.arguments["prompt"] == "premium product on a marble surface"
    assert pipeline.arguments["prompt_2"].startswith("premium product on a marble surface")
    assert "commercial product photography" in pipeline.arguments["prompt_2"]
    assert pipeline.arguments["negative_prompt"] == "distorted label"
    assert pipeline.arguments["negative_prompt_2"] == "distorted label"
    assert pipeline.arguments["num_inference_steps"] == 25
    assert pipeline.arguments["strength"] == 0.5
    assert pipeline.arguments["control_guidance_end"] == 0.65
    assert pipeline.arguments["aesthetic_score"] == 7.0
    assert pipeline.arguments["negative_aesthetic_score"] == 2.0
    assert pipeline.arguments["generator"].seed == 12345


class FailingPipeline(FakePipeline):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("simulated CUDA failure")
        return super().__call__(**kwargs)


def test_generate_variations_preserves_partial_failures_and_seeds() -> None:
    pipeline = FailingPipeline()
    stack = cast(SDXLModelStack, cast(object, SimpleNamespace(device="cpu", pipeline=pipeline)))

    results = generate_variations(
        stack,
        "prompt",
        None,
        Image.new("RGB", (8, 8)),
        Image.new("L", (8, 8)),
        variation_count=3,
        base_seed=100,
        torch_module=FakeTorch,
    )

    assert [result.seed for result in results] == [100, 101, 102]
    assert results[0].image is not None
    assert results[1].image is None
    assert results[1].error_message == "simulated CUDA failure"
    assert results[2].image is not None


def test_generate_variations_reports_each_result_incrementally() -> None:
    observed: list[tuple[int, int, bool]] = []

    generate_variations(
        cast(SDXLModelStack, cast(object, SimpleNamespace(device="cpu", pipeline=FakePipeline()))),
        "prompt",
        None,
        Image.new("RGB", (8, 8)),
        Image.new("L", (8, 8)),
        variation_count=3,
        base_seed=10,
        torch_module=FakeTorch,
        on_result=lambda index, result: observed.append((index, result.seed, result.image is not None)),
    )

    assert observed == [(0, 10, True), (1, 11, True), (2, 12, True)]


def test_generate_single_variation_rejects_negative_seed() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        generate_single_variation(
            cast(SDXLModelStack, cast(object, SimpleNamespace(device="cpu", pipeline=FakePipeline()))),
            "prompt",
            None,
            Image.new("RGB", (8, 8)),
            Image.new("L", (8, 8)),
            -1,
            torch_module=FakeTorch,
        )


def test_auto_offload_uses_disk_when_available_memory_is_low(monkeypatch: pytest.MonkeyPatch) -> None:
    stack = SDXLModelStack("base", "control", offload_mode="auto")
    monkeypatch.setattr(stack, "_available_memory_bytes", lambda: 8 * 1024**3)

    assert stack._resolve_offload_mode() == "disk"


def test_auto_offload_uses_model_when_available_memory_is_sufficient(monkeypatch: pytest.MonkeyPatch) -> None:
    stack = SDXLModelStack("base", "control", offload_mode="auto")
    monkeypatch.setattr(stack, "_available_memory_bytes", lambda: 16 * 1024**3)

    assert stack._resolve_offload_mode() == "model"


def test_invalid_offload_mode_is_rejected() -> None:
    stack = SDXLModelStack("base", "control", offload_mode="unsupported")

    with pytest.raises(ValueError, match="Unsupported SDXL offload mode"):
        stack._resolve_offload_mode()


def test_model_loader_uses_diffusers_035_torch_dtype_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeControlNet:
        @classmethod
        def from_pretrained(cls, _model: str, **kwargs: object) -> object:
            calls.append(kwargs)
            return object()

    class FakeLoadedPipeline:
        @classmethod
        def from_pretrained(cls, _model: str, **kwargs: object) -> "FakeLoadedPipeline":
            calls.append(kwargs)
            return cls()

        def to(self, _device: str) -> None:
            return None

    fake_torch = ModuleType("torch")
    fake_torch.float16 = object()
    fake_torch.float32 = object()
    fake_torch.bfloat16 = object()
    fake_diffusers = ModuleType("diffusers")
    fake_diffusers.ControlNetModel = FakeControlNet
    fake_diffusers.StableDiffusionXLControlNetImg2ImgPipeline = FakeLoadedPipeline
    fake_hooks = ModuleType("diffusers.hooks")
    fake_hooks.apply_group_offloading = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "diffusers", fake_diffusers)
    monkeypatch.setitem(sys.modules, "diffusers.hooks", fake_hooks)

    stack = SDXLModelStack("base", "control", device="cpu")
    assert stack.pipeline is not None
    assert all("torch_dtype" in kwargs and "dtype" not in kwargs for kwargs in calls)
