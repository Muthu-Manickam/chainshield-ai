from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://chainshield:chainshield@localhost:55432/chainshield"
    jwt_secret: str = "dev-only-secret-change-me-in-production"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-6-luna"
    llm_fallback_model: str = "anthropic/claude-haiku-5.5"
    llm_mode: str = "replay"
    llm_budget_usd: float = 3.0
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    data_dir: Path = ROOT / "data"
    artifacts_dir: Path = ROOT / "artifacts"
    guidance_dir: Path = ROOT / "corpus"


settings = Settings()
