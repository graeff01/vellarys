# Walkthrough: Active Intelligence Features

Implementei os dois pilares estratégicos para diferenciar o Vellarys: **Morning Briefing** (Email) e **Intelligence Injection** (UI).

## 1. Intelligence Injection (No Card do Lead)

Agora, ao abrir um Lead, o corretor verá um card amarelo **"Intelligence Injection"** no topo da lista de conversas.

### O que ele faz:
*   **Analisa** as últimas 10 mensagens da conversa.
*   **Identifica** o tópico chave (ex: "Segurança", "Preço", "Localização").
*   **Calcula** o sentimento do cliente.
*   **Sugere** uma ação tática imediata (ex: "Ofereça o imóvel X", "Ligue agora").
*   **Fallback:** Se não houver conversa, ele dá dicas baseadas na qualificação do lead (Cold/Hot).

### Arquivos Modificados:
*   `backend/src/infrastructure/services/sales_advisor_service.py`: Cérebro da análise.
*   `backend/src/api/routes/leads.py`: Novo endpoint `GET /leads/{id}/ai-insights`.
*   `frontend/src/components/leads/lead-intelligence-card.tsx`: Componente visual (Yellow Sticky Note).
*   `frontend/src/app/dashboard/leads/[id]/page.tsx`: Integração na tela.

---

## 2. Morning Briefing (Email às 06:00)

O sistema agora tem um serviço capaz de gerar um **Email Executivo "Edificado"** e enviar para os gestores.

### O que ele faz:
*   **Coleta métricas:** Vendas do mês, Meta (fixada em 2M para teste), Leads de ontem.
*   **Deal Rescue:** Identifica top 5 leads **QUENTES** que não receberam resposta há 24h.
*   **Formato Premium:** Email HTML responsivo, limpo e direto ao ponto.

### Como Testar:
Como não tenho acesso ao cronjob do servidor, criei um **gatilho manual** para você testar agora:

**Endpoint:** `POST /api/v1/manager/copilot/trigger-briefing`
**Body:** (Opcional)
```json
{
  "target_email": "douglas@velocebm.com"
}
```
**Auth:** Requer token de Admin ou Gestor.

### Arquivos Modificados:
*   `backend/src/infrastructure/services/morning_briefing_service.py`: Lógica de geração e envio.
*   `backend/src/api/routes/manager_ai.py`: Endpoint de gatilho manual.

---

## Próximos Passos Sugeridos
1.  **Configurar Cron Job:** Adicionar chamada ao `generate_and_send` no scheduler do sistema (Celery/APScheduler) para rodar às 06:00.
2.  **Meta Dinâmica:** Conectar a meta de receita a uma tabela de configurações do Tenant.
