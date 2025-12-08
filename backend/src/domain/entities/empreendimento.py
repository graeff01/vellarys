"""
ENTIDADE: EMPREENDIMENTO
=========================

Cadastro de empreendimentos imobiliários para fluxo especializado de atendimento.
Disponível apenas para tenants com nicho "realestate" ou "imobiliaria".

Quando um lead envia uma mensagem contendo um dos gatilhos configurados,
a IA carrega as informações do empreendimento e segue o fluxo de qualificação específico.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Boolean, ForeignKey, 
    DateTime, func, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.mutable import MutableDict, MutableList

from src.domain.entities.base import Base, TimestampMixin


class Empreendimento(Base, TimestampMixin):
    """
    Representa um empreendimento imobiliário cadastrado pelo tenant.
    
    Campos principais:
    - Informações básicas (nome, status, URL)
    - Gatilhos de detecção (palavras que ativam o fluxo)
    - Localização completa
    - Características (tipologias, metragens, etc)
    - Valores e condições
    - Diferenciais e lazer
    - Perguntas de qualificação específicas
    - Destino dos leads (vendedor específico ou rodízio)
    """
    
    __tablename__ = "empreendimentos"
    
    # =========================================================================
    # IDENTIFICAÇÃO
    # =========================================================================
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("tenants.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # =========================================================================
    # INFORMAÇÕES BÁSICAS
    # =========================================================================
    
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="lancamento"
    )  # lancamento, em_obras, pronto_para_morar
    
    url_landing_page: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    imagem_destaque: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # =========================================================================
    # GATILHOS DE DETECÇÃO
    # =========================================================================
    
    # Palavras/frases que ativam este empreendimento
    # Ex: ["essence", "essence residence", "portal de investimento"]
    gatilhos: Mapped[list] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        default=list,
        nullable=False
    )
    
    # Prioridade de detecção (maior = mais prioritário)
    # Útil quando um lead menciona termos que casam com múltiplos empreendimentos
    prioridade: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # =========================================================================
    # LOCALIZAÇÃO
    # =========================================================================
    
    endereco: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    bairro: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cidade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estado: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    cep: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Texto livre sobre localização e diferenciais do local
    descricao_localizacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Coordenadas para mapa (opcional)
    latitude: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    longitude: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # =========================================================================
    # CARACTERÍSTICAS DO EMPREENDIMENTO
    # =========================================================================
    
    # Descrição geral do empreendimento
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tipologias disponíveis: ["1 dormitório", "2 dormitórios", "3 dormitórios", "cobertura"]
    tipologias: Mapped[list] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        default=list,
        nullable=True
    )
    
    # Faixa de metragem: "45m² a 120m²"
    metragem_minima: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metragem_maxima: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Estrutura do empreendimento
    torres: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    andares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unidades_por_andar: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_unidades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Vagas de garagem: "1 a 3 vagas"
    vagas_minima: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vagas_maxima: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Previsão de entrega
    previsao_entrega: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data_entrega: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # =========================================================================
    # VALORES E CONDIÇÕES
    # =========================================================================
    
    # Faixa de preço
    preco_minimo: Mapped[Optional[float]] = mapped_column(nullable=True)
    preco_maximo: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Condições de pagamento
    aceita_financiamento: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aceita_fgts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aceita_permuta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aceita_consorcio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Texto livre sobre condições especiais
    condicoes_especiais: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # =========================================================================
    # DIFERENCIAIS E LAZER
    # =========================================================================
    
    # Lista de itens de lazer: ["piscina", "academia", "churrasqueira", "salão de festas"]
    itens_lazer: Mapped[list] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        default=list,
        nullable=True
    )
    
    # Diferenciais do empreendimento: ["vista para o mar", "varanda gourmet", "smart home"]
    diferenciais: Mapped[list] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        default=list,
        nullable=True
    )
    
    # =========================================================================
    # QUALIFICAÇÃO ESPECÍFICA
    # =========================================================================
    
    # Perguntas que a IA deve fazer para leads deste empreendimento
    # Sobrescreve ou complementa as perguntas padrão do tenant
    perguntas_qualificacao: Mapped[list] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        default=list,
        nullable=True
    )
    
    # Informações adicionais para a IA (instruções específicas)
    instrucoes_ia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # =========================================================================
    # DESTINO DOS LEADS
    # =========================================================================
    
    # ID do vendedor específico (se None, usa distribuição padrão do tenant)
    vendedor_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Método de distribuição específico deste empreendimento
    # Se None, usa o método padrão do tenant
    metodo_distribuicao: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Notificar gestor imediatamente quando chegar lead deste empreendimento
    notificar_gestor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # WhatsApp específico para notificação (se diferente do gestor padrão)
    whatsapp_notificacao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # =========================================================================
    # MÉTRICAS
    # =========================================================================
    
    # Contadores para relatórios
    total_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_qualificados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_convertidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # =========================================================================
    # DADOS EXTRAS (JSONB para flexibilidade)
    # =========================================================================
    
    # Campos extras que podem variar por empreendimento
    # Ex: {"construtora": "XYZ", "incorporadora": "ABC", "registro": "123456"}
    dados_extras: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )
    
    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    
    # Relacionamento com Tenant
    tenant = relationship("Tenant", back_populates="empreendimentos")
    
    # Relacionamento com Seller (vendedor específico)
    vendedor = relationship("Seller", back_populates="empreendimentos")
    
    # =========================================================================
    # ÍNDICES
    # =========================================================================
    
    __table_args__ = (
        # Índice composto para busca por tenant + ativo
        Index("ix_empreendimentos_tenant_ativo", "tenant_id", "ativo"),
        # Índice para busca por slug dentro do tenant
        Index("ix_empreendimentos_tenant_slug", "tenant_id", "slug", unique=True),
    )
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def matches_message(self, message: str) -> bool:
        """
        Verifica se a mensagem contém algum dos gatilhos deste empreendimento.
        
        Args:
            message: Mensagem do lead (já em lowercase)
            
        Returns:
            True se algum gatilho foi encontrado
        """
        if not self.gatilhos:
            return False
        
        message_lower = message.lower()
        
        for gatilho in self.gatilhos:
            if gatilho.lower() in message_lower:
                return True
        
        return False
    
    def get_faixa_preco_formatada(self) -> str:
        """Retorna a faixa de preço formatada."""
        if self.preco_minimo and self.preco_maximo:
            return f"R$ {self.preco_minimo:,.0f} a R$ {self.preco_maximo:,.0f}".replace(",", ".")
        elif self.preco_minimo:
            return f"A partir de R$ {self.preco_minimo:,.0f}".replace(",", ".")
        elif self.preco_maximo:
            return f"Até R$ {self.preco_maximo:,.0f}".replace(",", ".")
        return "Consulte-nos"
    
    def get_faixa_metragem_formatada(self) -> str:
        """Retorna a faixa de metragem formatada."""
        if self.metragem_minima and self.metragem_maxima:
            return f"{self.metragem_minima}m² a {self.metragem_maxima}m²"
        elif self.metragem_minima:
            return f"A partir de {self.metragem_minima}m²"
        elif self.metragem_maxima:
            return f"Até {self.metragem_maxima}m²"
        return ""
    
    def get_condicoes_pagamento(self) -> list[str]:
        """Retorna lista de condições de pagamento aceitas."""
        condicoes = []
        if self.aceita_financiamento:
            condicoes.append("Financiamento bancário")
        if self.aceita_fgts:
            condicoes.append("FGTS")
        if self.aceita_permuta:
            condicoes.append("Permuta")
        if self.aceita_consorcio:
            condicoes.append("Consórcio")
        return condicoes
    
    def to_ai_context(self) -> dict:
        """
        Converte o empreendimento para contexto da IA.
        Usado no prompt para informar a IA sobre o empreendimento.
        """
        context = {
            "nome": self.nome,
            "status": self.status,
            "descricao": self.descricao,
        }
        
        # Localização
        if self.endereco or self.bairro or self.cidade:
            context["localizacao"] = {
                "endereco": self.endereco,
                "bairro": self.bairro,
                "cidade": self.cidade,
                "estado": self.estado,
                "descricao": self.descricao_localizacao,
            }
        
        # Características
        if self.tipologias:
            context["tipologias"] = self.tipologias
        
        metragem = self.get_faixa_metragem_formatada()
        if metragem:
            context["metragem"] = metragem
        
        if self.previsao_entrega:
            context["previsao_entrega"] = self.previsao_entrega
        
        # Valores
        context["faixa_preco"] = self.get_faixa_preco_formatada()
        context["condicoes_pagamento"] = self.get_condicoes_pagamento()
        
        if self.condicoes_especiais:
            context["condicoes_especiais"] = self.condicoes_especiais
        
        # Lazer e diferenciais
        if self.itens_lazer:
            context["lazer"] = self.itens_lazer
        
        if self.diferenciais:
            context["diferenciais"] = self.diferenciais
        
        # Perguntas específicas
        if self.perguntas_qualificacao:
            context["perguntas_qualificacao"] = self.perguntas_qualificacao
        
        # Instruções extras
        if self.instrucoes_ia:
            context["instrucoes_especiais"] = self.instrucoes_ia
        
        return context
    
    def __repr__(self) -> str:
        return f"<Empreendimento(id={self.id}, nome='{self.nome}', tenant_id={self.tenant_id})>"