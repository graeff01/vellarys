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

# Configurações de Hashing (Argon2id é o padrão atual da OWASP)
# Mantemos suporte ao SHA256 antigo para migração transparente
pwd_context = CryptContext(
    schemes=["argon2", "sha256_crypt"],
    deprecated="auto",
)

# Configurações JWT
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Gera hash da senha usando Argon2id."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> Tuple[bool, bool]:
    """
    Verifica se a senha está correta.
    Retorna (senha_valida, precisa_de_upgrade)
    """
    if not hashed_password:
        return False, False
        
    # Se o hash for do tipo antigo (SHA256 simples com salt$), convertemos para o contexto do passlib
    # Isso lida com sua implementação anterior de salt$hash
    if "$" in hashed_password and not hashed_password.startswith("$argon2"):
        # Verificação compatível com a lógica antiga para permitir migração
        try:
            salt, old_hash = hashed_password.split("$", 1)
            import hashlib
            is_valid = hashlib.sha256((plain_password + salt).encode()).hexdigest() == old_hash
            return is_valid, True # Se válida, precisa de upgrade para Argon2
        except:
            return False, False

    isValid = pwd_context.verify(plain_password, hashed_password)
    needsUpgrade = pwd_context.needs_update(hashed_password)
    
    return isValid, needsUpgrade


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