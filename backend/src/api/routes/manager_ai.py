from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Any

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, User
from src.api.dependencies import get_current_user, get_current_tenant
from src.infrastructure.services.manager_copilot_service import ManagerCopilotService

router = APIRouter(prefix="/manager/copilot", tags=["Manager AI"])

class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = ""
    # Campos opcionais para compatibilidade futura com histórico avançado
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    history: List[ChatMessage]

class QueryResponse(BaseModel):
    response: str

@router.post("/chat", response_model=QueryResponse)
async def chat_with_jarvis(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint do 'Jarvis' (Manager Copilot).
    Recebe pergunta do gestor e retorna resposta baseada em dados do CRM.
    """
    
    # Apenas gestores e admins
    if user.role not in ["superadmin", "admin", "gestor"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a gestores.")

    service = ManagerCopilotService(db, tenant, user)
    
    # Converte history Pydantic para dicts limpos
    history_dicts = []
    for m in request.history:
        msg = {"role": m.role, "content": m.content or ""}
        # Se tiver tool_calls no futuro, adicionar aqui
        history_dicts.append(msg)
    
    try:
        response_text = await service.process_query(request.query, history_dicts)
        return {"response": response_text}
    except Exception as e:
        # Logar erro real
        from logging import getLogger
        logger = getLogger(__name__)
        logger.error(f"Erro no Jarvis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar sua pergunta. Tente novamente.")
