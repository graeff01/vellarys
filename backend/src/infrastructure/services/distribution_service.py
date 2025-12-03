"""
SERVIÇO DE DISTRIBUIÇÃO DE LEADS
=================================

Responsável por decidir qual vendedor deve receber cada lead.
Suporta múltiplos métodos de distribuição configuráveis por tenant.
"""

from datetime import date, datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Seller, Lead, Tenant, LeadAssignment, Notification


# ==========================================
# CONFIGURAÇÕES PADRÃO
# ==========================================

DEFAULT_DISTRIBUTION_CONFIG = {
    "method": "round_robin",  # round_robin, by_city, by_specialty, by_city_specialty, by_priority, least_busy, manual
    "fallback": "manager",  # manager, round_robin, queue
    "respect_daily_limit": True,
    "respect_availability": True,
    "notify_manager_copy": False,  # Gestor sempre recebe cópia?
    "last_seller_index": 0,  # Para round robin
}


# ==========================================
# FUNÇÕES DE SELEÇÃO DE VENDEDOR
# ==========================================

async def get_available_sellers(
    db: AsyncSession,
    tenant_id: int,
    respect_limit: bool = True,
    respect_availability: bool = True,
) -> List[Seller]:
    """
    Busca vendedores disponíveis para receber leads.
    """
    query = select(Seller).where(
        Seller.tenant_id == tenant_id,
        Seller.active == True,
    )
    
    if respect_availability:
        query = query.where(
            Seller.available == True,
            Seller.on_vacation == False,
        )
    
    result = await db.execute(query)
    sellers = list(result.scalars().all())
    
    if respect_limit:
        today = date.today()
        available_sellers = []
        for seller in sellers:
            if seller.max_leads_per_day == 0:
                available_sellers.append(seller)
            elif seller.leads_today_date != today:
                available_sellers.append(seller)
            elif seller.leads_today < seller.max_leads_per_day:
                available_sellers.append(seller)
        return available_sellers
    
    return sellers


async def select_by_round_robin(
    sellers: List[Seller],
    last_index: int,
) -> Tuple[Optional[Seller], int]:
    """
    Seleciona vendedor por rodízio.
    Retorna (vendedor, novo_índice)
    """
    if not sellers:
        return None, last_index
    
    # Ordena por ID para consistência
    sellers_sorted = sorted(sellers, key=lambda s: s.id)
    
    # Próximo índice
    next_index = (last_index + 1) % len(sellers_sorted)
    
    return sellers_sorted[next_index], next_index


async def select_by_city(
    sellers: List[Seller],
    lead_city: Optional[str],
) -> Optional[Seller]:
    """
    Seleciona vendedor pela cidade do lead.
    """
    if not sellers or not lead_city:
        return None
    
    lead_city_lower = lead_city.lower().strip()
    
    # Busca vendedor que atende a cidade
    matching_sellers = []
    for seller in sellers:
        if seller.cities:
            seller_cities = [c.lower().strip() for c in seller.cities]
            if lead_city_lower in seller_cities:
                matching_sellers.append(seller)
    
    if not matching_sellers:
        return None
    
    # Se tem mais de um, pega o com menos leads hoje
    return min(matching_sellers, key=lambda s: s.leads_today or 0)


async def select_by_specialty(
    sellers: List[Seller],
    lead_specialty: Optional[str],
) -> Optional[Seller]:
    """
    Seleciona vendedor pela especialidade do lead.
    A especialidade do lead vem do custom_data (ex: interesse em venda/aluguel)
    """
    if not sellers or not lead_specialty:
        return None
    
    lead_specialty_lower = lead_specialty.lower().strip()
    
    # Busca vendedor com a especialidade
    matching_sellers = []
    for seller in sellers:
        if seller.specialties:
            seller_specialties = [s.lower().strip() for s in seller.specialties]
            if lead_specialty_lower in seller_specialties:
                matching_sellers.append(seller)
    
    if not matching_sellers:
        return None
    
    # Se tem mais de um, pega o com menos leads hoje
    return min(matching_sellers, key=lambda s: s.leads_today or 0)


async def select_by_city_and_specialty(
    sellers: List[Seller],
    lead_city: Optional[str],
    lead_specialty: Optional[str],
) -> Optional[Seller]:
    """
    Seleciona vendedor pela cidade E especialidade do lead.
    """
    if not sellers:
        return None
    
    # Primeiro filtra por cidade
    city_sellers = []
    if lead_city:
        lead_city_lower = lead_city.lower().strip()
        for seller in sellers:
            if seller.cities:
                seller_cities = [c.lower().strip() for c in seller.cities]
                if lead_city_lower in seller_cities:
                    city_sellers.append(seller)
    
    # Depois filtra por especialidade
    if city_sellers and lead_specialty:
        lead_specialty_lower = lead_specialty.lower().strip()
        matching_sellers = []
        for seller in city_sellers:
            if seller.specialties:
                seller_specialties = [s.lower().strip() for s in seller.specialties]
                if lead_specialty_lower in seller_specialties:
                    matching_sellers.append(seller)
        
        if matching_sellers:
            return min(matching_sellers, key=lambda s: s.leads_today or 0)
    
    # Se não achou com os dois critérios, tenta só cidade
    if city_sellers:
        return min(city_sellers, key=lambda s: s.leads_today or 0)
    
    # Se não achou por cidade, tenta só especialidade
    if lead_specialty:
        return await select_by_specialty(sellers, lead_specialty)
    
    return None


async def select_by_priority(
    sellers: List[Seller],
) -> Optional[Seller]:
    """
    Seleciona vendedor com maior prioridade.
    Em caso de empate, pega o com menos leads hoje.
    """
    if not sellers:
        return None
    
    # Ordena por prioridade (desc) e leads_today (asc)
    sorted_sellers = sorted(
        sellers, 
        key=lambda s: (-s.priority, s.leads_today or 0)
    )
    
    return sorted_sellers[0]


async def select_least_busy(
    sellers: List[Seller],
) -> Optional[Seller]:
    """
    Seleciona vendedor com menos leads hoje.
    """
    if not sellers:
        return None
    
    return min(sellers, key=lambda s: s.leads_today or 0)


# ==========================================
# FUNÇÃO PRINCIPAL DE DISTRIBUIÇÃO
# ==========================================

async def distribute_lead(
    db: AsyncSession,
    lead: Lead,
    tenant: Tenant,
) -> dict:
    """
    Distribui um lead para o vendedor apropriado.
    
    Returns:
        {
            "success": bool,
            "seller": Seller ou None,
            "method": str (método usado),
            "fallback_used": bool,
            "message": str,
        }
    """
    settings = tenant.settings or {}
    distribution_config = {
        **DEFAULT_DISTRIBUTION_CONFIG,
        **settings.get("distribution", {}),
    }
    
    method = distribution_config.get("method", "round_robin")
    fallback = distribution_config.get("fallback", "manager")
    respect_limit = distribution_config.get("respect_daily_limit", True)
    respect_availability = distribution_config.get("respect_availability", True)
    
    # Busca vendedores disponíveis
    sellers = await get_available_sellers(
        db, tenant.id, respect_limit, respect_availability
    )
    
    if not sellers:
        return {
            "success": False,
            "seller": None,
            "method": method,
            "fallback_used": True,
            "message": "Nenhum vendedor disponível",
        }
    
    selected_seller = None
    fallback_used = False
    
    # Extrai dados do lead para matching
    lead_city = lead.city
    lead_specialty = None
    if lead.custom_data:
        # Tenta pegar interesse/tipo do custom_data
        lead_specialty = (
            lead.custom_data.get("interest_type") or
            lead.custom_data.get("specialty") or
            lead.custom_data.get("service_type") or
            lead.custom_data.get("tipo_interesse")
        )
    
    # Aplica método de distribuição
    if method == "round_robin":
        last_index = distribution_config.get("last_seller_index", 0)
        selected_seller, new_index = await select_by_round_robin(sellers, last_index)
        
        # Atualiza índice no settings
        if selected_seller:
            new_distribution = {**distribution_config, "last_seller_index": new_index}
            tenant.settings = {**settings, "distribution": new_distribution}
    
    elif method == "by_city":
        selected_seller = await select_by_city(sellers, lead_city)
    
    elif method == "by_specialty":
        selected_seller = await select_by_specialty(sellers, lead_specialty)
    
    elif method == "by_city_specialty":
        selected_seller = await select_by_city_and_specialty(
            sellers, lead_city, lead_specialty
        )
    
    elif method == "by_priority":
        selected_seller = await select_by_priority(sellers)
    
    elif method == "least_busy":
        selected_seller = await select_least_busy(sellers)
    
    elif method == "manual":
        # Manual não distribui automaticamente
        return {
            "success": True,
            "seller": None,
            "method": "manual",
            "fallback_used": False,
            "message": "Distribuição manual - aguardando gestor",
        }
    
    # Se não encontrou vendedor, aplica fallback
    if not selected_seller:
        fallback_used = True
        
        if fallback == "round_robin":
            last_index = distribution_config.get("last_seller_index", 0)
            selected_seller, new_index = await select_by_round_robin(sellers, last_index)
            if selected_seller:
                new_distribution = {**distribution_config, "last_seller_index": new_index}
                tenant.settings = {**settings, "distribution": new_distribution}
        
        elif fallback == "manager":
            # Não atribui a nenhum vendedor, vai pro gestor
            return {
                "success": True,
                "seller": None,
                "method": method,
                "fallback_used": True,
                "message": "Nenhum vendedor compatível - enviado para gestor",
            }
        
        elif fallback == "queue":
            # Deixa na fila
            return {
                "success": True,
                "seller": None,
                "method": method,
                "fallback_used": True,
                "message": "Lead na fila - aguardando vendedor disponível",
            }
    
    # Atribui o lead ao vendedor
    if selected_seller:
        await assign_lead_to_seller(
            db=db,
            lead=lead,
            seller=selected_seller,
            tenant=tenant,
            method=method if not fallback_used else f"{method}_fallback",
        )
        
        return {
            "success": True,
            "seller": selected_seller,
            "method": method,
            "fallback_used": fallback_used,
            "message": f"Lead atribuído para {selected_seller.name}",
        }
    
    return {
        "success": False,
        "seller": None,
        "method": method,
        "fallback_used": True,
        "message": "Não foi possível distribuir o lead",
    }


async def assign_lead_to_seller(
    db: AsyncSession,
    lead: Lead,
    seller: Seller,
    tenant: Tenant,
    method: str,
    reason: str = None,
) -> LeadAssignment:
    """
    Atribui um lead a um vendedor e registra o histórico.
    """
    now = datetime.utcnow()
    today = date.today()
    
    # Atualiza o lead
    lead.assigned_seller_id = seller.id
    lead.assigned_at = now
    lead.assignment_method = method
    
    # Atualiza contadores do vendedor
    if seller.leads_today_date != today:
        seller.leads_today = 1
        seller.leads_today_date = today
    else:
        seller.leads_today += 1
    
    seller.total_leads += 1
    seller.last_lead_at = now
    
    # Cria registro de atribuição
    assignment = LeadAssignment(
        tenant_id=tenant.id,
        lead_id=lead.id,
        seller_id=seller.id,
        assignment_method=method,
        reason=reason,
        assigned_at=now,
        status="pending",
    )
    db.add(assignment)
    
    # Cria notificação
    notification = Notification(
        tenant_id=tenant.id,
        type="lead_assigned",
        title="📥 Novo Lead Atribuído",
        message=f"Lead {lead.name or 'Novo'} foi atribuído para {seller.name}",
        reference_type="lead",
        reference_id=lead.id,
        read=False,
    )
    db.add(notification)
    
    return assignment


async def get_lead_specialty_from_niche(
    lead: Lead,
    niche: str,
) -> Optional[str]:
    """
    Extrai a especialidade do lead baseado no nicho.
    """
    if not lead.custom_data:
        return None
    
    # Mapeamento de campos por nicho
    specialty_fields = {
        "real_estate": ["interest_type", "tipo_interesse", "tipo"],
        "healthcare": ["specialty", "especialidade", "servico"],
        "fitness": ["goal", "objetivo", "modalidade"],
        "education": ["course_interest", "curso", "area"],
        "services": ["service_type", "tipo_servico", "servico"],
    }
    
    fields_to_check = specialty_fields.get(niche, ["specialty", "type", "tipo"])
    
    for field in fields_to_check:
        value = lead.custom_data.get(field)
        if value:
            return value
    
    return None