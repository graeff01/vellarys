"""
SERVIÇO DE AUTENTICAÇÃO
========================

Gerencia hash de senhas e tokens JWT.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from passlib.context import CryptContext
from jose import JWTError, jwt

from src.config import get_settings

settings = get_settings()

# Configuração do contexto de criptografia usando PBKDF2-SHA256 (Padrão Django/Enterprise)
# Extremamente robusto, sem limite de caracteres e altamente compatível.
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "sha256_crypt"], 
    deprecated="auto",
    pbkdf2_sha256__rounds=200000  # 200k é seguro e evita timeouts em PRD
)
# Configurações JWT
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Gera o hash da senha usando Bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> Tuple[bool, bool]:
    """
    Verifica se a senha está correta.
    Retorna (senha_valida, precisa_de_upgrade)
    """
    # Identificação de hashes SHA256 legados (ex: 'salt$hash')
    # Diferencia de hashes passlib que começam com '$' (ex: '$pbkdf2-sha256$...')
    is_legacy = "$" in hashed_password and not hashed_password.startswith("$")

    if is_legacy:
        try:
            salt, old_hash = hashed_password.split("$", 1)
            import hashlib
            is_valid = hashlib.sha256((plain_password + salt).encode()).hexdigest() == old_hash
            return is_valid, True # Se válida, precisa de upgrade para PBKDF2
        except Exception as e:
            from src.api.routes.auth import logger
            logger.error(f"Erro na verificação de hash legado: {e}")
            return False, False

    try:
        isValid = pwd_context.verify(plain_password, hashed_password)
        needsUpgrade = pwd_context.needs_update(hashed_password)
        return isValid, needsUpgrade
    except Exception as e:
        # Se falhar a verificação (ex: hash corrompido ou formato desconhecido)
        return False, False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria token JWT.
    
    Args:
        data: Dados a incluir no token (ex: {"sub": user_id})
        expires_delta: Tempo de expiração
    
    Returns:
        Token JWT assinado
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica e valida token JWT.
    
    Returns:
        Dados do token ou None se inválido
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None