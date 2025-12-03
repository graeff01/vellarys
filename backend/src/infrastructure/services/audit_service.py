"""
AUDIT LOG SERVICE - Serviço de Auditoria
==========================================

Registra TODAS as ações do sistema para:
- Compliance (LGPD, etc)
- Segurança
- Debug
- Análise de comportamento

Tipos de eventos:
- Mensagens recebidas/enviadas
- Ações da IA
- Tentativas de ataque
- Acessos a dados
- Alterações de dados
- Logins/Logouts
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AuditAction(str, Enum):
    """Tipos de ações auditáveis."""
    
    # Mensagens
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    MESSAGE_BLOCKED = "message_blocked"
    
    # IA
    AI_RESPONSE_GENERATED = "ai_response_generated"
    AI_HANDOFF_TRIGGERED = "ai_handoff_triggered"
    AI_QUALIFICATION_CHANGED = "ai_qualification_changed"
    
    # Segurança
    SECURITY_THREAT_DETECTED = "security_threat_detected"
    SECURITY_BLOCKED = "security_blocked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Dados
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    LEAD_DELETED = "lead_deleted"
    LEAD_DATA_EXPORTED = "lead_data_exported"
    
    # LGPD
    LGPD_DATA_REQUESTED = "lgpd_data_requested"
    LGPD_DATA_EXPORTED = "lgpd_data_exported"
    LGPD_DATA_DELETED = "lgpd_data_deleted"
    LGPD_CONSENT_GIVEN = "lgpd_consent_given"
    LGPD_CONSENT_REVOKED = "lgpd_consent_revoked"
    
    # Auth
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    
    # Admin
    TENANT_CREATED = "tenant_created"
    TENANT_UPDATED = "tenant_updated"
    TENANT_DEACTIVATED = "tenant_deactivated"
    USER_CREATED = "user_created"
    SETTINGS_CHANGED = "settings_changed"
    PLAN_CHANGED = "plan_changed"


class AuditSeverity(str, Enum):
    """Severidade do evento."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogEntry:
    """Entrada de log de auditoria."""
    
    def __init__(
        self,
        action: AuditAction,
        severity: AuditSeverity = AuditSeverity.INFO,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        lead_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        message: str = "",
    ):
        self.action = action
        self.severity = severity
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.lead_id = lead_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.old_value = old_value
        self.new_value = new_value
        self.metadata = metadata or {}
        self.message = message
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "action": self.action.value if isinstance(self.action, AuditAction) else self.action,
            "severity": self.severity.value if isinstance(self.severity, AuditSeverity) else self.severity,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "lead_id": self.lead_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "old_value": str(self.old_value) if self.old_value else None,
            "new_value": str(self.new_value) if self.new_value else None,
            "metadata": self.metadata,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


# Buffer de logs em memória (para batch insert)
_log_buffer: list[AuditLogEntry] = []
_buffer_max_size = 50


async def log_audit(
    db: AsyncSession,
    action: AuditAction,
    severity: AuditSeverity = AuditSeverity.INFO,
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
    message: str = "",
    flush_immediately: bool = False,
) -> None:
    """
    Registra evento de auditoria.
    
    Por padrão, eventos são bufferizados e inseridos em batch.
    Use flush_immediately=True para eventos críticos.
    """
    from src.domain.entities.audit_log import AuditLog
    
    entry = AuditLogEntry(
        action=action,
        severity=severity,
        tenant_id=tenant_id,
        user_id=user_id,
        lead_id=lead_id,
        ip_address=ip_address,
        resource_type=resource_type,
        resource_id=resource_id,
        old_value=old_value,
        new_value=new_value,
        metadata=metadata,
        message=message,
    )
    
    # Para eventos críticos, insere imediatamente
    if flush_immediately or severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
        log_record = AuditLog(
            action=entry.action.value if isinstance(entry.action, AuditAction) else entry.action,
            severity=entry.severity.value if isinstance(entry.severity, AuditSeverity) else entry.severity,
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            lead_id=entry.lead_id,
            ip_address=entry.ip_address,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            old_value=str(entry.old_value) if entry.old_value else None,
            new_value=str(entry.new_value) if entry.new_value else None,
            extra_data=entry.metadata,
            message=entry.message,
        )
        db.add(log_record)
        await db.flush()
        return
    
    # Adiciona ao buffer
    global _log_buffer
    _log_buffer.append(entry)
    
    # Flush se buffer cheio
    if len(_log_buffer) >= _buffer_max_size:
        await flush_audit_buffer(db)


async def flush_audit_buffer(db: AsyncSession) -> int:
    """
    Persiste todos os logs do buffer no banco.
    
    Returns:
        Número de logs persistidos
    """
    from src.domain.entities.audit_log import AuditLog
    
    global _log_buffer
    
    if not _log_buffer:
        return 0
    
    count = len(_log_buffer)
    
    for entry in _log_buffer:
        log_record = AuditLog(
            action=entry.action.value if isinstance(entry.action, AuditAction) else entry.action,
            severity=entry.severity.value if isinstance(entry.severity, AuditSeverity) else entry.severity,
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            lead_id=entry.lead_id,
            ip_address=entry.ip_address,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            old_value=str(entry.old_value) if entry.old_value else None,
            new_value=str(entry.new_value) if entry.new_value else None,
            extra_data=entry.metadata,
            message=entry.message,
        )
        db.add(log_record)
    
    _log_buffer = []
    await db.flush()
    
    return count


# =============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

async def log_message_received(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
    content_preview: str,
    channel: str = "whatsapp",
    ip_address: str = None,
) -> None:
    """Log de mensagem recebida."""
    await log_audit(
        db=db,
        action=AuditAction.MESSAGE_RECEIVED,
        severity=AuditSeverity.INFO,
        tenant_id=tenant_id,
        lead_id=lead_id,
        metadata={
            "channel": channel,
            "content_length": len(content_preview),
            "content_preview": content_preview[:100] + "..." if len(content_preview) > 100 else content_preview,
        },
        message=f"Mensagem recebida via {channel}",
    )


async def log_security_threat(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
    threat_type: str,
    threat_level: str,
    content_preview: str,
    matched_pattern: str = None,
    ip_address: str = None,
    blocked: bool = True,
) -> None:
    """Log de ameaça de segurança detectada."""
    severity = AuditSeverity.CRITICAL if blocked else AuditSeverity.WARNING
    
    await log_audit(
        db=db,
        action=AuditAction.SECURITY_THREAT_DETECTED,
        severity=severity,
        tenant_id=tenant_id,
        lead_id=lead_id,
        ip_address=ip_address,
        metadata={
            "threat_type": threat_type,
            "threat_level": threat_level,
            "matched_pattern": matched_pattern,
            "content_preview": content_preview[:200] if content_preview else None,
            "blocked": blocked,
        },
        message=f"Ameaça detectada: {threat_type} (nível: {threat_level})",
        flush_immediately=True,  # Sempre salva imediatamente
    )


async def log_lgpd_action(
    db: AsyncSession,
    action: AuditAction,
    tenant_id: int,
    lead_id: int,
    user_id: int = None,
    ip_address: str = None,
    details: str = "",
) -> None:
    """Log de ação LGPD."""
    await log_audit(
        db=db,
        action=action,
        severity=AuditSeverity.INFO,
        tenant_id=tenant_id,
        lead_id=lead_id,
        user_id=user_id,
        ip_address=ip_address,
        message=details,
        flush_immediately=True,  # LGPD sempre salva imediatamente
    )


async def log_ai_action(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
    action_type: str,
    details: dict = None,
) -> None:
    """Log de ação da IA."""
    action_map = {
        "response": AuditAction.AI_RESPONSE_GENERATED,
        "handoff": AuditAction.AI_HANDOFF_TRIGGERED,
        "qualification": AuditAction.AI_QUALIFICATION_CHANGED,
    }
    
    await log_audit(
        db=db,
        action=action_map.get(action_type, AuditAction.AI_RESPONSE_GENERATED),
        severity=AuditSeverity.INFO,
        tenant_id=tenant_id,
        lead_id=lead_id,
        metadata=details or {},
        message=f"IA: {action_type}",
    )


async def get_audit_logs(
    db: AsyncSession,
    tenant_id: int = None,
    lead_id: int = None,
    action: AuditAction = None,
    severity: AuditSeverity = None,
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 100,
) -> list:
    """
    Busca logs de auditoria com filtros.
    """
    from src.domain.entities.audit_log import AuditLog
    
    query = select(AuditLog)
    
    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)
    if lead_id:
        query = query.where(AuditLog.lead_id == lead_id)
    if action:
        query = query.where(AuditLog.action == action.value)
    if severity:
        query = query.where(AuditLog.severity == severity.value)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()