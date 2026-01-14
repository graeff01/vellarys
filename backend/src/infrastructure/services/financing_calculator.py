import math
from typing import Dict

class FinancingCalculator:
    """
    Calculadora para simulações rápidas de financiamento.
    SAC (Sistema de Amortização Constante) e PRICE.
    """

    @staticmethod
    def simulate_price(valor_financiado: float, taxa_anual: float, meses: int) -> Dict:
        """Simulação Tabela Price."""
        taxa_mensal = (1 + taxa_anual/100)**(1/12) - 1
        
        parcela = (valor_financiado * taxa_mensal) / (1 - (1 + taxa_mensal)**(-meses))
        custo_total = parcela * meses
        juros_totais = custo_total - valor_financiado
        
        return {
            "tipo": "PRICE",
            "parcela_fixa": round(parcela, 2),
            "custo_total": round(custo_total, 2),
            "juros_totais": round(juros_totais, 2),
            "meses": meses
        }

    @staticmethod
    def simulate_sac(valor_financiado: float, taxa_anual: float, meses: int) -> Dict:
        """Simulação Tabela SAC."""
        taxa_mensal = (1 + taxa_anual/100)**(1/12) - 1
        amortizacao = valor_financiado / meses
        
        primeira_parcela = amortizacao + (valor_financiado * taxa_mensal)
        ultima_parcela = amortizacao + (amortizacao * taxa_mensal)
        
        # Média simples para custo total aproximado no SAC
        custo_total = (primeira_parcela + ultima_parcela) / 2 * meses
        juros_totais = custo_total - valor_financiado
        
        return {
            "tipo": "SAC",
            "primeira_parcela": round(primeira_parcela, 2),
            "ultima_parcela": round(ultima_parcela, 2),
            "custo_total": round(custo_total, 2),
            "juros_totais": round(juros_totais, 2),
            "meses": meses
        }

    @staticmethod
    def get_context_description() -> str:
        return """
        CALCULADORA DE FINANCIAMENTO (Simulação):
        - Taxa média atual: 10% a 12% ao ano.
        - Prazo comum: 360 meses (30 anos).
        - Entrada mínima: Geralmente 20% do valor do imóvel.
        """
