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
    access_token_expire_minutes: int = 15  # Reduzido para 15 min (mais seguro com refresh)
    refresh_token_expire_days: int = 7  # Refresh token dura 7 dias
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # ===========================================
    # REDIS (Cache & Rate Limiting)
    # ===========================================
    redis_url: Optional[str] = None  # Ex: redis://default:xxx@xxx.railway.app:6379
    
    # ===========================================
    # DATABASE POOL (Escalabilidade)
    # ===========================================
    db_pool_size: int = 15  # Conexões permanentes
    db_max_overflow: int = 30  # Conexões extras em pico
    db_pool_recycle: int = 3600  # Recicla conexões após 1h
    db_pool_timeout: int = 30  # Timeout para obter conexão
    
    # ===========================================
    # CORS
    # ===========================================
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080,https://vellarys.up.railway.app,https://vellarys-production.up.railway.app,https://velaris.app"
    
    # ===========================================
    # OPENAI
    # ===========================================
    openai_api_key: str
    openai_model: str = "gpt-4o"

    # ===========================================
    # AI CONSTANTS
    # ===========================================
    max_message_length: int = 2000
    max_conversation_history: int = 30
    openai_timeout_seconds: int = 30
    openai_max_retries: int = 2
    
    # ===========================================
    # EMAIL (Resend)
    # ===========================================
    resend_api_key: Optional[str] = None
    email_from: str = "noreply@vellarys.app"
    frontend_url: str = "http://localhost:3000"  # Para links de reset
    
    # ===========================================
    # SENTRY (Error Tracking)
    # ===========================================
    sentry_dsn: Optional[str] = None
    
    # ===========================================
    # GUPSHUP (WhatsApp)  novo
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
        if not self.cors_origins:
            return ["*"]
        if self.cors_origins == "*":
            return ["*"]
        # Filtra strings vazias e remove espaços
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

# ===========================================
# FALLBACK RESPONSES (não precisam ser do env)
# ===========================================
FALLBACK_RESPONSES = {
    "error": "Desculpe, estou com uma instabilidade momentânea. Tente novamente em alguns segundos.",
    "security": "Por segurança, não posso responder a essa mensagem.",
}