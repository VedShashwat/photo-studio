from unittest.mock import patch

from app.models.model_registry import ModelRegistry


def test_model_registry_loads_birefnet_lazily_and_reuses_instance() -> None:
    with patch("app.pipelines.background_removal.BiRefNetAdapter") as adapter_factory:
        registry = ModelRegistry(
            "example/birefnet",
            device="cuda",
            torch_dtype="float16",
            cache_dir="/models",
        )
        adapter_factory.assert_not_called()

        first = registry.birefnet
        second = registry.birefnet

    assert first is second
    adapter_factory.assert_called_once_with(
        "example/birefnet",
        device="cuda",
        torch_dtype="float16",
        cache_dir="/models",
    )


def test_model_registry_reports_configured_versions_and_runtime_settings() -> None:
    registry = ModelRegistry(
        "ZhengPeng7/BiRefNet",
        device="cuda",
        cache_dir="/models",
        sdxl_base_model="base/model",
        sdxl_controlnet_model="control/model",
    )

    assert registry.versions == {
        "background_removal": {
            "component": "background_removal",
            "identifier": "ZhengPeng7/BiRefNet",
        },
        "sdxl_base": {"component": "sdxl_base", "identifier": "base/model"},
        "sdxl_controlnet": {"component": "sdxl_controlnet", "identifier": "control/model"},
    }
    assert registry.runtime_settings == {
        "device": "cuda",
        "torch_dtype": "float16",
        "cache_dir": "/models",
        "sdxl_offload_mode": "auto",
    }


def test_model_registry_caches_sdxl_stack_without_loading_weights() -> None:
    with patch("app.pipelines.sdxl_generation.SDXLModelStack") as stack_factory:
        registry = ModelRegistry(
            "background/model",
            sdxl_base_model="base/model",
            sdxl_controlnet_model="control/model",
        )
        stack_factory.assert_not_called()

        first = registry.sdxl
        second = registry.sdxl

    assert first is second
    stack_factory.assert_called_once_with(
        "base/model",
        "control/model",
        device="cuda",
        torch_dtype="float16",
        cache_dir=None,
        offload_mode="auto",
    )
