from __future__ import annotations

import ctypes
import gc
import logging
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger("studio.worker")
_MIN_AVAILABLE_MEMORY_FOR_MODEL_OFFLOAD = 12 * 1024**3
BASE_PHOTOGRAPHY_STYLE = (
    "professional commercial product photography, realistic materials and lighting, "
    "high-end advertising campaign, sharp focus, clean intentional composition"
)


@dataclass(frozen=True)
class SingleVariationResult:
    image: Image.Image
    seed: int


@dataclass(frozen=True)
class VariationResult:
    seed: int
    image: Image.Image | None
    error_message: str | None = None
    duration_ms: float | None = None


def release_cuda_memory() -> None:
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def release_host_memory() -> None:
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (AttributeError, OSError):
        pass


class SDXLModelStack:
    """Lazily load the SDXL img2img + Canny ControlNet pipeline once per worker."""

    def __init__(
        self,
        base_model: str,
        controlnet_model: str,
        device: str = "cuda",
        torch_dtype: str = "float16",
        cache_dir: str | None = None,
        offload_mode: str = "auto",
    ):
        self.base_model = base_model
        self.controlnet_model = controlnet_model
        self.device = device
        self.torch_dtype = torch_dtype
        self.cache_dir = cache_dir
        self.offload_mode = offload_mode

    @cached_property
    def pipeline(self) -> Any:
        try:
            import torch
            from diffusers import ControlNetModel, StableDiffusionXLControlNetImg2ImgPipeline
            from diffusers.hooks import apply_group_offloading
        except ImportError as exc:
            raise RuntimeError("Diffusers, Accelerate, and PyTorch are required for SDXL generation") from exc

        dtype = self._resolve_dtype(torch)
        load_kwargs: dict[str, Any] = {
            "torch_dtype": dtype,
            "use_safetensors": True,
            "variant": "fp16" if dtype == torch.float16 else None,
        }
        load_kwargs = {key: value for key, value in load_kwargs.items() if value is not None}
        if self.cache_dir:
            load_kwargs["cache_dir"] = self.cache_dir
        controlnet = ControlNetModel.from_pretrained(self.controlnet_model, **load_kwargs)
        pipeline = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
            self.base_model,
            controlnet=controlnet,
            **load_kwargs,
        )
        if self.device.startswith("cuda"):
            resolved_offload_mode = self._resolve_offload_mode()
            if resolved_offload_mode == "disk":
                self._enable_disk_group_offload(pipeline, torch, apply_group_offloading)
            elif resolved_offload_mode == "sequential":
                pipeline.enable_sequential_cpu_offload()
            else:
                pipeline.enable_model_cpu_offload()
            pipeline.enable_attention_slicing("auto")
            pipeline.enable_vae_slicing()
            pipeline.enable_vae_tiling()
            logger.info("configured SDXL offload mode", extra={"offload_mode": resolved_offload_mode})
        else:
            pipeline.to(self.device)
        return pipeline

    def _resolve_offload_mode(self) -> str:
        valid_modes = {"auto", "model", "sequential", "disk"}
        if self.offload_mode not in valid_modes:
            raise ValueError(f"Unsupported SDXL offload mode '{self.offload_mode}'")
        if self.offload_mode != "auto":
            return self.offload_mode
        available_memory = self._available_memory_bytes()
        if available_memory is not None and available_memory < _MIN_AVAILABLE_MEMORY_FOR_MODEL_OFFLOAD:
            return "disk"
        return "model"

    @staticmethod
    def _available_memory_bytes() -> int | None:
        try:
            with open("/proc/meminfo", encoding="ascii") as handle:
                for line in handle:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            pass
        try:
            return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        except (AttributeError, OSError, ValueError):
            return None

    def _enable_disk_group_offload(self, pipeline: Any, torch: Any, apply_group_offloading: Any) -> None:
        offload_root = Path(self.cache_dir or ".model_offload") / "group_offload"
        for component_name in ("text_encoder", "text_encoder_2", "unet", "controlnet"):
            component = getattr(pipeline, component_name, None)
            if component is None:
                continue
            apply_group_offloading(
                component,
                onload_device=torch.device(self.device),
                offload_device=torch.device("cpu"),
                offload_type="block_level",
                num_blocks_per_group=1,
                offload_to_disk_path=str(offload_root / component_name),
            )
        pipeline.vae.to(self.device)
        release_host_memory()

    def _resolve_dtype(self, torch: Any) -> Any:
        if self.device.startswith("cuda") and self.torch_dtype == "float16":
            return torch.float16
        if self.device.startswith("cuda") and self.torch_dtype == "bfloat16":
            return torch.bfloat16
        if self.torch_dtype not in {"float16", "float32", "bfloat16"}:
            raise ValueError(f"Unsupported torch dtype '{self.torch_dtype}'")
        return torch.float32


def generate_single_variation(
    stack: SDXLModelStack,
    prompt: str,
    negative_prompt: str | None,
    init_image: Image.Image,
    control_image: Image.Image,
    seed: int,
    settings: Mapping[str, int | float] | None = None,
    torch_module: Any | None = None,
) -> SingleVariationResult:
    """Generate one background variation using a deterministic seed."""
    if seed < 0:
        raise ValueError("Seed must be non-negative")
    if torch_module is None:
        import torch as torch_module

    values = settings or {}
    generator = torch_module.Generator(device=stack.device).manual_seed(seed)
    result = stack.pipeline(
        prompt=prompt,
        prompt_2=f"{prompt}, {BASE_PHOTOGRAPHY_STYLE}",
        negative_prompt=negative_prompt,
        negative_prompt_2=negative_prompt,
        image=init_image.convert("RGB"),
        control_image=control_image.convert("RGB"),
        strength=float(values.get("strength", 0.9)),
        guidance_scale=float(values.get("guidance_scale", 8.0)),
        num_inference_steps=int(values.get("steps", 25)),
        controlnet_conditioning_scale=float(values.get("controlnet_conditioning_scale", 0.3)),
        control_guidance_end=0.65,
        aesthetic_score=7.0,
        negative_aesthetic_score=2.0,
        generator=generator,
        output_type="pil",
    )
    images = getattr(result, "images", None)
    if not images:
        raise RuntimeError("SDXL pipeline returned no images")
    return SingleVariationResult(image=images[0], seed=seed)


def generate_variations(
    stack: SDXLModelStack,
    prompt: str,
    negative_prompt: str | None,
    init_image: Image.Image,
    control_image: Image.Image,
    variation_count: int,
    base_seed: int | None,
    settings: Mapping[str, int | float] | None = None,
    torch_module: Any | None = None,
    on_result: Callable[[int, VariationResult], None] | None = None,
    skip_seeds: set[int] | None = None,
) -> list[VariationResult]:
    """Generate requested variations sequentially while retaining partial failures."""
    if variation_count not in {3, 4}:
        raise ValueError("Variation count must be 3 or 4")
    first_seed = base_seed if base_seed is not None else 0
    results: list[VariationResult] = []
    for index in range(variation_count):
        seed = first_seed + index
        if skip_seeds and seed in skip_seeds:
            continue
        started_at = time.perf_counter()
        try:
            result = generate_single_variation(
                stack,
                prompt,
                negative_prompt,
                init_image,
                control_image,
                seed,
                settings,
                torch_module,
            )
        except Exception as exc:
            logger.exception("SDXL variation failed", extra={"seed": seed})
            release_cuda_memory()
            variation = VariationResult(
                seed=seed,
                image=None,
                error_message=str(exc),
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            )
        else:
            variation = VariationResult(
                seed=result.seed,
                image=result.image,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            )
        results.append(variation)
        if on_result is not None:
            on_result(index, variation)
    return results
