"""Application configuration loaded from environment."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nvidia_api_key: str = ""
    super_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nano_model: str = "nvidia/nemotron-3-nano-30b-a3b"
    nemotron_base_url: str = "https://integrate.api.nvidia.com/v1"

    api_port: int = 8000
    web_port: int = 3000
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./codemigrator.db"

    max_concurrent_calls: int = 15
    request_timeout_seconds: float = 120.0


settings = Settings()
