"""
Configuración de la aplicación usando Pydantic Settings.
Carga variables de entorno desde .env
"""

from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="allow"
    )

    # =============================================================================
    # GOOGLE GEMINI
    # =============================================================================
    gemini_api_key: str = Field(..., description="API Key de Google Gemini")
    gemini_pro_model: str = Field(default="gemini-2.5-pro-latest")
    gemini_flash_model: str = Field(default="gemini-2.5-flash-latest")
    gemini_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    gemini_max_output_tokens: int = Field(default=8192)
    gemini_top_p: float = Field(default=0.95)
    gemini_top_k: int = Field(default=40)

    # =============================================================================
    # MONGODB
    # =============================================================================
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="hacknation_medical")
    mongodb_max_connections: int = Field(default=10)
    mongodb_min_connections: int = Field(default=1)

    # =============================================================================
    # CHROMADB
    # =============================================================================
    chroma_persist_directory: str = Field(default="./data/vectorstore")
    chroma_collection_prefix: str = Field(default="medical_kb")
    chroma_embedding_model: str = Field(default="models/text-embedding-004")

    # =============================================================================
    # PUBMED/NCBI
    # =============================================================================
    pubmed_email: str = Field(..., description="Email para PubMed API")
    pubmed_api_key: str = Field(default="")
    pubmed_max_results: int = Field(default=10)
    pubmed_tool_name: str = Field(default="ClinicalCrew")

    # =============================================================================
    # API
    # =============================================================================
    api_v1_prefix: str = Field(default="/api/v1")
    api_title: str = Field(default="Clinical Crew")
    api_version: str = Field(default="1.0.0")
    api_description: str = Field(
        default="Sistema de interconsultation médica con IA multi-agente"
    )
    debug: bool = Field(default=True)
    cors_origins_str: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    # =============================================================================
    # AGENT CONFIGURATION
    # =============================================================================
    max_interconsultas_paralelas: int = Field(default=5)
    timeout_especialista_segundos: int = Field(default=120)
    enable_streaming: bool = Field(default=True)
    max_retries: int = Field(default=3)

    # =============================================================================
    # LOGGING
    # =============================================================================
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: str = Field(default="logs/app.log")

    # =============================================================================
    # SECURITY
    # =============================================================================
    secret_key: str = Field(default="changeme-insecure-secret-key")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)

    # =============================================================================
    # PATHS
    # =============================================================================
    knowledge_base_path: str = Field(default="./data/knowledge_base")
    especialistas_config_path: str = Field(default="./app/config/specialists.yaml")


@lru_cache()
def get_settings() -> Settings:
    """
    Obtener la configuración de la aplicación (cached).

    Returns:
        Settings: Configuración de la aplicación
    """
    return Settings()


# Instancia global de settings
settings = get_settings()
