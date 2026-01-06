"""
PROMPT ESPECÍFICO PARA IMOBILIÁRIA - VERSÃO ENXUTA
===================================================
Prompt otimizado SÓ para nicho imobiliário.
Máximo 6000 chars - SEM truncamento.

ÚLTIMA ATUALIZAÇÃO: 2026-01-06
"""

import logging

logger = logging.getLogger(__name__)

# ============================================
# PROMPT BASE IMOBILIÁRIA - ENXUTO E DIRETO
# ============================================

IMOBILIARIA_SYSTEM_PROMPT = """Você é a assistente virtual da {company_name}.

Seu trabalho é QUALIFICAR leads de imóveis no WhatsApp.

═══════════════════════════════════════════════════════════════
🎯 REGRAS DE OURO - LEIA COM ATENÇÃO!
═══════════════════════════════════════════════════════════════

**REGRA #1: RESPOSTAS CURTAS (MÁXIMO 2-3 LINHAS)**

Isso é WhatsApp! Seja BREVE.

✅ BOM: "Show! Essa casa de 3 quartos em Canoas tá R$ 258k. Pra morar ou investir?"

❌ RUIM: "Olá! Que ótimo que entrou em contato. Esse imóvel é uma excelente 
oportunidade com características incríveis..."

───────────────────────────────────────────────────────────────

**REGRA #2: URGÊNCIA + INTERESSE = TRANSFERE AGORA!**

Se o lead disser QUALQUER coisa indicando DECISÃO ou URGÊNCIA:

🔥 Sinais de URGÊNCIA:
- "Tenho valor à vista"
- "Financiamento aprovado"
- "Preciso me mudar rápido"
- "O mais rápido possível"
- "Quero esse imóvel"
- "Gostei desse"
- "Quando posso visitar?"
- "Quero comprar"

→ PARE de coletar info
→ RESPONDA: "Perfeito! Você tá pronto. Vou te passar pro corretor agora!"
→ TRANSFIRA IMEDIATAMENTE

───────────────────────────────────────────────────────────────

**REGRA #3: TEM CÓDIGO DE IMÓVEL? USE OS DADOS!**

Se o lead menciona CÓDIGO (ex: 765791), VOCÊ JÁ TEM os dados!

❌ ERRADO: "Você busca casa ou apartamento?" (VOCÊ JÁ SABE!)
✅ CERTO: "Show! Esse apto de 3 quartos em Canoas tá R$ 258k. Pra morar ou investir?"

───────────────────────────────────────────────────────────────

**REGRA #4: UMA PERGUNTA POR VEZ**

❌ ERRADO: "Tem preferência sobre banheiros, vagas e área?"
✅ CERTO: "Pra morar ou investir?"

───────────────────────────────────────────────────────────────

**REGRA #5: NÃO PERGUNTE O QUE ELE JÁ RESPONDEU**

ANTES de perguntar, LEIA o histórico!

Se ele já disse o nome, NÃO pergunte de novo.
Se ele já disse o bairro, NÃO pergunte de novo.

═══════════════════════════════════════════════════════════════
💬 TOM DE VOZ - WHATSAPP CASUAL
═══════════════════════════════════════════════════════════════

Seja {tone}, mas NATURAL:

✅ USE: "Show!", "Legal!", "Opa!", "Beleza!"
❌ EVITE: "Excelente escolha", "Ótimo!", tom corporativo

Emojis: 0-1 por mensagem (quando fizer sentido).

═══════════════════════════════════════════════════════════════
📋 INFORMAÇÕES PARA COLETAR (se der tempo)
═══════════════════════════════════════════════════════════════

1. **Nome** - "Como posso te chamar?"
2. **Interesse** - "Pra morar ou investir?"
3. **Urgência** - "Pra quando você tá pensando?"
4. **Orçamento** (opcional) - "Qual faixa de valor você tá buscando?"

Mas LEMBRE: Se ele demonstrou URGÊNCIA → TRANSFIRA!

═══════════════════════════════════════════════════════════════
🌡️ QUALIFICAÇÃO
═══════════════════════════════════════════════════════════════

🔥 LEAD QUENTE:
- Tem urgência + interesse específico
- Quer visitar/comprar AGORA
- Mencionou dinheiro/financiamento aprovado

→ TRANSFIRA!

🌡️ LEAD MORNO:
- Interesse claro SEM urgência
- Pesquisando opções
- Perguntas detalhadas

❄️ LEAD FRIO:
- Só curiosidade
- Sem engajamento
- "Talvez um dia"

═══════════════════════════════════════════════════════════════
{empreendimento_section}
═══════════════════════════════════════════════════════════════

{imovel_portal_section}

═══════════════════════════════════════════════════════════════
{lead_context_section}
═══════════════════════════════════════════════════════════════

{custom_rules_section}

═══════════════════════════════════════════════════════════════
⚠️ SITUAÇÕES ESPECIAIS
═══════════════════════════════════════════════════════════════

📱 ÁUDIO: "Não consigo ouvir áudio 😅 Pode escrever?"

❓ NÃO SABE: "Vou anotar pro corretor! Ele é expert nisso."

💰 PERGUNTA DE PREÇO (sem dados): "Vou confirmar o valor atualizado!"

📍 LOCALIZAÇÃO ESPECÍFICA: Responda se souber, senão "Vou confirmar!"

🚨 PERGUNTAS TÉCNICAS (financiamento, documentos, etc):
→ "O corretor te passa todos os detalhes certinhos!"

═══════════════════════════════════════════════════════════════
✨ LEMBRE-SE
═══════════════════════════════════════════════════════════════

Você é consultora que:
- 👂 OUVE (lê o histórico!)
- 💬 CONVERSA naturalmente (WhatsApp, não e-mail!)
- 🎯 QUALIFICA (detecta urgência!)
- 🚀 TRANSFERE na hora certa (quente = JÁ!)

Seja RÁPIDA, OBJETIVA e HUMANA! 🤝
"""


# ============================================
# SEÇÕES DINÂMICAS
# ============================================

EMPREENDIMENTO_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🏢 EMPREENDIMENTO: {nome}
═══════════════════════════════════════════════════════════════

{descricao}

**Localização:** {localizacao}
**Tipologias:** {tipologias}
**Metragem:** {metragem}
**Investimento:** {preco}

{diferenciais}

{instrucoes_ia}

⚠️ PERGUNTAS OBRIGATÓRIAS sobre este empreendimento:
{perguntas_qualificacao}
"""

IMOVEL_PORTAL_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🏠 IMÓVEL DO PORTAL - CÓDIGO {codigo}
═══════════════════════════════════════════════════════════════

**DADOS DISPONÍVEIS:**
- Tipo: {tipo}
- Localização: {regiao}
- Quartos: {quartos}
- Banheiros: {banheiros}
- Vagas: {vagas}
- Área: {metragem} m²
- Preço: {preco}

⚠️ VOCÊ JÁ TEM ESSES DADOS - NÃO PERGUNTE DE NOVO!

**COMO RESPONDER:**

Cliente: "Código {codigo}"
Você: "Show! Esse {tipo} de {quartos} quartos em {regiao} tá {preco}. Pra morar ou investir?"

NÃO pergunte tipo/quartos/localização - VOCÊ JÁ SABE!
"""

LEAD_CONTEXT_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
👤 INFORMAÇÕES DO LEAD (O QUE VOCÊ JÁ SABE)
═══════════════════════════════════════════════════════════════

{lead_info}

⚠️ NÃO PERGUNTE O QUE VOCÊ JÁ SABE!

{historico_recente}
"""


# ============================================
# FUNÇÃO PRINCIPAL
# ============================================

def build_prompt_imobiliaria(
    company_name: str,
    tone: str = "cordial",
    empreendimento: dict = None,
    imovel_portal: dict = None,
    lead_context: dict = None,
    custom_rules: list[str] = None,
    recent_messages: list[dict] = None,
) -> str:
    """
    Monta prompt ENXUTO para imobiliária.
    
    Args:
        company_name: Nome da empresa
        tone: Tom de voz (cordial, descontraído, etc)
        empreendimento: Dados do empreendimento (se detectado)
        imovel_portal: Dados do imóvel do portal (se detectado)
        lead_context: Contexto do lead (nome, phone, etc)
        custom_rules: Regras customizadas adicionais
        recent_messages: Últimas 3-5 mensagens do histórico
    """
    
    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO: EMPREENDIMENTO
    # ═══════════════════════════════════════════════════════════════
    empreendimento_section = ""
    if empreendimento:
        # Monta localização
        loc_parts = []
        if empreendimento.get("endereco"):
            loc_parts.append(empreendimento["endereco"])
        if empreendimento.get("bairro"):
            loc_parts.append(empreendimento["bairro"])
        if empreendimento.get("cidade"):
            cidade = empreendimento["cidade"]
            if empreendimento.get("estado"):
                cidade += f"/{empreendimento['estado']}"
            loc_parts.append(cidade)
        
        localizacao = ", ".join(loc_parts) if loc_parts else "N/A"
        
        # Tipologias
        tipologias = ", ".join(empreendimento.get("tipologias", [])) if empreendimento.get("tipologias") else "Consulte"
        
        # Metragem
        metragem = "N/A"
        if empreendimento.get("metragem_minima") and empreendimento.get("metragem_maxima"):
            metragem = f"{empreendimento['metragem_minima']}m² a {empreendimento['metragem_maxima']}m²"
        elif empreendimento.get("metragem_minima"):
            metragem = f"A partir de {empreendimento['metragem_minima']}m²"
        
        # Preço
        preco = "Consulte"
        if empreendimento.get("preco_minimo") and empreendimento.get("preco_maximo"):
            preco = f"R$ {empreendimento['preco_minimo']:,.0f} a R$ {empreendimento['preco_maximo']:,.0f}".replace(",", ".")
        elif empreendimento.get("preco_minimo"):
            preco = f"A partir de R$ {empreendimento['preco_minimo']:,.0f}".replace(",", ".")
        
        # Diferenciais
        diferenciais = ""
        if empreendimento.get("diferenciais"):
            difs = empreendimento["diferenciais"][:5]  # Max 5
            diferenciais = "**Diferenciais:** " + ", ".join(difs)
        
        # Instruções IA
        instrucoes_ia = ""
        if empreendimento.get("instrucoes_ia"):
            instrucoes_ia = f"**IMPORTANTE:** {empreendimento['instrucoes_ia']}"
        
        # Perguntas obrigatórias
        perguntas_qualificacao = ""
        if empreendimento.get("perguntas_qualificacao"):
            perguntas = empreendimento["perguntas_qualificacao"][:5]  # Max 5
            perguntas_qualificacao = "\n".join(f"{i}. {p}" for i, p in enumerate(perguntas, 1))
        
        empreendimento_section = EMPREENDIMENTO_SECTION_TEMPLATE.format(
            nome=empreendimento.get("nome", "N/A"),
            descricao=empreendimento.get("descricao", "")[:200] if empreendimento.get("descricao") else "",
            localizacao=localizacao,
            tipologias=tipologias,
            metragem=metragem,
            preco=preco,
            diferenciais=diferenciais,
            instrucoes_ia=instrucoes_ia,
            perguntas_qualificacao=perguntas_qualificacao,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO: IMÓVEL PORTAL
    # ═══════════════════════════════════════════════════════════════
    imovel_portal_section = ""
    if imovel_portal:
        imovel_portal_section = IMOVEL_PORTAL_SECTION_TEMPLATE.format(
            codigo=imovel_portal.get("codigo", "N/A"),
            tipo=imovel_portal.get("tipo", "Imóvel"),
            regiao=imovel_portal.get("regiao", "N/A"),
            quartos=imovel_portal.get("quartos", "N/A"),
            banheiros=imovel_portal.get("banheiros", "N/A"),
            vagas=imovel_portal.get("vagas", "N/A"),
            metragem=imovel_portal.get("metragem", "N/A"),
            preco=imovel_portal.get("preco", "Consulte"),
        )
    
    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO: CONTEXTO DO LEAD
    # ═══════════════════════════════════════════════════════════════
    lead_context_section = ""
    if lead_context:
        lead_info_parts = []
        
        if lead_context.get("name"):
            lead_info_parts.append(f"**Nome:** {lead_context['name']}")
        
        if lead_context.get("phone"):
            lead_info_parts.append(f"**WhatsApp:** {lead_context['phone']}")
        
        if lead_context.get("urgency_level"):
            lead_info_parts.append(f"**Urgência:** {lead_context['urgency_level']}")
        
        if lead_context.get("budget_range"):
            lead_info_parts.append(f"**Orçamento:** {lead_context['budget_range']}")
        
        if lead_context.get("preferences"):
            prefs = lead_context["preferences"]
            if isinstance(prefs, dict):
                prefs_str = ", ".join(f"{k}: {v}" for k, v in prefs.items())
                lead_info_parts.append(f"**Preferências:** {prefs_str}")
        
        if lead_context.get("empreendimento_nome"):
            lead_info_parts.append(f"**Interessado em:** {lead_context['empreendimento_nome']}")
        
        # Histórico recente
        historico_recente = ""
        if recent_messages and len(recent_messages) >= 2:
            historico_recente = "\n**ÚLTIMAS MENSAGENS (LEIA COM ATENÇÃO!):**\n"
            for msg in recent_messages[-3:]:  # Últimas 3
                role = "👤 LEAD" if msg.get("role") == "user" else "🤖 VOCÊ"
                content = msg.get("content", "")
                historico_recente += f"{role}: {content}\n"
            historico_recente += "\n⚠️ NÃO repita perguntas que o lead JÁ respondeu acima!"
        
        if lead_info_parts or historico_recente:
            lead_info = "\n".join(lead_info_parts) if lead_info_parts else "Nenhuma informação coletada ainda."
            
            lead_context_section = LEAD_CONTEXT_SECTION_TEMPLATE.format(
                lead_info=lead_info,
                historico_recente=historico_recente,
            )
    
    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO: REGRAS CUSTOMIZADAS
    # ═══════════════════════════════════════════════════════════════
    custom_rules_section = ""
    if custom_rules:
        custom_rules_section = "═══════════════════════════════════════════════════════════════\n"
        custom_rules_section += "📌 REGRAS ADICIONAIS DA EMPRESA\n"
        custom_rules_section += "═══════════════════════════════════════════════════════════════\n\n"
        for rule in custom_rules[:5]:  # Max 5 regras
            custom_rules_section += f"• {rule}\n"
    
    # ═══════════════════════════════════════════════════════════════
    # MONTA PROMPT FINAL
    # ═══════════════════════════════════════════════════════════════
    final_prompt = IMOBILIARIA_SYSTEM_PROMPT.format(
        company_name=company_name,
        tone=tone,
        empreendimento_section=empreendimento_section,
        imovel_portal_section=imovel_portal_section,
        lead_context_section=lead_context_section,
        custom_rules_section=custom_rules_section,
    )
    
    # Remove linhas vazias excessivas
    lines = final_prompt.split('\n')
    cleaned_lines = []
    empty_count = 0
    for line in lines:
        if line.strip() == '':
            empty_count += 1
            if empty_count <= 2:  # Max 2 linhas vazias seguidas
                cleaned_lines.append(line)
        else:
            empty_count = 0
            cleaned_lines.append(line)
    
    final_prompt = '\n'.join(cleaned_lines)
    
    logger.info(f"✅ Prompt imobiliária gerado: {len(final_prompt)} chars")
    
    return final_prompt