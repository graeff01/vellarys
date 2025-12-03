"""
SERVIÇO DE AUTENTICAÇÃO
========================

Gerencia hash de senhas e tokens JWT.
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets
from jose import JWTError, jwt

from src.config import get_settings

settings = get_settings()

# Configurações JWT
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Gera hash da senha usando SHA256 + salt."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta."""
    try:
        salt, pwd_hash = hashed_password.split("$")
        return hashlib.sha256((plain_password + salt).encode()).hexdigest() == pwd_hash
    except ValueError:
        return False


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