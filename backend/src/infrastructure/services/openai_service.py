"""
SERVIÇO OPENAI - VERSÃO OTIMIZADA
===================================

Integração com a API da OpenAI.
MELHORIAS:
- Resumos curtos e objetivos
- Qualificação precisa de leads
- Prompts otimizados
- Validação robusta
- Temperature ajustado
"""

import json
import random
import logging
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from src.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

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


def get_random_greeting(tone: str = "cordial") -> str:
    """Retorna uma saudação aleatória baseada no tom."""
    greetings = GREETING_VARIATIONS.get(tone, GREETING_VARIATIONS["cordial"])
    return random.choice(greetings)


# ============================================
# FUNÇÕES PRINCIPAIS
# ============================================

async def chat_completion(
    messages: list[dict],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> dict:
    """Envia mensagens para OpenAI e retorna resposta."""
    try:
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
    except Exception as e:
        logger.error(f"Erro na chamada OpenAI: {e}")
        return {
            "content": "Desculpe, tive um problema técnico. Pode repetir?",
            "tokens_used": 0
        }


async def detect_sentiment(message: str) -> dict:
    """
    Detecta o sentimento/humor do lead na mensagem.
    Análise rápida por palavras-chave (sem chamar API).
    """
    
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
            "tone_adjustment": "Seja empático, resolva rapidamente. Evite frases genéricas.",
            "detected_signals": "frustração"
        }
    elif urgent_score >= 1:
        return {
            "sentiment": "urgent",
            "confidence": min(0.9, 0.6 + urgent_score * 0.1),
            "tone_adjustment": "Seja direto e objetivo. Priorize resolver a urgência.",
            "detected_signals": "urgência"
        }
    elif excited_score >= 1 and positive_score >= 1:
        return {
            "sentiment": "excited",
            "confidence": 0.8,
            "tone_adjustment": "Mantenha a energia! Facilite o fechamento.",
            "detected_signals": "animação"
        }
    elif positive_score >= 1:
        return {
            "sentiment": "positive",
            "confidence": min(0.9, 0.6 + positive_score * 0.1),
            "tone_adjustment": "Continue positivo. Bom momento para qualificar.",
            "detected_signals": "satisfação"
        }
    else:
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "tone_adjustment": None,
            "detected_signals": None
        }


async def extract_lead_data(
    conversation: list[dict],
    required_fields: list[str],
    optional_fields: list[str],
) -> dict:
    """
    Extrai dados estruturados do lead a partir da conversa.
    OTIMIZADO: Prompt mais curto e direto.
    """

    all_fields = required_fields + optional_fields

    extraction_prompt = f"""Extraia informações do cliente desta conversa.

CAMPOS: {json.dumps(all_fields, ensure_ascii=False)}

EXTRAS (se mencionado):
- family_situation, work_info, budget_range, urgency_level
- preferences, pain_points, objections, buying_signals

CONVERSA (últimas 10 mensagens):
{json.dumps(conversation[-10:], ensure_ascii=False)}

Retorne APENAS JSON válido. Use null se não mencionado.

JSON:"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.1,
            max_tokens=600,
        )

        content = response.choices[0].message.content.strip()
        
        # Remove markdown se houver
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        return json.loads(content)
    except (json.JSONDecodeError, IndexError, Exception) as e:
        logger.error(f"Erro ao extrair dados do lead: {e}")
        return {}


async def qualify_lead(
    conversation: list[dict],
    extracted_data: dict,
    qualification_rules: dict,
) -> dict:
    """
    Qualifica o lead como hot/warm/cold.
    CORRIGIDO: Não marca leads interessados como "frio".
    """

    qualification_prompt = f"""Qualifique este lead como HOT, WARM ou COLD.

CRITÉRIOS:
🔥 HOT (pronto para comprar):
- Perguntou sobre pagamento/preço
- Perguntou disponibilidade/quando pode começar
- Tem prazo definido
- Demonstra urgência clara

🟡 WARM (interessado):
- Fez várias perguntas
- Está comparando opções
- Tem interesse claro mas sem urgência
- Respondeu perguntas de qualificação

🔵 COLD (só pesquisando):
- Poucas mensagens
- Respostas curtas/vagas
- "Só olhando"/"Depois eu vejo"

DADOS:
{json.dumps(extracted_data, ensure_ascii=False)}

CONVERSA (últimas 8):
{json.dumps(conversation[-8:], ensure_ascii=False)}

Retorne APENAS JSON:
{{
  "qualification": "hot|warm|cold",
  "confidence": 0.0-1.0,
  "reason": "motivo em 1 linha",
  "buying_signals_found": ["sinal1", "sinal2"],
  "recommended_action": "ação para o vendedor"
}}

JSON:"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": qualification_prompt}],
            temperature=0.15,  # Mais determinístico
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        result = json.loads(content)
        
        # Validação: Se tem buying_signals, não pode ser cold
        if result.get("buying_signals_found") and result.get("qualification") == "cold":
            result["qualification"] = "warm"
            logger.warning("Corrigido: Lead com sinais de compra marcado como cold")
        
        return result
        
    except (json.JSONDecodeError, IndexError, Exception) as e:
        logger.error(f"Erro ao qualificar lead: {e}")
        return {
            "qualification": "warm",
            "confidence": 0.5,
            "reason": "Erro na qualificação, classificado como warm por segurança",
            "buying_signals_found": [],
            "recommended_action": "Continuar qualificação"
        }


async def generate_lead_summary(
    conversation: list[dict],
    extracted_data: dict,
    qualification: dict,
) -> str:
    """
    Gera resumo CURTO e ÚTIL para o vendedor.
    Máximo 5 linhas, informações acionáveis.
    """

    lead_name = extracted_data.get("name", "Cliente")
    
    # Interesse principal
    interest = "informações"
    if extracted_data.get("preferences"):
        prefs = extracted_data["preferences"]
        if isinstance(prefs, list) and prefs:
            interest = prefs[0][:30]
        elif isinstance(prefs, str):
            interest = prefs[:30]
    
    # Qualificação
    qual = qualification.get("qualification", "cold").upper()
    
    # Urgência
    urgency = "Média"
    if qual == "HOT":
        urgency = "Alta"
    elif qual == "COLD":
        urgency = "Baixa"
    
    # Orçamento
    budget = extracted_data.get("budget_range", "Não informado")
    if isinstance(budget, str) and len(budget) > 25:
        budget = budget[:22] + "..."
    
    # Próximo passo
    next_step = qualification.get("recommended_action", "Fazer contato")
    if len(next_step) > 35:
        next_step = next_step[:32] + "..."

    summary_prompt = f"""Crie resumo ULTRA CURTO para vendedor (5 linhas, 40 chars/linha).

DADOS:
- Cliente: {lead_name}
- Busca: {interest}
- Status: {qual}
- Urgência: {urgency}
- Orçamento: {budget}

CONVERSA (últimas 3 mensagens):
{json.dumps(conversation[-3:], ensure_ascii=False)}

FORMATO (EXATAMENTE assim):
🎯 {lead_name} quer [resumo do interesse]
📍 Busca [especifique o que procura]
⏰ Urgência {urgency} - [motivo curto]
💰 {budget}
✅ Ação: [próximo passo]

REGRAS:
- MÁXIMO 40 caracteres por linha
- SEM asteriscos, SEM bullets
- Emojis APENAS no início
- DIRETO, ACIONÁVEL

RESUMO:"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.1,
            max_tokens=150,
        )

        summary = response.choices[0].message.content.strip()
        
        # Limpa formatação
        summary = summary.replace("**", "").replace("- ", "").replace("* ", "")
        
        # Força 5 linhas
        lines = [line.strip() for line in summary.split('\n') if line.strip()]
        if len(lines) > 5:
            lines = lines[:5]
            logger.warning(f"Resumo truncado de {len(lines)} para 5 linhas")
        elif len(lines) < 5:
            # Completa com linha de ação se faltar
            while len(lines) < 5:
                lines.append(f"✅ Ação: {next_step}")
        
        # Limita tamanho de cada linha
        lines = [line[:60] if len(line) > 60 else line for line in lines]
        
        return '\n'.join(lines)
        
    except Exception as e:
        logger.error(f"Erro ao gerar resumo: {e}")
        # Fallback direto e garantido
        return f"""🎯 {lead_name} quer {interest[:20]}
📍 Interesse em {qual}
⏰ Urgência {urgency}
💰 {budget}
✅ Ação: {next_step[:30]}"""


async def generate_conversation_summary(conversation: list[dict]) -> str:
    """
    Gera um resumo curto da conversa (máximo 100 caracteres).
    Para uso em retorno do lead.
    """
    
    if len(conversation) < 2:
        return None
    
    summary_prompt = f"""Resuma em 1 frase curta (máximo 80 caracteres) o que o cliente queria.

CONVERSA:
{json.dumps(conversation[-6:], ensure_ascii=False)}

Formato: "Queria saber sobre [X]"
SEM saudações, SEM formalidades.

RESUMO:"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2,
            max_tokens=50,
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Garante máximo 100 caracteres
        if len(summary) > 100:
            summary = summary[:97] + "..."
        
        return summary
        
    except Exception as e:
        logger.error(f"Erro ao gerar resumo da conversa: {e}")
        return None


# ============================================
# HELPERS
# ============================================

def calculate_typing_delay(message_length: int) -> float:
    """
    Calcula delay de digitação baseado no tamanho da mensagem.
    Entre 1 e 5 segundos.
    """
    words = message_length / 5
    seconds = words / 40 * 60
    
    delay = max(1.0, min(5.0, seconds))
    
    # Adiciona variação aleatória de ±20%
    variation = delay * 0.2 * (random.random() * 2 - 1)
    
    return round(delay + variation, 1)