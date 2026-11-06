from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_parse_model: str = "gemini-3.5-flash"
    gemini_generate_model: str = "gemini-3.1-pro-preview"
    gemini_embed_model: str = "gemini-embedding-2"
    embed_dim: int = 768
    dedup_threshold: float = 0.85
    recency_decay: float = 0.85
    slot_min_share: float = 0.6
    surprise_count: int = 3
    study_guide_size: int = 10
    database_url: str = "sqlite:///./exam_analyzer.db"
    storage_dir: str = "./storage/papers"
    frontend_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
