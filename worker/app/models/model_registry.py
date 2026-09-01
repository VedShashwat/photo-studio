from functools import cached_property

from app.models.model_versions import configured_versions


class ModelRegistry:
    def __init__(
        self,
        model_name: str,
        device: str = "cuda",
        torch_dtype: str = "float16",
        cache_dir: str | None = None,
        sdxl_base_model: str | None = None,
        sdxl_controlnet_model: str | None = None,
        sdxl_offload_mode: str = "auto",
    ):
        self.model_name = model_name
        self.device = device
        self.torch_dtype = torch_dtype
        self.cache_dir = cache_dir
        self.sdxl_base_model = sdxl_base_model
        self.sdxl_controlnet_model = sdxl_controlnet_model
        self.sdxl_offload_mode = sdxl_offload_mode

    @cached_property
    def birefnet(self):
        from app.pipelines.background_removal import BiRefNetAdapter

        return BiRefNetAdapter(
            self.model_name,
            device=self.device,
            torch_dtype=self.torch_dtype,
            cache_dir=self.cache_dir,
        )

    @cached_property
    def sdxl(self):
        if not self.sdxl_base_model or not self.sdxl_controlnet_model:
            raise RuntimeError("SDXL model identifiers are not configured")
        from app.pipelines.sdxl_generation import SDXLModelStack

        return SDXLModelStack(
            self.sdxl_base_model,
            self.sdxl_controlnet_model,
            device=self.device,
            torch_dtype=self.torch_dtype,
            cache_dir=self.cache_dir,
            offload_mode=self.sdxl_offload_mode,
        )

    @property
    def versions(self) -> dict[str, dict[str, str]]:
        return configured_versions(self.model_name, self.sdxl_base_model, self.sdxl_controlnet_model)

    @property
    def runtime_settings(self) -> dict[str, str | None]:
        return {
            "device": self.device,
            "torch_dtype": self.torch_dtype,
            "cache_dir": self.cache_dir,
            "sdxl_offload_mode": self.sdxl_offload_mode,
        }
