"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Luxe Sales Coach API"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Security
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/auth/callback"

    # Email domain allowlist (empty = allow all)
    allowed_email_domains: list[str] = []

    # Azure OAuth (Entra ID)
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant_id: str = "common"
    azure_redirect_uri: str = "http://localhost:5173/auth/callback"

    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_live_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 1024

    # Coach Agent
    coach_model: str = "gemini-2.0-flash"

    # Database (Firestore)
    gcp_project_id: str = ""
    firestore_database: str = "(default)"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://aistudio.google.com",
    ]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 1000
    rate_limit_auth_requests_per_minute: int = 10
    rate_limit_gemini_requests_per_minute: int = 100

    # WebSocket
    websocket_max_connections: int = 5
    websocket_timeout_minutes: int = 30

    # RAG Configuration
    rag_enabled: bool = True
    rag_collection_name: str = "knowledge_chunks"
    rag_embedding_model: str = "gemini-embedding-2"
    rag_top_k: int = 3
    rag_use_hybrid_search: bool = False
    rag_use_reranking: bool = False
    rag_use_conversation_context: bool = False
    rag_use_objection_lookup: bool = True
    rag_reranking_model: str = "gemini-2.0-flash"
    rag_reranking_initial_k: int = 10
    rag_reranking_final_k: int = 3

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
