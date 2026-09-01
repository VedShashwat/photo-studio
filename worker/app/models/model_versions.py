from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelVersion:
    component: str
    identifier: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def configured_versions(
    background_removal_model: str,
    sdxl_base_model: str | None = None,
    sdxl_controlnet_model: str | None = None,
) -> dict[str, dict[str, str]]:
    """Return reproducible model identifiers without importing ML libraries."""
    versions = {
        "background_removal": ModelVersion(
            component="background_removal",
            identifier=background_removal_model,
        ).as_dict()
    }
    if sdxl_base_model:
        versions["sdxl_base"] = ModelVersion("sdxl_base", sdxl_base_model).as_dict()
    if sdxl_controlnet_model:
        versions["sdxl_controlnet"] = ModelVersion("sdxl_controlnet", sdxl_controlnet_model).as_dict()
    return versions
