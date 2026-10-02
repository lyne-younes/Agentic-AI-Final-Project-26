from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Running from backend/ locally reads the repo-root .env; Docker Compose passes env vars.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str
    app_url: str = "http://localhost:3000"
    secret_key: str
    session_ttl_days: int = 7
    cookie_secure: bool = False

    google_client_id: str
    google_client_secret: str

    # Embeddings always use OpenAI; without a key, indexing fails.
    openai_api_key: str = ""
    upload_dir: str = "uploads"

    # Chat model via LiteLLM: switching provider is configuration only.
    chat_model: str = "anthropic/claude-sonnet-5"
    chat_api_key: str = Field(
        default="", validation_alias=AliasChoices("CHAT_API_KEY", "ANTHROPIC_API_KEY")
    )
    chat_api_base: str = ""  # only for self-hosted models, e.g. an Ollama URL

    # Calendar MCP server: the Study Planner's only route to Google Calendar.
    calendar_mcp_url: str = "http://calendar-mcp:3333/mcp"
    calendar_mcp_timeout: float = 30.0

    @property
    def google_redirect_uri(self) -> str:
        # The frontend origin proxies /api/* to this service, so cookies stay same-origin.
        return f"{self.app_url}/api/auth/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
