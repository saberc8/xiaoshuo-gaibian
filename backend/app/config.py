from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NOVEL_", env_file=ROOT / ".env", extra="ignore"
    )
    data_dir: Path = ROOT / "data"
    api_url: str = "http://127.0.0.1:8010"
    database_url: str = "postgresql://localhost/xuzhang"
    database_schema: str = "public"
    max_upload_bytes: int = 30 * 1024 * 1024
    max_archive_bytes: int = 200 * 1024 * 1024


