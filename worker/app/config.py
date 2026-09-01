from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    database_url: str = "postgresql+psycopg://studio:studio@localhost:5432/studio"
    storage_root: str = "./storage"
    device: str = "cuda"
    torch_dtype: str = "float16"
    sdxl_offload_mode: str = "auto"
    model_cache_dir: str = "./model_cache"
    background_removal_model: str = "ZhengPeng7/BiRefNet"
    sdxl_base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    sdxl_canny_controlnet_model: str = "diffusers/controlnet-canny-sdxl-1.0"
    job_poll_interval_seconds: float = 2.0
    job_timeout_seconds: int = 1800
    max_concurrent_gpu_jobs: int = 1
    default_canvas_size: int = 1024
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
