"""
Entidade: Refresh Token
Armazena tokens de refresh para autenticação segura
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class RefreshToken(Base):
    """Token de refresh para renovação de access tokens."""
    
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relacionamentos
    user = relationship("User", back_populates="refresh_tokens")
    
    def is_valid(self) -> bool:
        """Verifica se o token ainda é válido."""
        if self.revoked:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return True
