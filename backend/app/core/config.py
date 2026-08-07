from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://studio:studio@localhost:5432/studio"
    storage_root: str = "./storage"
    frontend_origin: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    public_storage_base_url: str = ""
    max_upload_mb: int = 15
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origins(self) -> list[str]:
        origins = {origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()}
        if self.app_env == "local":
            origins.update({"http://localhost:3000", "http://localhost:3001"})
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
