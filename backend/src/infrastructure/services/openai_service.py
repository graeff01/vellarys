"""
SERVIÇO OPENAI - VERSÃO INTELIGENTE
=====================================

Integração com a API da OpenAI.
Inclui:
- Memória de contexto (retomar conversa)
- Variação de respostas (menos robótico)
- Detecção de sentimento
- Sugestões proativas
"""

import json
import random
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from src.config import get_settings

settings = get_settings()

# Cliente OpenAI (singleton)
client = AsyncOpenAI(api_key=settings.openai_api_key)


# ============================================
# VARIAÇÕES DE SAUDAÇÕES E RESPOSTAS
# ============================================

GREETING_VARIATIONS = {
    "formal": [
        "Olá! Como posso ajudá-lo hoje?",
        "Olá! Em que posso ser útil?",
        "Bom dia! Como posso auxiliá-lo?",
        "Olá! Estou à disposição para ajudar.",
    ],
    "cordial": [
        "Oi! 😊 Como posso te ajudar?",
        "Olá! Tudo bem? Em que posso ajudar?",
        "Oi! Que bom falar com você! Como posso ajudar?",
        "Olá! 👋 Estou aqui pra te ajudar!",
    ],
    "informal": [
        "E aí! 👋 Como posso te ajudar?",
        "Oi! Tudo certo? Bora lá, como posso ajudar?",
        "Fala! 😄 O que você precisa?",
        "Oi oi! Como posso te ajudar hoje?",
    ],
}

ACKNOWLEDGMENT_VARIATIONS = [
    "Entendi!",
    "Perfeito!",
    "Ótimo!",
    "Certo!",
    "Legal!",
    "Beleza!",
    "Show!",
    "Anotado!",
]

TRANSITION_PHRASES = [
    "E me conta,",
    "Aproveitando,",
    "Só pra eu entender melhor,",
    "E outra coisa,",
    "Ah, e",
    "Deixa eu perguntar,",
]


def get_random_greeting(tone: str = "cordial") -> str:
    """Retorna uma saudação aleatória baseada no tom."""
    greetings = GREETING_VARIATIONS.get(tone, GREETING_VARIATIONS["cordial"])
    return random.choice(greetings)


def get_random_acknowledgment() -> str:
    """Retorna uma frase de reconhecimento aleatória."""
    return random.choice(ACKNOWLEDGMENT_VARIATIONS)


def get_random_transition() -> str:
    """Retorna uma frase de transição aleatória."""
    return random.choice(TRANSITION_PHRASES)


# ============================================
# FUNÇÕES PRINCIPAIS
# ============================================

async def chat_completion(
    messages: list[dict],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> dict:
    """
    Envia mensagens para OpenAI e retorna resposta.
    """
    response = await client.chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "content": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens if response.usage else 0
    }


async def detect_sentiment(message: str) -> dict:
    """
    Detecta o sentimento/humor do lead na mensagem.
    
    Returns:
        {
            "sentiment": "positive" | "neutral" | "negative" | "frustrated" | "excited",
            "confidence": 0.0-1.0,
            "tone_adjustment": "sugestão de ajuste no tom"
        }
    """
    
    # Análise rápida por palavras-chave (sem chamar API para economizar)
    message_lower = message.lower()
    
    # Sinais de frustração/irritação
    frustrated_signals = [
        "demora", "lento", "ninguém responde", "péssimo", "horrível",
        "não funciona", "problema", "reclamação", "absurdo", "vergonha",
        "desisto", "cancelar", "nunca mais", "pior", "raiva", "irritado",
        "cansado de", "toda vez", "sempre isso", "!!", "???",
    ]
    
    # Sinais de pressa/urgência
    urgent_signals = [
        "urgente", "rápido", "agora", "hoje", "preciso logo",
        "não posso esperar", "emergência", "prazo", "deadline",
    ]
    
    # Sinais positivos/animação
    positive_signals = [
        "obrigado", "obrigada", "perfeito", "ótimo", "excelente",
        "maravilha", "adorei", "amei", "show", "top", "😊", "😄",
        "👍", "🙏", "❤️", "muito bom", "gostei",
    ]
    
    # Sinais de interesse forte
    excited_signals = [
        "quero", "preciso", "vamos fechar", "quando começa",
        "como faço", "me inscreve", "reserva", "!!",
    ]
    
    # Pontua cada categoria
    frustrated_score = sum(1 for s in frustrated_signals if s in message_lower)
    urgent_score = sum(1 for s in urgent_signals if s in message_lower)
    positive_score = sum(1 for s in positive_signals if s in message_lower)
    excited_score = sum(1 for s in excited_signals if s in message_lower)
    
    # Determina sentimento predominante
    if frustrated_score >= 2:
        return {
            "sentiment": "frustrated",
            "confidence": min(0.9, 0.5 + frustrated_score * 0.1),
            "tone_adjustment": "Seja empático, peça desculpas se necessário, resolva o problema rapidamente. Evite frases genéricas.",
            "detected_signals": "frustração/irritação"
        }
    elif urgent_score >= 1:
        return {
            "sentiment": "urgent",
            "confidence": min(0.9, 0.6 + urgent_score * 0.1),
            "tone_adjustment": "Seja direto e objetivo. Priorize resolver a urgência. Evite perguntas desnecessárias.",
            "detected_signals": "urgência/pressa"
        }
    elif excited_score >= 1 and positive_score >= 1:
        return {
            "sentiment": "excited",
            "confidence": 0.8,
            "tone_adjustment": "Mantenha a energia! Facilite o fechamento. Seja entusiasmado também.",
            "detected_signals": "animação/interesse forte"
        }
    elif positive_score >= 1:
        return {
            "sentiment": "positive",
            "confidence": min(0.9, 0.6 + positive_score * 0.1),
            "tone_adjustment": "Continue positivo. Bom momento para avançar na qualificação.",
            "detected_signals": "satisfação/positividade"
        }
    else:
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "tone_adjustment": None,
            "detected_signals": None
        }


async def generate_context_aware_response(
    messages: list[dict],
    lead_data: dict,
    sentiment: dict,
    tone: str = "cordial",
    is_returning_lead: bool = False,
    hours_since_last_message: float = 0,
    previous_summary: str = None,
) -> dict:
    """
    Gera resposta consciente do contexto, sentimento e histórico.
    
    Args:
        messages: Histórico de mensagens
        lead_data: Dados extraídos do lead
        sentiment: Resultado da detecção de sentimento
        tone: Tom de voz configurado
        is_returning_lead: Se o lead está retornando após um tempo
        hours_since_last_message: Horas desde última mensagem
        previous_summary: Resumo da conversa anterior (se lead retornando)
    
    Returns:
        {
            "content": "resposta da IA",
            "tokens_used": int,
            "context_used": "descrição do contexto aplicado"
        }
    """
    
    context_instructions = []
    
    # 1. Ajuste por sentimento
    if sentiment.get("tone_adjustment"):
        context_instructions.append(f"AJUSTE DE TOM: {sentiment['tone_adjustment']}")
    
    # 2. Lead retornando após tempo
    if is_returning_lead and hours_since_last_message > 24:
        days = int(hours_since_last_message / 24)
        
        if previous_summary:
            context_instructions.append(f"""
LEAD RETORNANDO APÓS {days} DIA(S):
- Cumprimente de forma acolhedora
- Mencione brevemente o que conversaram antes: "{previous_summary}"
- Pergunte se ainda tem interesse ou se a situação mudou
- NÃO repita perguntas que já foram respondidas
- Exemplo: "Oi [nome]! Que bom te ver de volta! Da última vez você estava interessado em [X]. Ainda está procurando?"
""")
        else:
            context_instructions.append(f"""
LEAD RETORNANDO APÓS {days} DIA(S):
- Cumprimente de forma acolhedora
- Mencione que já conversaram antes
- Pergunte como pode ajudar
- Exemplo: "Oi! Tudo bem? A gente já conversou há alguns dias. Como posso te ajudar agora?"
""")
    
    # 3. Contexto do lead para personalização
    if lead_data:
        personalization = []
        
        if lead_data.get("name"):
            personalization.append(f"Use o nome '{lead_data['name']}' ocasionalmente (não toda mensagem)")
        
        if lead_data.get("family_situation"):
            personalization.append(f"Situação familiar: {lead_data['family_situation']} - adapte sugestões")
        
        if lead_data.get("work_info"):
            personalization.append(f"Trabalho: {lead_data['work_info']} - considere na abordagem")
        
        if lead_data.get("budget_range"):
            personalization.append(f"Orçamento: {lead_data['budget_range']} - respeite a faixa")
        
        if lead_data.get("urgency_level"):
            personalization.append(f"Urgência: {lead_data['urgency_level']} - adapte o ritmo")
        
        if lead_data.get("preferences"):
            prefs = lead_data['preferences']
            if isinstance(prefs, list):
                prefs = ", ".join(prefs)
            personalization.append(f"Preferências: {prefs} - use nas sugestões")
        
        if lead_data.get("pain_points"):
            pains = lead_data['pain_points']
            if isinstance(pains, list):
                pains = ", ".join(pains)
            personalization.append(f"Dores/Problemas: {pains} - mostre empatia e soluções")
        
        if lead_data.get("objections"):
            objs = lead_data['objections']
            if isinstance(objs, list):
                objs = ", ".join(objs)
            personalization.append(f"⚠️ OBJEÇÕES ANTERIORES: {objs} - contorne com argumentos")
        
        if lead_data.get("buying_signals"):
            signals = lead_data['buying_signals']
            if isinstance(signals, list):
                signals = ", ".join(signals)
            personalization.append(f"🔥 SINAIS DE COMPRA: {signals} - ACELERE O FECHAMENTO!")
        
        if personalization:
            context_instructions.append("PERSONALIZAÇÃO (use naturalmente):\n" + "\n".join(f"- {p}" for p in personalization))
    
    # 4. Instruções de variação
    context_instructions.append(f"""
VARIAÇÃO DE LINGUAGEM:
- NÃO repita as mesmas frases de mensagens anteriores
- Varie as saudações e transições
- Use linguagem natural, não robótica
- Tom configurado: {tone}
- Evite começar todas as mensagens com "Olá" ou "Oi"
""")
    
    # Monta mensagem de contexto
    if context_instructions:
        context_message = {
            "role": "system",
            "content": "INSTRUÇÕES DE CONTEXTO PARA ESTA RESPOSTA:\n\n" + "\n\n".join(context_instructions)
        }
        # Insere após o system prompt principal
        messages_with_context = [messages[0], context_message] + messages[1:]
    else:
        messages_with_context = messages
    
    # Chama a API
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages_with_context,
        temperature=0.75,  # Um pouco mais criativo
        max_tokens=500,
    )
    
    return {
        "content": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens if response.usage else 0,
        "context_used": ", ".join([
            sentiment.get("detected_signals") or "neutral",
            "returning_lead" if is_returning_lead else "new_conversation",
            f"personalized:{len(lead_data or {})}_fields"
        ])
    }


async def generate_conversation_summary(conversation: list[dict]) -> str:
    """
    Gera um resumo curto da conversa para uso em retorno do lead.
    
    Returns:
        Resumo em 1-2 frases do que foi discutido
    """
    
    if len(conversation) < 2:
        return None
    
    summary_prompt = f"""Resuma esta conversa em 1-2 frases curtas, focando no que o cliente estava buscando.

CONVERSA:
{json.dumps(conversation[-10:], ensure_ascii=False, indent=2)}

Formato: Uma frase direta como "Você estava interessado em [X] e perguntou sobre [Y]"
NÃO inclua saudações ou formalidades.
Máximo 100 caracteres.

RESUMO:"""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": summary_prompt}],
        temperature=0.3,
        max_tokens=100,
    )
    
    return response.choices[0].message.content.strip()


async def extract_lead_data(
    conversation: list[dict],
    required_fields: list[str],
    optional_fields: list[str],
) -> dict:
    """
    Extrai dados estruturados do lead a partir da conversa.
    Versão expandida com contexto completo.
    """

    all_fields = required_fields + optional_fields

    extraction_prompt = f"""Analise a conversa abaixo e extraia TODAS as informações do cliente.

CAMPOS BÁSICOS A EXTRAIR:
{json.dumps(all_fields, ensure_ascii=False)}

CONTEXTO ADICIONAL A EXTRAIR (se mencionado):
- family_situation: Situação familiar (solteiro, casado, tem filhos, quantos filhos, etc)
- work_info: Informações sobre trabalho (onde trabalha, profissão, região do trabalho)
- budget_range: Faixa de orçamento ou capacidade de pagamento
- urgency_level: Nível de urgência (imediato, essa semana, esse mês, pesquisando, sem pressa)
- preferences: Lista de preferências específicas mencionadas
- pain_points: Problemas ou dores que o cliente mencionou
- objections: Objeções ou preocupações levantadas (preço alto, precisa pensar, etc)
- decision_factors: O que é importante para a decisão (localização, preço, qualidade, etc)
- timeline: Prazo ou data mencionada
- previous_experience: Experiência anterior com produto/serviço similar
- competitor_mentions: Se mencionou concorrentes ou alternativas
- buying_signals: Sinais de compra detectados (perguntou forma de pagamento, disponibilidade, etc)
- communication_style: Estilo de comunicação do cliente (direto, detalhista, informal, formal)

REGRAS:
- Se a informação não foi mencionada, use null
- Para listas (preferences, pain_points, etc), use array de strings
- Para buying_signals, liste frases que indicam intenção de compra
- Seja específico e extraia o máximo de contexto possível
- Retorne APENAS o JSON, sem explicações

CONVERSA:
{json.dumps(conversation, ensure_ascii=False, indent=2)}

JSON:"""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": extraction_prompt}],
        temperature=0.1,
        max_tokens=800,
    )

    try:
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except (json.JSONDecodeError, IndexError):
        return {}


async def qualify_lead(
    conversation: list[dict],
    extracted_data: dict,
    qualification_rules: dict,
) -> dict:
    """
    Qualifica o lead como hot/warm/cold baseado na conversa.
    Versão melhorada com análise de sinais de compra.
    """

    qualification_prompt = f"""Analise a conversa e dados do lead para qualificá-lo.

REGRAS DE QUALIFICAÇÃO:
- HOT (pronto para fechar): {', '.join(qualification_rules.get('hot', []))}
- WARM (interessado mas não urgente): {', '.join(qualification_rules.get('warm', []))}
- COLD (apenas pesquisando): {', '.join(qualification_rules.get('cold', []))}

SINAIS DE COMPRA FORTES (indicam lead HOT):
- Pergunta sobre formas de pagamento ou parcelamento
- Pergunta sobre disponibilidade imediata
- Menciona prazo específico ("preciso para", "até dia X")
- Já pesquisou concorrentes e está comparando
- Pergunta sobre próximos passos para fechar
- Demonstra urgência ou necessidade clara
- Já tem orçamento definido

SINAIS DE OBJEÇÃO (podem indicar lead WARM ou COLD):
- "Vou pensar" - pode ser warm se outros sinais positivos
- "Tá caro" - warm se continua interessado
- "Depois eu vejo" - provavelmente cold
- "Só pesquisando" - cold

DADOS COLETADOS:
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

CONVERSA:
{json.dumps(conversation, ensure_ascii=False, indent=2)}

Responda APENAS em JSON:
{{
  "qualification": "hot|warm|cold",
  "confidence": 0.0-1.0,
  "reason": "motivo da qualificação",
  "buying_signals_found": ["lista de sinais de compra detectados"],
  "objections_found": ["lista de objeções detectadas"],
  "recommended_action": "ação recomendada para o vendedor",
  "next_best_question": "próxima pergunta que a IA deveria fazer para avançar"
}}

JSON:"""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": qualification_prompt}],
        temperature=0.2,
        max_tokens=400,
    )

    try:
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except (json.JSONDecodeError, IndexError):
        return {"qualification": "cold", "confidence": 0.5, "reason": "Não foi possível qualificar"}


async def generate_lead_summary(
    conversation: list[dict],
    extracted_data: dict,
    qualification: dict,
) -> str:
    """
    Gera um resumo estruturado do lead para o gestor.
    Versão melhorada com contexto completo.
    """

    summary_prompt = f"""Gere um resumo COMPLETO e ESTRUTURADO deste lead para a equipe comercial.

DADOS DO LEAD:
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

QUALIFICAÇÃO: {qualification.get('qualification', 'N/A')} ({qualification.get('confidence', 0)*100:.0f}% confiança)
MOTIVO: {qualification.get('reason', '')}
SINAIS DE COMPRA: {', '.join(qualification.get('buying_signals_found', []))}
OBJEÇÕES: {', '.join(qualification.get('objections_found', []))}
AÇÃO RECOMENDADA: {qualification.get('recommended_action', '')}

CONVERSA:
{json.dumps(conversation[-8:], ensure_ascii=False, indent=2)}

Formato do resumo:
📋 RESUMO DO LEAD
- O que busca:
- Situação:
- Urgência:
- Orçamento:
- Objeções a contornar:
- Pontos a destacar na abordagem:
- Próximo passo recomendado:

Seja direto e útil para o vendedor fechar a venda.

RESUMO:"""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": summary_prompt}],
        temperature=0.3,
        max_tokens=400,
    )

    return response.choices[0].message.content.strip()


async def generate_proactive_suggestions(
    conversation: list[dict],
    extracted_data: dict,
    niche: str,
) -> dict:
    """
    Gera sugestões proativas baseadas no contexto do lead.

    Returns:
        {
            "suggestions": ["sugestão 1", "sugestão 2"],
            "urgency_message": "mensagem de urgência se aplicável",
            "next_step": "próximo passo recomendado",
            "personalized_pitch": "argumento personalizado"
        }
    """

    suggestion_prompt = f"""Com base no contexto do lead, gere sugestões proativas para a IA usar na conversa.

NICHO: {niche}

DADOS DO LEAD:
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

CONVERSA RECENTE:
{json.dumps(conversation[-6:], ensure_ascii=False, indent=2)}

Gere em JSON:
{{
    "suggestions": ["até 3 sugestões específicas baseadas no perfil do lead"],
    "urgency_message": "mensagem de urgência se o lead demonstrou interesse (ou null)",
    "next_step": "próximo passo natural da conversa",
    "personalized_pitch": "argumento de venda personalizado para este lead específico",
    "objection_responses": {{"objeção": "resposta para contornar"}}
}}

REGRAS:
- Sugestões devem ser específicas para o perfil (ex: se tem filhos, sugira opções family-friendly)
- Urgency só se houver motivo real (disponibilidade limitada, promoção, etc)
- Personalized pitch deve usar informações do lead (trabalho, família, preferências)
- Seja natural, não agressivo

JSON:"""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": suggestion_prompt}],
        temperature=0.4,
        max_tokens=500,
    )

    try:
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except (json.JSONDecodeError, IndexError):
        return {
            "suggestions": [],
            "urgency_message": None,
            "next_step": "Continuar qualificação",
            "personalized_pitch": None,
            "objection_responses": {}
        }


# ============================================
# HELPERS PARA DELAY HUMANIZADO
# ============================================

def calculate_typing_delay(message_length: int) -> float:
    """
    Calcula delay de digitação baseado no tamanho da mensagem.
    
    Args:
        message_length: Número de caracteres da resposta
    
    Returns:
        Delay em segundos (entre 1 e 5)
    """
    # Simula ~40 palavras por minuto de digitação
    # ~5 caracteres por palavra em média
    words = message_length / 5
    seconds = words / 40 * 60
    
    # Limita entre 1 e 5 segundos
    delay = max(1.0, min(5.0, seconds))
    
    # Adiciona variação aleatória de ±20%
    variation = delay * 0.2 * (random.random() * 2 - 1)
    
    return round(delay + variation, 1)