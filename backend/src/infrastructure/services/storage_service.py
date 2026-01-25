"""
Storage Service - Upload e Armazenamento de Arquivos
=====================================================

Gerencia upload de anexos (imagens, documentos, áudio, vídeo).

Suporta:
- Local: Salva em /app/storage (desenvolvimento)
- S3: AWS S3 (produção - futuro)

Validações:
- Tipos permitidos: image/*, application/pdf, audio/*, video/*
- Tamanho máximo: 10MB
- Sanitização de nomes de arquivo
"""
import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import logging
import aiofiles

logger = logging.getLogger(__name__)

# Configurações
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")
STORAGE_LOCAL_PATH = os.getenv("STORAGE_LOCAL_PATH", "/app/storage")
STORAGE_BASE_URL = os.getenv("STORAGE_BASE_URL", "http://localhost:8000/storage")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Tipos MIME permitidos
ALLOWED_MIMETYPES = {
    # Imagens
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    # Documentos
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Áudio
    "audio/mpeg", "audio/ogg", "audio/wav", "audio/mp4",
    # Vídeo
    "video/mp4", "video/quicktime", "video/x-msvideo"
}


class StorageService:
    """Serviço de armazenamento de arquivos."""

    def __init__(self):
        self.storage_type = STORAGE_TYPE
        self.local_path = Path(STORAGE_LOCAL_PATH)
        self.base_url = STORAGE_BASE_URL

        # Cria diretório local se não existir
        if self.storage_type == "local":
            self.local_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"[Storage] Modo LOCAL: {self.local_path}")

    def validate_file(self, filename: str, content_type: str, size: int) -> Tuple[bool, Optional[str]]:
        """
        Valida arquivo antes de upload.

        Returns:
            (is_valid, error_message)
        """
        # Validar tamanho
        if size > MAX_FILE_SIZE:
            return False, f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE / 1024 / 1024}MB"

        # Validar tipo MIME
        if content_type not in ALLOWED_MIMETYPES:
            return False, f"Tipo de arquivo não permitido: {content_type}"

        # Validar extensão
        ext = Path(filename).suffix.lower()
        if not ext:
            return False, "Arquivo sem extensão"

        return True, None

    def sanitize_filename(self, filename: str) -> str:
        """Remove caracteres perigosos do nome do arquivo."""
        # Remove path traversal
        filename = Path(filename).name

        # Remove caracteres especiais
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        filename = "".join(c if c in safe_chars else "_" for c in filename)

        return filename

    def generate_unique_filename(self, original_filename: str) -> str:
        """Gera nome único baseado em UUID."""
        ext = Path(original_filename).suffix
        unique_name = f"{uuid.uuid4()}{ext}"
        return unique_name

    async def save_local(self, file_content: bytes, filename: str) -> str:
        """
        Salva arquivo localmente.

        Returns:
            Caminho relativo do arquivo
        """
        # Organiza em subpastas por data (YYYY/MM/DD)
        now = datetime.utcnow()
        subfolder = self.local_path / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        subfolder.mkdir(parents=True, exist_ok=True)

        # Caminho completo
        file_path = subfolder / filename

        # Salva arquivo
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        # Retorna caminho relativo
        relative_path = file_path.relative_to(self.local_path)
        logger.info(f"[Storage] Arquivo salvo: {relative_path}")

        return str(relative_path)

    def get_public_url(self, relative_path: str) -> str:
        """Retorna URL pública do arquivo."""
        # Remove barras iniciais
        relative_path = relative_path.lstrip("/")

        if self.storage_type == "local":
            return f"{self.base_url}/{relative_path}"
        elif self.storage_type == "s3":
            # TODO: Implementar S3
            return f"https://s3.amazonaws.com/vellarys/{relative_path}"

        return relative_path

    def get_file_type(self, mime_type: str) -> str:
        """Mapeia MIME type para categoria."""
        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("audio/"):
            return "audio"
        elif mime_type.startswith("video/"):
            return "video"
        elif "pdf" in mime_type or "document" in mime_type or "sheet" in mime_type:
            return "document"
        else:
            return "file"

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str
    ) -> dict:
        """
        Faz upload completo do arquivo.

        Returns:
            {
                "type": "image",
                "url": "https://...",
                "filename": "documento.pdf",
                "mime_type": "application/pdf",
                "size": 245678,
                "uploaded_at": "2026-01-25T10:00:00Z"
            }
        """
        # 1. Validar
        is_valid, error = self.validate_file(filename, content_type, len(file_content))
        if not is_valid:
            raise ValueError(error)

        # 2. Sanitizar e gerar nome único
        safe_filename = self.sanitize_filename(filename)
        unique_filename = self.generate_unique_filename(safe_filename)

        # 3. Salvar
        if self.storage_type == "local":
            relative_path = await self.save_local(file_content, unique_filename)
        else:
            # TODO: Implementar S3
            raise NotImplementedError("S3 storage não implementado ainda")

        # 4. Retornar metadados
        return {
            "type": self.get_file_type(content_type),
            "url": self.get_public_url(relative_path),
            "filename": safe_filename,
            "mime_type": content_type,
            "size": len(file_content),
            "uploaded_at": datetime.utcnow().isoformat()
        }


# Singleton global
storage_service = StorageService()
