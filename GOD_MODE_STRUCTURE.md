# 🦅 GOD MODE: O Painel de Controle do Sócio Fundador (Velaris Admin 2.0)

Este documento define a estrutura do **"Admin Master"**, projetado não apenas para administração técnica, mas para **Governança de Negócio e Infraestrutura**. O objetivo é responder às perguntas que tiram o sono do fundador em 5 segundos.

---

## 🎯 1. O "Head-Up Display" (Topo da Tela - Visão Instantânea)
*Objetivo: Saber se o negócio está vivo e dando lucro agora.*

| Métrica | O que mostra | Por que importa? |
| :--- | :--- | :--- |
| **Status Global** | 🟢 🟡 🔴 (Sinalizador Geral) | "O sistema caiu?" (Resume DB, Redis, WhatsApp, OpenAI) |
| **MRR Estimado** | `R$ 54.300,00` (+12% vs mês anterior) | Saúde financeira do SaaS. |
| **Burn Rate (Hoje)** | `R$ 145,30` (Custo OpenAI/Infra hoje) | "Quanto estamos gastando por minuto?" |
| **Margem Bruta** | `82%` | Eficiência do negócio. |
| **Usuários Online** | `42` ativos agora | Pulso real de uso. |

---

## 📊 2. Seção Financeira & Growth (O "CFO Virtual")
*Objetivo: Identificar onde ganhar dinheiro (Upsell) e onde não perder (Churn).*

### A. Tabela de Risco (Churn Prediction) ⚠️
*Lista de clientes que estão "esfriando".*
*   **Critério:** Nenhuma mensagem em 48h OU Queda brusca de volume (-50% vs semana anterior).
*   **Ação:** Botão "WhatsApp Gestor" (abre conversa direta com o dono da imobiliária).

### B. Top Consumidores (Upsell Opportunities) 🚀
*Lista de clientes que estão "estourando" o plano.*
*   **Dados:** Nome, Plano Atual, % de Uso de Tokens, Qtd Leads.
*   **Insight:** "Cliente X atingiu 90% da cota. Oferecer plano Enterprise."

### C. Custo por Lead (Unit Economics)
*   Gráfico de linha comparando: Custo de Infra vs. Receita por Lead Gerado.
*   Mostra se a IA está ficando mais barata ou mais cara de operar.

---

## 🛠️ 3. Seção CTO & Infraestrutura (O "Mecânico")
*Objetivo: Diagnóstico técnico sem precisar abrir o terminal.*

### A. Monitor de Latência (SLA)
*   **OpenAI:** `1.2s` (Médio) | `4.5s` (P99)
*   **WhatsApp Webhook:** `200ms`
*   **Database:** `45ms`
* *Se o OpenAI subir para 10s, você sabe que o problema é lá, não no seu código.*

### B. Fila de Processamento (RabbitMQ/Redis)
*   **Mensagens na Fila:** `0` (Ideal) ou `543` (Gargalo).
*   **Falhas de Envio:** Contador de mensagens que falharam nas últimas 24h.

### C. Logs de Erro Agrupados
*   Em vez de um log bruto, um agrupamento inteligente:
    *   `Error: Rate Limit Exceeded` (45x na última hora) → *Ação Crítica!*
    *   `Error: Phone number invalid` (12x) → *Baixa prioridade.*

---

## ⚡ 4. Controle Operacional (God Actions)
*Botões perigosos que só o Sócio tem acesso.*

*   🔴 **Kill Switch Global:** Pausa toas as IAs imediatamente (em caso de bug crítico/alucinação em massa).
*   🔄 **Force Restart Workers:** Reinicia os consumers de fila se travarem.
*   📢 **Broadcast de Sistema:** Envia um banner para o dashboard de TODOS os clientes ("Manutenção programada às 22h").
*   🕵️ **Masquerade Mode:** "Entrar como Cliente X" (Já implementado, mas destacar aqui).

---

## 🔗 5. Integrações & Ecossistema
*Monitoramento das pontas soltas.*
*   **Status dos Webhooks:** 99.8% de sucesso na entrega para CRMs dos clientes.
*   **Quota de API:** Barra de progresso do limite mensal da Meta/WABA.

---

## 📝 Próximos Passos de Implementação
1.  **Backend:** Criar endpoint que agrega `tokens_used` da tabela `Messages` x Custo do Token + Custo fixo do Plano (para Burn Rate).
2.  **Frontend:** Atualizar `ceo-dashboard.tsx` para incluir os cards financeiros e de infra.
3.  **Monitoramento:** Instalar Sentry ou Promotheus para alimentar os dados de latência/erros.
