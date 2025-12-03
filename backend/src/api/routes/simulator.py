"""
ROTAS: SIMULADOR DE CONVERSA
=============================

Endpoint para testar a IA sem criar leads reais.
Permite que gestores testem as configurações antes de ativar.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List

from src.infrastructure.database import get_db
from src.api.dependencies import get_current_user
from src.domain.entities import User, Tenant
from src.infrastructure.services import (
    chat_completion,
    detect_sentiment,
    calculate_typing_delay,
)
from src.domain.prompts import get_niche_config

router = APIRouter(prefix="/simulator", tags=["Simulador"])


class SimulatorMessage(BaseModel):
    role: str
    content: str


class SimulatorChatRequest(BaseModel):
    message: str
    session_id: str
    history: Optional[List[SimulatorMessage]] = []


class SimulatorChatResponse(BaseModel):
    reply: str
    typing_delay: float
    sentiment: str
    qualification_hint: str


@router.post("/chat", response_model=SimulatorChatResponse)
async def simulator_chat(
    payload: SimulatorChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simula uma conversa com a IA usando as configurações do tenant.
    
    Não cria leads nem salva mensagens - apenas para teste.
    """
    
    # Buscar tenant do usuário
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    settings = tenant.settings or {}
    
    # Detectar sentimento da mensagem
    sentiment_result = await detect_sentiment(payload.message)
    sentiment = sentiment_result.get("sentiment", "neutral")
    
    # Buscar template do nicho
    niche = settings.get("niche", "services")
    tone = settings.get("tone", "cordial")
    niche_config = get_niche_config(niche)
    
    # Montar histórico de mensagens para contexto
    messages_for_ai = []
    for msg in payload.history:
        messages_for_ai.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Adicionar mensagem atual
    messages_for_ai.append({
        "role": "user",
        "content": payload.message
    })
    
    # Montar system prompt
    company_name = settings.get("company_name", tenant.name)
    
    # FAQ se habilitado
    faq_text = ""
    if settings.get("faq_enabled") and settings.get("faq_items"):
        faq_text = "\n\nPerguntas Frequentes (FAQ):\n"
        for item in settings.get("faq_items", []):
            faq_text += f"P: {item['question']}\nR: {item['answer']}\n\n"
    
    # Escopo se habilitado
    scope_text = ""
    if settings.get("scope_enabled") and settings.get("scope_description"):
        scope_text = f"\n\nEscopo do atendimento: {settings.get('scope_description')}"
        if settings.get("out_of_scope_message"):
            scope_text += f"\nSe perguntarem sobre assuntos fora do escopo, responda: {settings.get('out_of_scope_message')}"
    
    # Perguntas personalizadas
    questions_text = ""
    if settings.get("custom_questions"):
        questions_text = "\n\nPerguntas que você deve fazer durante a conversa:\n"
        for q in settings.get("custom_questions", []):
            questions_text += f"- {q}\n"
    
    # Regras personalizadas
    rules_text = ""
    if settings.get("custom_rules"):
        rules_text = "\n\nRegras importantes:\n"
        for r in settings.get("custom_rules", []):
            rules_text += f"- {r}\n"
    
    # Ajuste de tom baseado em sentimento
    sentiment_instruction = ""
    if sentiment == "frustrated":
        sentiment_instruction = "\n\n⚠️ O cliente parece frustrado. Seja empático, peça desculpas se necessário e tente resolver rapidamente."
    elif sentiment == "urgent":
        sentiment_instruction = "\n\n⚡ O cliente parece com urgência. Seja direto e objetivo."
    elif sentiment == "excited":
        sentiment_instruction = "\n\n🎉 O cliente parece animado/interessado. Aproveite o momento para avançar na qualificação."
    
    # Montar prompt completo
    system_prompt = f"""Você é um assistente de atendimento da empresa {company_name}.

{niche_config.prompt_template if niche_config else "Atenda o cliente de forma profissional e ajude-o com suas dúvidas."}

Tom de voz: {tone}
{faq_text}
{scope_text}
{questions_text}
{rules_text}
{sentiment_instruction}

IMPORTANTE:
- Esta é uma simulação de teste. Responda como faria com um cliente real.
- Use emojis moderadamente se o tom for cordial ou informal.
- Seja natural e humano na conversa.
- Faça perguntas para qualificar o lead.
"""

    try:
        # Montar mensagens para a IA (system prompt + histórico + mensagem atual)
        ai_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages_for_ai
        
        # Gerar resposta da IA
        result = await chat_completion(
            messages=ai_messages,
            max_tokens=500,
        )
        
        ai_response = result["content"]
        
        # Calcular delay de digitação
        typing_delay = calculate_typing_delay(len(ai_response))
        
        # Determinar hint de qualificação baseado na conversa
        qualification_hint = analyze_qualification(payload.message, ai_response, payload.history)
        
        return SimulatorChatResponse(
            reply=ai_response,
            typing_delay=typing_delay,
            sentiment=sentiment,
            qualification_hint=qualification_hint,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao gerar resposta: {str(e)}"
        )


def analyze_qualification(user_message: str, ai_response: str, history: List[SimulatorMessage]) -> str:
    """
    Analisa a conversa e dá uma dica de como o lead seria qualificado.
    """
    message_lower = user_message.lower()
    
    # Sinais de lead quente
    hot_signals = [
        "quero comprar", "quero fechar", "como faço para", "qual o valor",
        "aceita cartão", "posso pagar", "tem disponível", "quando posso",
        "vou querer", "pode reservar", "fecha negócio", "quero agendar",
        "visitar", "conhecer pessoalmente"
    ]
    
    # Sinais de lead morno
    warm_signals = [
        "quanto custa", "qual o preço", "tem financiamento", "como funciona",
        "quais as opções", "me interessei", "gostaria de saber", "pode me explicar",
        "estou pesquisando", "estou procurando"
    ]
    
    # Verificar sinais
    for signal in hot_signals:
        if signal in message_lower:
            return "🔥 Lead QUENTE - Cliente demonstra intenção de compra"
    
    for signal in warm_signals:
        if signal in message_lower:
            return "🟡 Lead MORNO - Cliente demonstra interesse"
    
    # Verificar histórico
    total_messages = len(history) + 1
    if total_messages >= 5:
        return "🟡 Lead MORNO - Conversa em andamento"
    
    return "🔵 Lead FRIO - Início da conversa"


@router.get("/suggestions")
async def get_simulator_suggestions():
    """
    Retorna sugestões de mensagens para testar o simulador.
    """
    return {
        "suggestions": [
            {
                "category": "Primeira mensagem",
                "messages": [
                    "Oi, vi o anúncio de vocês",
                    "Olá, gostaria de informações",
                    "Boa tarde! Vocês trabalham com o quê?",
                ]
            },
            {
                "category": "Interesse",
                "messages": [
                    "Quanto custa?",
                    "Quais as formas de pagamento?",
                    "Vocês fazem financiamento?",
                    "Tem disponibilidade para essa semana?",
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
                "category": "Lead Quente",
                "messages": [
                    "Quero fechar! Como faço?",
                    "Aceita cartão de crédito?",
                    "Posso visitar hoje?",
                    "Pode reservar pra mim?",
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
    }