from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PYPERSIM_DEMO_")

    data_dir: Path = Path.cwd() / "data"
    embedding_model: str = "all-MiniLM-L6-v2"

    @computed_field
    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "db.sqlite"

    @computed_field
    @property
    def lance_dir(self) -> Path:
        return self.data_dir / "lance"

    def ensure_dirs_exist(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lance_dir.mkdir(parents=True, exist_ok=True)
