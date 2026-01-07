"""Configurações da aplicação - carrega variáveis do .env"""
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # carrega local
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # ===========================================
    # SUPERADMIN
    # ===========================================
    superadmin_email: str | None = None
    superadmin_password: str | None = None
    superadmin_tenant_name: str | None = None
    superadmin_tenant_slug: str | None = None

    # ===========================================
    # Z-API (WhatsApp)
    # ===========================================
    zapi_instance_id: str = ""
    zapi_token: str = ""
    zapi_client_token: str = ""

    # ===========================================
    # VAPID (Push Notifications) ← NOVO
    # ===========================================
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:contato@velaris.app"
    
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
    # CORS
    # ===========================================
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    
    # ===========================================
    # OPENAI
    # ===========================================
    openai_api_key: str
    openai_model: str = "gpt-4o"
    
    # ===========================================
    # GUPSHUP (WhatsApp)
    # ===========================================
    gupshup_api_key: Optional[str] = None
    gupshup_app_name: Optional[str] = None
    gupshup_source_phone: Optional[str] = None
    gupshup_webhook_secret: Optional[str] = None
    
    # ===========================================
    # 360DIALOG (WhatsApp)
    # ===========================================
    dialog360_api_key: Optional[str] = None
    webhook_verify_token: str = "velaris_webhook_token"
    
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
    
    @property
    def dialog360_configured(self) -> bool:
        """Verifica se 360dialog está configurado."""
        return bool(self.dialog360_api_key)
    
    @property
    def vapid_configured(self) -> bool:
        """Verifica se VAPID está configurado para Push Notifications."""
        return bool(self.vapid_public_key and self.vapid_private_key)
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Retorna lista de origens CORS permitidas"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()