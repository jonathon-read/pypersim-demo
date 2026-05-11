from pathlib import Path
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PYPERSIM_DEMO_")

    data_dir: Path = Path.cwd() / "data"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Agent model — provider selects the ADK wrapper class:
    #   "litellm"  → LiteLlm; model_name uses LiteLLM routing strings
    #                e.g. "ollama_chat/qwen2.5:7b", "openai/gpt-4o", "anthropic/claude-3-5-sonnet"
    #   "google"   → Gemini (native Google AI / Vertex); model_name is the Gemini model ID
    #                e.g. "gemini-2.0-flash", "gemini-1.5-pro"
    agent_model_provider: Literal["litellm", "google"] = "litellm"
    agent_model_name: str = "ollama_chat/qwen2.5:7b"

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
