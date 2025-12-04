"""Configurações da aplicação - carrega variáveis do .env"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # carrega local
        env_file_encoding="utf-8",
        case_sensitive=False
    )


    # ...
    superadmin_email: str | None = None
    superadmin_password: str | None = None
    superadmin_tenant_name: str | None = None
    superadmin_tenant_slug: str | None = None


    # ===========================================
    # CORE
    # ===========================================
    environment: str = "development"
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 1440
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # ===========================================
    # OPENAI
    # ===========================================
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # ===========================================
    # GUPSHUP (WhatsApp)
    # ===========================================
    gupshup_api_key: Optional[str] = None
    gupshup_app_name: Optional[str] = None
    gupshup_source_phone: Optional[str] = None  # Número WhatsApp Business
    gupshup_webhook_secret: Optional[str] = None  # Para validar assinaturas

    # ===========================================
    # PROPRIEDADES
    # ===========================================
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def gupshup_configured(self) -> bool:
        """Verifica se Gupshup está configurado."""
        return bool(
            self.gupshup_api_key and 
            self.gupshup_app_name and 
            self.gupshup_source_phone
        )

print("🔗 DATABASE_URL ATUAL:", settings.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()