"""
ROTAS: SIMULADOR DE CONVERSA (VERSÃO UNIFICADA)
=================================================

Endpoint para testar a IA sem criar leads reais.
Permite que gestores testem as configurações antes de ativar.

IMPORTANTE: Este simulador usa EXATAMENTE a mesma lógica de
construção de prompt que o process_message em produção.

Isso garante que o teste seja fiel ao comportamento real.

ÚLTIMA ATUALIZAÇÃO: 2025-01-XX
VERSÃO: 4.0 (Unificada com produção)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import logging

from src.infrastructure.database import get_db
from src.api.dependencies import get_current_user
from src.domain.entities import User, Tenant, Product
from src.infrastructure.services import (
    chat_completion,
    calculate_typing_delay,
)
from src.infrastructure.services.openai_service import detect_sentiment

# ============================================================================
# IMPORTA O MÓDULO CENTRALIZADO - FONTE ÚNICA DE VERDADE
# ============================================================================
# ✅ CORRETO - imports reais
from src.application.services.ai_context_builder import (
    AIContext,
    LeadContext,
    ProductContext,
    ImovelPortalContext,
    migrate_settings_if_needed,
    extract_ai_context,
    build_complete_prompt,
    product_to_context,
    analyze_qualification_from_message,
    detect_hot_lead_signals,
)

# Para detecção de imóvel de portal (se disponível)
try:
    from src.infrastructure.services.property_lookup_service import (
        buscar_imovel_na_mensagem,
        extrair_codigo_imovel,
    )
    HAS_PROPERTY_LOOKUP = True
except ImportError:
    HAS_PROPERTY_LOOKUP = False
    buscar_imovel_na_mensagem = None
    extrair_codigo_imovel = None

logger = logging.getLogger(__name__)

# Nichos que podem ter empreendimentos
NICHOS_IMOBILIARIOS = ["realestate", "imobiliaria", "real_estate", "imobiliario"]

router = APIRouter(prefix="/simulator", tags=["Simulador"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SimulatorMessage(BaseModel):
    role: str
    content: str


class SimulatorChatRequest(BaseModel):
    message: str
    session_id: str
    history: Optional[List[SimulatorMessage]] = []
    # Contexto simulado do lead (opcional)
    simulated_lead_name: Optional[str] = None
    simulated_lead_phone: Optional[str] = "5511999999999"


class SimulatorChatResponse(BaseModel):
    reply: str
    typing_delay: float
    sentiment: str
    qualification_hint: str
    # Metadados do prompt (para debug)
    prompt_length: int = 0
    has_identity: bool = False
    has_product: bool = False
    has_imovel_portal: bool = False
    hot_lead_detected: bool = False
    hot_lead_signal: Optional[str] = None


class SimulatorDebugResponse(BaseModel):
    tenant_name: str
    tenant_slug: str
    company_name: str
    niche: str
    tone: str
    has_identity: bool
    identity_fields: dict
    faq_count: int
    scope_description: bool
    products_count: int = 0
    prompt_preview: str = ""


# =============================================================================
# HELPERS
# =============================================================================

async def detect_product_for_simulator(
    db: AsyncSession,
    tenant_id: int,
    message: str,
    history: List[SimulatorMessage],
) -> Optional[Product]:
    """
    Detecta produto na mensagem atual OU no histórico.
    """
    try:
        result = await db.execute(
            select(Product)
            .where(Product.tenant_id == tenant_id)
            .where(Product.active == True)
            .order_by(Product.priority.desc())
        )
        products = result.scalars().all()
        
        if not products:
            return None
        
        # Verifica na mensagem atual
        message_lower = message.lower()
        for prod in products:
            if prod.triggers:
                for trigger in prod.triggers:
                    if trigger.lower() in message_lower:
                        logger.info(f"📦 Simulador - Produto detectado: {prod.name}")
                        return prod
        
        # Verifica no histórico
        for msg in history:
            msg_lower = msg.content.lower()
            for prod in products:
                if prod.triggers:
                    for trigger in prod.triggers:
                        if trigger.lower() in msg_lower:
                            logger.info(f"📦 Simulador - Produto no histórico: {prod.name}")
                            return prod
        
        return None
    except Exception as e:
        logger.error(f"Erro detectando produto no simulador: {e}")
        return None


def detect_imovel_portal_for_simulator(
    message: str,
    history: List[SimulatorMessage],
) -> Optional[dict]:
    """
    Detecta imóvel de portal na mensagem ou histórico.
    
    NOTA: Usa a mesma função do process_message.
    """
    if not HAS_PROPERTY_LOOKUP or not buscar_imovel_na_mensagem:
        return None
    
    try:
        # Tenta na mensagem atual
        imovel = buscar_imovel_na_mensagem(message)
        if imovel:
            logger.info(f"🏠 Simulador - Imóvel detectado: {imovel.get('codigo')}")
            return imovel
        
        # Tenta no histórico
        for msg in reversed(history):
            if msg.role == "user":
                imovel = buscar_imovel_na_mensagem(msg.content)
                if imovel:
                    logger.info(f"🏠 Simulador - Imóvel no histórico: {imovel.get('codigo')}")
                    return imovel
        
        return None
    except Exception as e:
        logger.error(f"Erro detectando imóvel no simulador: {e}")
        return None


# =============================================================================
# ENDPOINT PRINCIPAL
# =============================================================================

@router.post("/chat", response_model=SimulatorChatResponse)
async def simulator_chat(
    payload: SimulatorChatRequest,
    target_tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simula uma conversa com a IA usando as configurações do tenant.
    
    Superadmin pode passar target_tenant_id para gerenciar outro cliente.
    """
    
    # 1. BUSCA TENANT
    active_tenant_id = current_user.tenant_id
    
    # Se for superadmin e tiver target_tenant_id, troca o tenant de contexto
    if target_tenant_id and current_user.role == "superadmin":
        active_tenant_id = target_tenant_id
        logger.info(f"Superadmin {current_user.email} simulando para tenant_id {target_tenant_id}")

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == active_tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # =========================================================================
    # 2. EXTRAI CONTEXTO (MESMA LÓGICA DO PROCESS_MESSAGE)
    # =========================================================================
    raw_settings = tenant.settings or {}
    settings = migrate_settings_if_needed(raw_settings)
    ai_context = extract_ai_context(tenant.name, settings)
    
    logger.info(f"📱 Simulador - Tenant: {tenant.slug} | Company: {ai_context.company_name}")
    logger.info(f"📱 Simulador - Identity: {bool(ai_context.identity)} | Nicho: {ai_context.niche_id}")
    
    # =========================================================================
    # 3. DETECTA PRODUTO (MESMA LÓGICA DO PROCESS_MESSAGE)
    # =========================================================================
    product = await detect_product_for_simulator(
        db=db,
        tenant_id=tenant.id,
        message=payload.message,
        history=payload.history or [],
    )
    
    product_context = None
    if product:
        logger.info(f"📦 Simulador - Produto ativo: {product.name}")
        product_context = product_to_context(product)
        
        # Adiciona perguntas de qualificação do produto
        if product.qualification_questions:
            ai_context.custom_questions = (
                ai_context.custom_questions + 
                product.qualification_questions
            )
    
    # =========================================================================
    # 4. DETECTA IMÓVEL DE PORTAL (MESMA LÓGICA DO PROCESS_MESSAGE)
    # =========================================================================
    imovel_portal_context = None
    imovel_dict = detect_imovel_portal_for_simulator(
        message=payload.message,
        history=payload.history or [],
    )
    
    if imovel_dict:
        from src.application.services.ai_context_builder import imovel_dict_to_context
        imovel_portal_context = imovel_dict_to_context(imovel_dict)
        logger.info(f"🏠 Simulador - Imóvel portal: {imovel_portal_context.codigo}")
    
    # =========================================================================
    # 5. CRIA CONTEXTO SIMULADO DO LEAD
    # =========================================================================
    from datetime import datetime, timezone
    
    simulated_lead = LeadContext(
        lead_id=0,  # ID fictício
        name=payload.simulated_lead_name,
        phone=payload.simulated_lead_phone or "5511999999999",
        created_at=datetime.now(timezone.utc),
        message_count=len(payload.history or []) + 1,
        qualification="novo",
        status="em_atendimento",
    )
    
    # =========================================================================
    # 6. DETECTA SENTIMENTO
    # =========================================================================
    sentiment = "neutral"
    try:
        sentiment_result = await detect_sentiment(payload.message)
        sentiment = sentiment_result.get("sentiment", "neutral")
    except Exception as e:
        logger.error(f"Erro detectando sentimento: {e}")
    
    # =========================================================================
    # 7. DETECTA LEAD QUENTE (MESMA LÓGICA DO PROCESS_MESSAGE)
    # =========================================================================
    is_hot, hot_signal = detect_hot_lead_signals(payload.message)
    
    if is_hot:
        logger.warning(f"🔥 Simulador - Lead QUENTE detectado: {hot_signal}")
        simulated_lead.qualification = "quente"
    
    # =========================================================================
    # 8. CONSTRÓI PROMPT COMPLETO (USANDO FUNÇÃO CENTRALIZADA!)
    # =========================================================================
    prompt_result = build_complete_prompt(
        ai_context=ai_context,
        lead_context=simulated_lead,
        product=product_context,
        imovel_portal=imovel_portal_context,
        include_security=True,
        is_simulation=True,  # Adiciona aviso de simulação
    )
    
    logger.info(f"📝 Simulador - Prompt: {prompt_result.prompt_length} chars")
    if prompt_result.warnings:
        for warning in prompt_result.warnings:
            logger.warning(f"⚠️ Simulador - {warning}")
    
    # =========================================================================
    # 9. MONTA HISTÓRICO PARA A IA
    # =========================================================================
    messages_for_ai = [
        {"role": "system", "content": prompt_result.system_prompt}
    ]
    
    for msg in (payload.history or []):
        messages_for_ai.append({
            "role": msg.role,
            "content": msg.content
        })
    
    messages_for_ai.append({
        "role": "user",
        "content": payload.message
    })
    
    # =========================================================================
    # 10. CHAMA A IA
    # =========================================================================
    try:
        result = await chat_completion(
            messages=messages_for_ai,
            max_tokens=500,
            temperature=0.7,
        )
        
        ai_response = result["content"]
        
        # Calcula delay de digitação (mesma função do process_message)
        typing_delay = calculate_typing_delay(len(ai_response))
        
        # Analisa qualificação (para feedback visual)
        qualification_hint = analyze_qualification_from_message(
            user_message=payload.message,
            ai_response=ai_response,
            history=[{"role": m.role, "content": m.content} for m in (payload.history or [])]
        )
        
        # Se detectou lead quente, ajusta o hint
        if is_hot:
            qualification_hint = f"🔥 Lead QUENTE detectado! Sinal: {hot_signal}"
        
        return SimulatorChatResponse(
            reply=ai_response,
            typing_delay=typing_delay,
            sentiment=sentiment,
            qualification_hint=qualification_hint,
            prompt_length=prompt_result.prompt_length,
            has_identity=prompt_result.has_identity,
            has_product=prompt_result.has_product,
            has_imovel_portal=prompt_result.has_imovel_portal,
            hot_lead_detected=is_hot,
            hot_lead_signal=hot_signal,
        )
        
    except Exception as e:
        logger.error(f"Erro no simulador: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao gerar resposta: {str(e)}"
        )


# =============================================================================
# ENDPOINT DE DEBUG
# =============================================================================

@router.get("/debug-settings", response_model=SimulatorDebugResponse)
async def debug_settings(
    target_tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de debug para verificar se as configurações estão sendo carregadas.
    
    Mostra exatamente o que será usado para construir o prompt.
    """
    active_tenant_id = current_user.tenant_id
    if target_tenant_id and current_user.role == "superadmin":
        active_tenant_id = target_tenant_id

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == active_tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Extrai contexto
    raw_settings = tenant.settings or {}
    settings = migrate_settings_if_needed(raw_settings)
    ai_context = extract_ai_context(tenant.name, settings)
    
    identity = ai_context.identity or {}
    
    # Conta produtos
    prod_count = 0
    prod_result = await db.execute(
        select(Product)
        .where(Product.tenant_id == tenant.id)
        .where(Product.active == True)
    )
    prod_count = len(prod_result.scalars().all())
    
    # Gera preview do prompt
    prompt_result = build_complete_prompt(
        ai_context=ai_context,
        lead_context=None,
        product=None,
        imovel_portal=None,
        include_security=False,
        is_simulation=True,
    )
    
    # Pega só os primeiros 500 chars como preview
    prompt_preview = prompt_result.system_prompt[:500] + "..."
    
    return SimulatorDebugResponse(
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        company_name=ai_context.company_name,
        niche=ai_context.niche_id,
        tone=ai_context.tone,
        has_identity=bool(identity),
        identity_fields={
            "description": bool(identity.get("description")),
            "products_services": len(identity.get("products_services", [])),
            "not_offered": len(identity.get("not_offered", [])),
            "additional_context": bool(identity.get("additional_context")),
            "business_rules": len(identity.get("business_rules", [])),
            "differentials": len(identity.get("differentials", [])),
            "personality_traits": len(identity.get("tone_style", {}).get("personality_traits", [])),
        },
        faq_count=len(ai_context.faq_items),
        scope_description=bool(ai_context.scope_description),
        products_count=prod_count,
        prompt_preview=prompt_preview,
    )


# =============================================================================
# SUGESTÕES DE TESTE
# =============================================================================

@router.get("/suggestions")
async def get_simulator_suggestions(
    target_tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna sugestões de mensagens para testar o simulador.
    """
    # Busca tenant para personalizar sugestões
    active_tenant_id = current_user.tenant_id
    if target_tenant_id and current_user.role == "superadmin":
        active_tenant_id = target_tenant_id

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == active_tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    niche_id = "services"
    if tenant and tenant.settings:
        settings = migrate_settings_if_needed(tenant.settings)
        basic = settings.get("basic", {})
        niche_id = basic.get("niche") or settings.get("niche") or "services"
    
    # Sugestões base
    suggestions = [
        {
            "category": "Primeira mensagem",
            "messages": [
                "Oi, vi o anúncio de vocês",
                "Olá, gostaria de informações",
                "Boa tarde! Vocês trabalham com o quê?",
            ]
        },
        {
            "category": "Informações básicas",
            "messages": [
                "Qual o endereço de vocês?",
                "Qual o horário de funcionamento?",
                "Qual o telefone para contato?",
            ]
        },
        {
            "category": "Objeções",
            "messages": [
                "Tá muito caro",
                "Vou pensar e depois te falo",
                "Preciso falar com meu marido/esposa primeiro",
                "Achei o concorrente de vocês mais barato",
            ]
        },
        {
            "category": "Fora do escopo",
            "messages": [
                "Qual a capital da França?",
                "Me ajuda com meu dever de casa",
                "Conta uma piada",
            ]
        },
    ]
    
    # Sugestões específicas para nicho imobiliário
    if niche_id.lower() in NICHOS_IMOBILIARIOS:
        suggestions.insert(1, {
            "category": "🏠 Imobiliário - Interesse",
            "messages": [
                "Código 442025",
                "Quanto custa esse apartamento?",
                "Quero pra morar",
                "Quero pra investir",
                "Tem financiamento?",
                "Aceita FGTS?",
            ]
        })
        suggestions.insert(2, {
            "category": "🔥 Lead Quente (imobiliário)",
            "messages": [
                "Tenho dinheiro à vista",
                "Meu financiamento já foi aprovado",
                "Preciso mudar urgente, em 2 meses",
                "Quando posso visitar?",
                "Tenho 100 mil de entrada",
                "Quero fechar negócio",
            ]
        })
        
        # Busca produtos para sugerir gatilhos
        if tenant:
            prod_result = await db.execute(
                select(Product)
                .where(Product.tenant_id == tenant.id)
                .where(Product.active == True)
                .limit(5)
            )
            products = prod_result.scalars().all()
            
            if products:
                prod_messages = []
                for prod in products:
                    prod_messages.append(f"Interesse no {prod.name}")
                    if prod.triggers:
                        prod_messages.append(prod.triggers[0])
                
                suggestions.insert(3, {
                    "category": "📦 Produtos/Serviços",
                    "messages": prod_messages[:6]
                })
    else:
        # Sugestões genéricas para outros nichos
        suggestions.insert(1, {
            "category": "Interesse",
            "messages": [
                "Quanto custa?",
                "Quais as formas de pagamento?",
                "Tem disponibilidade para essa semana?",
            ]
        })
        suggestions.insert(2, {
            "category": "🔥 Lead Quente",
            "messages": [
                "Quero fechar! Como faço?",
                "Aceita cartão de crédito?",
                "Pode reservar pra mim?",
                "Posso ir aí hoje?",
            ]
        })
    
    return {"suggestions": suggestions, "niche": niche_id}


# =============================================================================
# ENDPOINT DE COMPARAÇÃO
# =============================================================================

@router.get("/prompt-comparison")
async def compare_prompts(
    test_message: str = "Oi, quero informações",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para comparar o prompt gerado pelo simulador.
    
    Útil para debug e para garantir que está igual ao de produção.
    """
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Extrai contexto
    settings = migrate_settings_if_needed(tenant.settings or {})
    ai_context = extract_ai_context(tenant.name, settings)
    
    # Lead simulado
    from datetime import datetime, timezone
    simulated_lead = LeadContext(
        lead_id=0,
        name=None,
        phone="5511999999999",
        created_at=datetime.now(timezone.utc),
        message_count=1,
        qualification="novo",
        status="em_atendimento",
    )
    
    # Detecta produto
    product = await detect_product_for_simulator(
        db=db,
        tenant_id=tenant.id,
        message=test_message,
        history=[],
    )
    
    product_context = None
    if product:
        product_context = product_to_context(product)
    
    # Constrói prompt
    prompt_result = build_complete_prompt(
        ai_context=ai_context,
        lead_context=simulated_lead,
        product=product_context,
        imovel_portal=None,
        include_security=True,
        is_simulation=True,
    )
    
    return {
        "test_message": test_message,
        "prompt_length": prompt_result.prompt_length,
        "has_identity": prompt_result.has_identity,
        "has_product": prompt_result.has_product,
        "has_imovel_portal": prompt_result.has_imovel_portal,
        "has_lead_context": prompt_result.has_lead_context,
        "warnings": prompt_result.warnings,
        "full_prompt": prompt_result.system_prompt,
    }