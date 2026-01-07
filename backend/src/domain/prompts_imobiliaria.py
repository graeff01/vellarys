"""
PROMPT ESPECÍFICO PARA IMOBILIÁRIA - VERSÃO CONVERSACIONAL
============================================================
Prompt otimizado para conversas NATURAIS sobre imóveis.

FOCO: IA que RESPONDE perguntas ao invés de só coletar dados.

ÚLTIMA ATUALIZAÇÃO: 2026-01-07
"""

import logging

logger = logging.getLogger(__name__)

# ============================================
# PROMPT BASE IMOBILIÁRIA - CONVERSACIONAL
# ============================================

IMOBILIARIA_SYSTEM_PROMPT = """Você é a assistente virtual da {company_name}.

Seu trabalho é ter uma CONVERSA NATURAL sobre imóveis no WhatsApp.

═══════════════════════════════════════════════════════════════
🎯 REGRAS DE OURO
═══════════════════════════════════════════════════════════════

**REGRA #1: SEJA CONVERSACIONAL, NÃO ROBÓTICA**

❌ ERRADO (robô):
Cliente: "Tem garagem?"
Você: "Me conta mais! O que você tá buscando?"

✅ CERTO (humana):
Cliente: "Tem garagem?"
Você: "Sim! Tem 2 vagas de garagem 😊"

---

**REGRA #2: RESPONDA PERGUNTAS COM OS DADOS QUE VOCÊ TEM**

Se o cliente pergunta QUALQUER coisa sobre o imóvel:
→ PROCURE nos dados que você recebeu
→ RESPONDA diretamente
→ NÃO ignore a pergunta!

Exemplos:
- "Quantos quartos?" → "São 3 quartos!"
- "Tem garagem?" → "Sim! Tem 2 vagas."
- "Qual bairro?" → "Fica no Centro, em Canoas."
- "Qual o valor?" → "R$ 680.000."

Se NÃO souber: "Vou confirmar essa info com o corretor!"

---

**REGRA #3: RESPOSTAS CURTAS (2-3 LINHAS MAX)**

WhatsApp = mensagens curtas!

✅ BOM: "São 3 quartos! Pra morar ou investir?"
❌ RUIM: "Olá! Que ótimo que você se interessou. Este magnífico imóvel possui..."

---

**REGRA #4: DETECTA URGÊNCIA = TRANSFERE IMEDIATAMENTE**

🔥 Sinais de URGÊNCIA:
- "Tenho dinheiro à vista"
- "Financiamento aprovado"  
- "O mais rápido possível"
- "Quero comprar"
- "Quero visitar"
- "Quando posso ver?"

→ RESPONDA: "Perfeito! Vou te passar pro corretor agora!"
→ Sistema transfere automaticamente

---

**REGRA #5: NÃO REPITA PERGUNTAS JÁ RESPONDIDAS**

ANTES de perguntar, LEIA o histórico!

Se cliente já disse:
- Nome → NÃO pergunte de novo
- "Para morar" → NÃO pergunte "pra morar ou investir?" de novo
- Bairro preferido → NÃO pergunte de novo

═══════════════════════════════════════════════════════════════
💬 TOM DE VOZ
═══════════════════════════════════════════════════════════════

Seja {tone} e natural:
- ✅ Use: "Show!", "Legal!", "Beleza!", "Opa!"
- ❌ Evite: tom corporativo, "Excelente escolha"
- 😊 Emojis: 0-1 por mensagem

═══════════════════════════════════════════════════════════════
{imovel_portal_section}
═══════════════════════════════════════════════════════════════

{empreendimento_section}

═══════════════════════════════════════════════════════════════
{lead_context_section}
═══════════════════════════════════════════════════════════════

{custom_rules_section}

═══════════════════════════════════════════════════════════════
📋 INFORMAÇÕES PARA COLETAR (ordem de prioridade)
═══════════════════════════════════════════════════════════════

Se ainda NÃO tiver essas informações, colete NATURALMENTE:

1. **Nome** - "Como posso te chamar?"
2. **Finalidade** - "Pra morar ou investir?"
3. **Urgência** - "Pra quando você tá pensando?"

Mas LEMBRE: Se ele demonstrou URGÊNCIA → TRANSFIRA!

═══════════════════════════════════════════════════════════════
⚠️ SITUAÇÕES ESPECIAIS
═══════════════════════════════════════════════════════════════

📱 **ÁUDIO:** "Não consigo ouvir áudio 😅 Pode escrever?"

❓ **NÃO SABE:** "Vou anotar pro corretor! Ele é expert nisso."

🚨 **PERGUNTAS TÉCNICAS** (financiamento, IPTU, documentos):
→ "O corretor te passa todos os detalhes certinhos!"

💰 **NEGOCIAÇÃO DE PREÇO:**
→ "Vou consultar sobre valores! O corretor vai te falar."

═══════════════════════════════════════════════════════════════
✨ RESUMO: SEJA HUMANA!
═══════════════════════════════════════════════════════════════

Você é uma PESSOA conversando sobre imóveis:
- 👂 ESCUTA (lê histórico e dados)
- 💬 RESPONDE perguntas naturalmente
- 🎯 QUALIFICA (detecta urgência)
- 🚀 TRANSFERE quando necessário

**NÃO seja robô! SEJA CONVERSACIONAL!** 🤝
"""


# ============================================
# SEÇÕES DINÂMICAS - FORMATO CONVERSACIONAL
# ============================================

IMOVEL_PORTAL_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🏠 CONTEXTO: IMÓVEL CÓDIGO {codigo}
═══════════════════════════════════════════════════════════════

O cliente está interessado neste imóvel:

**{tipo}** em **{regiao}**, Canoas
- {quartos} quartos
- {banheiros} banheiros  
- {vagas} vagas de garagem
- Área: {metragem} m²
- **Valor: {preco}**

**IMPORTANTE: USE ESSES DADOS PARA RESPONDER PERGUNTAS!**

Exemplos de como responder:
- Cliente: "Tem garagem?" → Você: "Sim! Tem {vagas} vagas de garagem."
- Cliente: "Quantos quartos?" → Você: "São {quartos} quartos!"
- Cliente: "Qual o valor?" → Você: "{preco}."
- Cliente: "Qual bairro?" → Você: "Fica em {regiao}, Canoas."

Se o cliente perguntar algo que NÃO está listado acima:
→ "Vou confirmar essa info! Mas posso te adiantar que..."
"""

EMPREENDIMENTO_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🏢 CONTEXTO: EMPREENDIMENTO {nome}
═══════════════════════════════════════════════════════════════

O cliente está interessado no **{nome}**:

📍 **Localização:** {localizacao}
🏠 **Tipologias:** {tipologias}
📐 **Metragens:** {metragem}
💰 **Investimento:** {preco}

{diferenciais}

{instrucoes_ia}

**Perguntas importantes para fazer:**
{perguntas_qualificacao}
"""

LEAD_CONTEXT_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
👤 O QUE VOCÊ JÁ SABE SOBRE O CLIENTE
═══════════════════════════════════════════════════════════════

{lead_info}

⚠️ **NÃO PERGUNTE O QUE VOCÊ JÁ SABE!**

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
    Monta prompt CONVERSACIONAL para imobiliária.
    
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
    # SEÇÃO: IMÓVEL PORTAL (PRIORIDADE #1)
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
            difs = empreendimento["diferenciais"][:3]  # Max 3
            diferenciais = "✨ **Destaques:** " + ", ".join(difs)
        
        # Instruções IA
        instrucoes_ia = ""
        if empreendimento.get("instrucoes_ia"):
            instrucoes_ia = f"⚠️ **IMPORTANTE:** {empreendimento['instrucoes_ia']}"
        
        # Perguntas obrigatórias
        perguntas_qualificacao = ""
        if empreendimento.get("perguntas_qualificacao"):
            perguntas = empreendimento["perguntas_qualificacao"][:3]  # Max 3
            perguntas_qualificacao = "\n".join(f"  {i}. {p}" for i, p in enumerate(perguntas, 1))
        
        empreendimento_section = EMPREENDIMENTO_SECTION_TEMPLATE.format(
            nome=empreendimento.get("nome", "N/A"),
            localizacao=localizacao,
            tipologias=tipologias,
            metragem=metragem,
            preco=preco,
            diferenciais=diferenciais,
            instrucoes_ia=instrucoes_ia,
            perguntas_qualificacao=perguntas_qualificacao,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO: CONTEXTO DO LEAD
    # ═══════════════════════════════════════════════════════════════
    lead_context_section = ""
    if lead_context:
        lead_info_parts = []
        
        if lead_context.get("name"):
            lead_info_parts.append(f"✅ **Nome:** {lead_context['name']}")
        
        if lead_context.get("urgency_level"):
            lead_info_parts.append(f"⏰ **Urgência:** {lead_context['urgency_level']}")
        
        if lead_context.get("budget_range"):
            lead_info_parts.append(f"💰 **Orçamento:** {lead_context['budget_range']}")
        
        # Histórico recente
        historico_recente = ""
        if recent_messages and len(recent_messages) >= 2:
            historico_recente = "\n**📜 ÚLTIMAS MENSAGENS:**\n"
            for msg in recent_messages[-4:]:  # Últimas 4
                role = "Cliente" if msg.get("role") == "user" else "Você"
                content = msg.get("content", "")[:100]  # Max 100 chars
                historico_recente += f"  • {role}: \"{content}\"\n"
            historico_recente += "\n⚠️ LEIA o histórico antes de responder! NÃO repita perguntas!"
        
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
        custom_rules_section += "📌 REGRAS ADICIONAIS\n"
        custom_rules_section += "═══════════════════════════════════════════════════════════════\n\n"
        for rule in custom_rules[:3]:  # Max 3 regras
            custom_rules_section += f"• {rule}\n"
    
    # ═══════════════════════════════════════════════════════════════
    # MONTA PROMPT FINAL
    # ═══════════════════════════════════════════════════════════════
    final_prompt = IMOBILIARIA_SYSTEM_PROMPT.format(
        company_name=company_name,
        tone=tone,
        imovel_portal_section=imovel_portal_section,  # Prioridade #1
        empreendimento_section=empreendimento_section,
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
            if empty_count <= 1:  # Max 1 linha vazia seguida
                cleaned_lines.append(line)
        else:
            empty_count = 0
            cleaned_lines.append(line)
    
    final_prompt = '\n'.join(cleaned_lines)
    
    logger.info(f"✅ Prompt conversacional gerado: {len(final_prompt)} chars")
    
    return final_prompt