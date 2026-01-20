"""
ENCRYPTION SERVICE
==================

Serviço para criptografar/descriptografar credenciais sensíveis.
Usa Fernet (AES-128-CBC) derivada da SECRET_KEY da aplicação.
"""

import json
import logging
import base64
import hashlib
from typing import Dict, Any, Optional

from cryptography.fernet import Fernet

from src.config import get_settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """
    Cria instância Fernet usando a SECRET_KEY da aplicação.

    A SECRET_KEY é convertida para formato Fernet (32 bytes, base64).
    """
    settings = get_settings()
    key = settings.secret_key

    # Deriva uma chave de 32 bytes via SHA256
    derived = hashlib.sha256(key.encode()).digest()

    # Codifica em base64 URL-safe (formato Fernet)
    fernet_key = base64.urlsafe_b64encode(derived)

    return Fernet(fernet_key)


def encrypt_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Criptografa dicionário de credenciais.

    Args:
        credentials: Dicionário com credenciais em texto plano

    Returns:
        {
            "_encrypted": True,
            "data": "<base64_encrypted_string>"
        }
    """
    if not credentials:
        return {}

    try:
        fernet = _get_fernet()

        # Serializa para JSON
        json_str = json.dumps(credentials)

        # Criptografa
        encrypted = fernet.encrypt(json_str.encode())

        return {
            "_encrypted": True,
            "data": encrypted.decode()
        }
    except Exception as e:
        logger.error(f"Erro ao criptografar credenciais: {e}")
        raise


def decrypt_credentials(encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Descriptografa credenciais.

    Args:
        encrypted_data: Dados criptografados no formato do encrypt_credentials

    Returns:
        Dicionário com credenciais em texto plano
    """
    if not encrypted_data:
        return {}

    # Se não está marcado como criptografado, retorna como está
    # (para compatibilidade com dados antigos)
    if not encrypted_data.get("_encrypted"):
        return encrypted_data

    try:
        fernet = _get_fernet()

        # Descriptografa
        decrypted = fernet.decrypt(encrypted_data["data"].encode())

        # Deserializa JSON
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"Erro ao descriptografar credenciais: {e}")
        return {}


def mask_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mascara valores sensíveis para exibição em logs/responses.

    Args:
        credentials: Dicionário com credenciais

    Returns:
        Dicionário com valores sensíveis mascarados
    """
    if not credentials:
        return {}

    # Campos que devem ser mascarados
    sensitive_keys = {
        "api_key", "token", "password", "secret",
        "key_value", "client_secret", "access_token",
        "refresh_token", "bearer", "authorization"
    }

    masked = {}
    for key, value in credentials.items():
        if key.lower() in sensitive_keys and value:
            # Mostra apenas primeiros 4 caracteres
            str_value = str(value)
            if len(str_value) > 4:
                masked[key] = f"{str_value[:4]}****"
            else:
                masked[key] = "****"
        else:
            masked[key] = value

    return masked


def is_encrypted(data: Optional[Dict[str, Any]]) -> bool:
    """Verifica se dados estão criptografados."""
    if not data:
        return False
    return data.get("_encrypted", False) is True
