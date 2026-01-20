# 📚 RUNBOOK OPERACIONAL - VELLARYS
**Versão:** 2.0  
**Última Atualização:** 20/01/2026  
**Responsável:** Equipe Vellarys

---

## 📋 ÍNDICE

1. [Arquitetura do Sistema](#arquitetura-do-sistema)
2. [Configuração de Ambiente](#configuração-de-ambiente)
3. [Deploy e Releases](#deploy-e-releases)
4. [Adicionando Novo Cliente (Tenant)](#adicionando-novo-cliente-tenant)
5. [Monitoramento e Alertas](#monitoramento-e-alertas)
6. [Troubleshooting Comum](#troubleshooting-comum)
7. [Procedimentos de Emergência](#procedimentos-de-emergência)
8. [Escalabilidade](#escalabilidade)
9. [Backup e Recuperação](#backup-e-recuperação)
10. [Contatos de Escalonamento](#contatos-de-escalonamento)

---

## 🏗️ ARQUITETURA DO SISTEMA

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   WhatsApp      │────▶│    Backend      │────▶│   PostgreSQL    │
│   (Z-API/360)   │     │    (FastAPI)    │     │   (Railway)     │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │     OpenAI      │
                        │    (GPT-4o)     │
                        └─────────────────┘
```

### Componentes:
- **Backend:** FastAPI + Python 3.11 (Railway)
- **Frontend:** Next.js 16 + React 19 (Railway)
- **Banco:** PostgreSQL 16 (Railway)
- **Cache:** Redis (Railway - opcional mas recomendado)
- **IA:** OpenAI GPT-4o
- **WhatsApp:** Z-API / 360Dialog / Gupshup
- **Monitoramento:** Sentry + UptimeRobot

---

## ⚙️ CONFIGURAÇÃO DE AMBIENTE

### Variáveis Obrigatórias (Backend)

```bash
# Core
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=chave-secreta-forte-256-bits
ENVIRONMENT=production
OPENAI_API_KEY=sk-xxx

# Superadmin
SUPERADMIN_EMAIL=admin@empresa.com
SUPERADMIN_PASSWORD=senha-forte-123
SUPERADMIN_TENANT_NAME=Empresa Admin
SUPERADMIN_TENANT_SLUG=empresa-admin
```

### Variáveis Opcionais

```bash
# Redis (RECOMENDADO para escala > 3 clientes)
REDIS_URL=redis://default:xxx@host:6379

# Pool de Banco (ajustar conforme carga)
DB_POOL_SIZE=15
DB_MAX_OVERFLOW=30

# WhatsApp
ZAPI_INSTANCE_ID=xxx
ZAPI_TOKEN=xxx
ZAPI_CLIENT_TOKEN=xxx

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx

# Push Notifications
VAPID_PUBLIC_KEY=xxx
VAPID_PRIVATE_KEY=xxx
```

---

## 🚀 DEPLOY E RELEASES

### Deploy Automático (Recomendado)

1. Push para `main` dispara deploy automático via Railway
2. CI/CD valida testes antes do deploy
3. Rollback automático se health check falhar

### Deploy Manual

```bash
# Backend
cd backend
railway up

# Frontend
cd frontend
railway up
```

### Checklist Pré-Deploy

- [ ] Testes locais passando (`pytest -v`)
- [ ] Lint sem erros (`ruff check .`)
- [ ] Branch atualizada com main
- [ ] Variáveis de ambiente revisadas
- [ ] Backup do banco realizado

### Rollback

```bash
# Via Railway CLI
railway rollback

# Ou via Dashboard Railway
# Settings > Deployments > Rollback to previous
```

---

## 🏢 ADICIONANDO NOVO CLIENTE (TENANT)

### Passo 1: Criar Tenant no Sistema

```bash
# Via API (requer token de superadmin)
curl -X POST https://api.vellarys.app/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Imobiliária XYZ",
    "slug": "imobiliaria-xyz",
    "niche_id": 1
  }'
```

### Passo 2: Configurar WhatsApp

1. Acessar dashboard como admin do tenant
2. Settings > Integrações > WhatsApp
3. Configurar credenciais Z-API ou 360Dialog:
   - Instance ID
   - Token
   - Client Token (Z-API)
4. Testar webhook: enviar mensagem de teste

### Passo 3: Configurar Prompt da IA

1. Settings > IA > Prompt do Sistema
2. Personalizar tom e informações da empresa
3. Testar no Simulator

### Passo 4: Adicionar Usuários

1. Usuários > Novo Usuário
2. Definir role: admin, seller, viewer
3. Enviar credenciais ao cliente

### Passo 5: Importar Dados (se aplicável)

1. Products > Importar CSV
2. Verificar triggers de produtos
3. Testar busca de imóveis

### Checklist de Onboarding

- [ ] Tenant criado
- [ ] WhatsApp configurado e testado
- [ ] Pelo menos 1 admin criado
- [ ] Prompt personalizado
- [ ] Produtos importados (se houver)
- [ ] Primeira conversa de teste OK
- [ ] Handoff testado
- [ ] Cliente treinado no dashboard

---

## 📊 MONITORAMENTO E ALERTAS

### Endpoints de Health Check

| Endpoint | Descrição | Frequência |
|----------|-----------|------------|
| `/api/health` | Status básico | 1 min |
| `/api/health/detailed` | Status completo | 5 min |

### UptimeRobot (Monitoramento Externo)

- URL: `https://api.vellarys.app/api/health`
- Intervalo: 1 minuto
- Alerta: Email + Slack

### Sentry (Erros)

- Dashboard: sentry.io/vellarys
- Alertas configurados para:
  - Erros críticos (imediato)
  - Taxa de erro > 1% (5 min)
  - Performance degradada (10 min)

### Métricas Chave (KPIs)

| Métrica | Threshold OK | Alerta |
|---------|--------------|--------|
| Response Time API | < 500ms | > 1s |
| Error Rate | < 0.1% | > 1% |
| DB Connections | < 80% | > 90% |
| Memory Usage | < 70% | > 85% |
| OpenAI Latency | < 10s | > 30s |

---

## 🔧 TROUBLESHOOTING COMUM

### Problema: Lead não recebe resposta

**Possíveis causas:**
1. Webhook não está chegando
2. Rate limit excedido
3. Erro na OpenAI
4. Tenant desativado

**Diagnóstico:**
```bash
# Ver logs recentes
railway logs --tail 100 | grep "lead_id"

# Verificar webhook
curl -X POST https://api.vellarys.app/api/v1/webhook/dialog360 \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Problema: Dashboard lento

**Possíveis causas:**
1. Query sem índice
2. Pool de conexões esgotado
3. Muitos dados sem paginação

**Diagnóstico:**
```bash
# Verificar conexões do banco
SELECT count(*) FROM pg_stat_activity;

# Queries lentas
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

### Problema: Mensagens duplicadas

**Causa:** Webhook sendo chamado múltiplas vezes

**Solução:** Verificar idempotência via `external_message_id`

### Problema: OpenAI timeout

**Possíveis causas:**
1. Prompt muito longo
2. OpenAI sobrecarregado
3. Rede instável

**Solução:**
1. Verificar tamanho do prompt
2. Aguardar e tentar novamente
3. Verificar status.openai.com

---

## 🚨 PROCEDIMENTOS DE EMERGÊNCIA

### Sistema Completamente Fora

1. Verificar status Railway: status.railway.app
2. Verificar logs: `railway logs`
3. Tentar restart: `railway restart`
4. Se persistir, escalonar para Lead

### Vazamento de Dados Suspeitado

1. **IMEDIATO:** Bloquear acesso afetado
2. Coletar evidências (logs, audit)
3. Notificar responsável LGPD
4. Documentar incidente

### OpenAI Indisponível

1. Sistema usa fallback automático
2. Leads recebem mensagem genérica
3. Monitorar retorno do serviço
4. Processar fila quando voltar

### Banco de Dados Corrompido

1. Parar aplicação imediatamente
2. Restaurar último backup
3. Verificar integridade
4. Comunicar clientes afetados

---

## 📈 ESCALABILIDADE

### Limites Atuais

| Recurso | Limite Soft | Limite Hard |
|---------|-------------|-------------|
| Tenants | 10 | 50 |
| Leads/tenant/dia | 500 | 2000 |
| Mensagens/min/tenant | 100 | 500 |
| Conexões DB | 45 | 60 |

### Sinais de que Precisa Escalar

- ⚠️ Response time > 1s (média)
- ⚠️ Pool de conexões > 80%
- ⚠️ Filas de mensagem crescendo
- ⚠️ Timeouts frequentes

### Como Escalar

1. **Banco:** Aumentar tier no Railway
2. **Pool:** Ajustar `DB_POOL_SIZE` e `DB_MAX_OVERFLOW`
3. **Cache:** Ativar Redis se não estiver ativo
4. **Horizontal:** Adicionar réplicas (requer Redis)

---

## 💾 BACKUP E RECUPERAÇÃO

### Backup Automático (Railway)

- Tipo: Snapshots diários
- Retenção: 7 dias
- Localização: Railway (mesmo datacenter)

### Backup Manual

```bash
# Exportar banco completo
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Apenas dados críticos
pg_dump $DATABASE_URL -t leads -t messages -t tenants > backup_core.sql
```

### Recuperação

```bash
# Restaurar do backup
psql $DATABASE_URL < backup_20260120.sql

# Ou via Railway Dashboard
# Database > Backups > Restore
```

---

## 📞 CONTATOS DE ESCALONAMENTO

### Nível 1: Operações
- **Quem:** Equipe de Suporte
- **Quando:** Problemas de uso, dúvidas, bugs simples
- **Contato:** suporte@vellarys.app

### Nível 2: Desenvolvimento
- **Quem:** Equipe Dev
- **Quando:** Bugs complexos, features urgentes
- **Contato:** dev@vellarys.app

### Nível 3: Emergência
- **Quem:** Tech Lead
- **Quando:** Sistema fora, vazamento de dados, SLA violado
- **Contato:** [Definir telefone/WhatsApp]

### Externos
- **Railway Support:** support@railway.app
- **OpenAI:** support@openai.com
- **Z-API:** suporte@z-api.io

---

## 📝 HISTÓRICO DE MUDANÇAS

| Data | Versão | Mudança |
|------|--------|---------|
| 20/01/2026 | 2.0 | Criação do runbook completo |
| - | - | - |

---

*Mantenha este documento atualizado após qualquer mudança significativa no sistema.*
