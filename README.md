# Vellarys - Plataforma de IA para Atendimento B2B

Sistema multi-tenant de atendimento ao cliente via IA, especializado no mercado imobiliario. Qualifica leads automaticamente, distribui para vendedores e oferece CRM com inbox em tempo real.

## Arquitetura

```
                    ┌─────────────────┐
                    │    Frontend     │
                    │  Next.js + React│
                    └────────┬────────┘
                             │
┌─────────────────┐  ┌──────┴──────────┐  ┌─────────────────┐
│   WhatsApp      │──│    Backend      │──│   PostgreSQL 16  │
│ Z-API/360Dialog │  │   FastAPI       │  │   (Railway)      │
│ Gupshup/Twilio  │  └──────┬──────────┘  └─────────────────┘
└─────────────────┘         │
                    ┌───────┼───────┐
                    │       │       │
               ┌────┴──┐ ┌─┴────┐ ┌┴──────┐
               │OpenAI │ │Redis │ │Sentry │
               │GPT-4o │ │Cache │ │Errors │
               └───────┘ └──────┘ └───────┘
```

## Stack

| Camada | Tecnologia |
|--------|-----------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Python 3.11 |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **Banco** | PostgreSQL 16 com pgvector (busca semantica) |
| **Cache** | Redis (rate limiting, cache de sessoes) |
| **IA** | OpenAI GPT-4o + Embeddings (text-embedding-3-small) |
| **WhatsApp** | Z-API, 360Dialog, Gupshup, Twilio |
| **Monitoramento** | Sentry + UptimeRobot |
| **Deploy** | Railway (backend + frontend + banco) |

## Estrutura do Projeto

```
vellarys/
├── backend/
│   ├── src/
│   │   ├── api/              # Rotas, schemas, middlewares
│   │   │   ├── routes/       # Endpoints (auth, leads, webhook, etc)
│   │   │   ├── schemas/      # Pydantic models
│   │   │   └── dependencies.py
│   │   ├── application/      # Casos de uso (process_message, etc)
│   │   ├── domain/           # Entidades, enums, regras de negocio
│   │   │   ├── entities/     # Models SQLAlchemy
│   │   │   └── services/     # Lead intelligence, qualifier
│   │   ├── infrastructure/   # Integracao externa
│   │   │   ├── database/     # Engine, migrations
│   │   │   ├── services/     # Auth, SSE, WhatsApp, Redis, etc
│   │   │   └── llm/          # OpenAI provider
│   │   └── config.py         # Settings centralizados
│   ├── alembic/              # Migrations de banco
│   ├── tests/                # Testes automatizados
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Rotas Next.js (App Router)
│   │   ├── components/       # Componentes React
│   │   └── lib/              # Utilitarios, API client
│   └── package.json
└── docker-compose.yml
```

## Como Rodar (Desenvolvimento)

### 1. Backend

```bash
cd backend
cp .env.example .env
# Edite o .env com suas credenciais

# Instalar dependencias
pip install -r requirements.txt

# Rodar migrations
alembic upgrade head

# Iniciar servidor
uvicorn src.api.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Docker (alternativo)

```bash
docker compose up -d
docker compose logs -f
```

### Acessos

- **API:** http://localhost:8000
- **Docs (Swagger):** http://localhost:8000/docs
- **Frontend:** http://localhost:3000

## Variaveis de Ambiente

### Backend (obrigatorias)

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
SECRET_KEY=chave-secreta-forte-256-bits
ENVIRONMENT=production
OPENAI_API_KEY=sk-xxx

# Superadmin (criado automaticamente no primeiro boot)
SUPERADMIN_EMAIL=admin@empresa.com
SUPERADMIN_PASSWORD=senha-forte
SUPERADMIN_TENANT_NAME=Admin
SUPERADMIN_TENANT_SLUG=admin
```

### Backend (opcionais)

```bash
# Redis (recomendado para escala > 3 clientes)
REDIS_URL=redis://default:xxx@host:6379

# Pool de banco (ajustar conforme carga)
DB_POOL_SIZE=15
DB_MAX_OVERFLOW=30

# WhatsApp (Z-API)
ZAPI_INSTANCE_ID=xxx
ZAPI_TOKEN=xxx
ZAPI_CLIENT_TOKEN=xxx

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx

# Push Notifications
VAPID_PUBLIC_KEY=xxx
VAPID_PRIVATE_KEY=xxx

# Webhook
WEBHOOK_VERIFY_TOKEN=token-secreto
```

### Frontend

```bash
NEXT_PUBLIC_API_URL=https://seu-backend.up.railway.app/api/v1
NEXT_PUBLIC_VAPID_PUBLIC_KEY=xxx
```

## Deploy (Railway)

### Deploy automatico

Push para `main` dispara deploy automatico via Railway.

### Deploy manual

```bash
cd backend && railway up
cd frontend && railway up
```

### Checklist pre-deploy

- [ ] Testes passando (`pytest -v`)
- [ ] Variaveis de ambiente configuradas
- [ ] Migrations aplicadas (`alembic upgrade head`)
- [ ] Health check respondendo (`GET /api/health`)

### Rollback

```bash
railway rollback
```

## Adicionando Novo Cliente (Tenant)

### Via API (superadmin)

```bash
curl -X POST https://api.vellarys.app/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Imobiliaria XYZ",
    "slug": "imobiliaria-xyz",
    "niche_id": 1
  }'
```

### Via registro (self-service)

```bash
POST /api/v1/auth/register
{
  "name": "Nome do Admin",
  "email": "admin@imobiliaria.com",
  "password": "senha-forte-8chars",
  "company_name": "Imobiliaria XYZ",
  "company_slug": "imobiliaria-xyz"
}
```

### Checklist de onboarding

- [ ] Tenant criado
- [ ] WhatsApp configurado e testado (Z-API ou 360Dialog)
- [ ] Admin do cliente criado
- [ ] Prompt da IA personalizado para o tom da empresa
- [ ] Produtos/imoveis importados
- [ ] Conversa de teste OK (lead -> IA -> handoff)
- [ ] Cliente treinado no dashboard

## Funcionalidades Principais

### IA e Atendimento
- Atendimento automatico via WhatsApp com GPT-4o
- Qualificacao inteligente de leads (hot/warm/cold)
- Busca semantica de imoveis via RAG (pgvector)
- Transcricao automatica de audios (Whisper)
- Resumo automatico de conversas longas
- Guards contra jailbreak e vazamento de dados
- Follow-ups e reengajamento automaticos

### CRM e Vendas
- Inbox em tempo real com SSE (Server-Sent Events)
- Distribuicao automatica de leads (round-robin, por regiao)
- Handoff IA -> vendedor com contexto completo
- Pipeline de vendas com status de leads
- Exportacao de dados (Excel, CSV, PDF)

### Seguranca
- Autenticacao JWT com refresh tokens
- RBAC com 5 roles (superadmin, admin, manager, user, seller)
- Rate limiting por IP, usuario e tenant
- Isolamento multi-tenant completo
- Audit logging de acoes criticas
- Protecao CORS, CSP, HSTS
- Conformidade LGPD (exportacao, anonimizacao)

### Monitoramento
- Health check basico: `GET /api/health`
- Health check detalhado: `GET /api/health/detailed` (autenticado)
- Status do pool de conexoes: `GET /api/health/pool` (autenticado)
- Sentry para rastreamento de erros
- UptimeRobot para monitoramento externo

## Troubleshooting

### Lead nao recebe resposta
1. Verificar se webhook esta chegando (logs do backend)
2. Verificar rate limiting (lead pode estar bloqueado)
3. Verificar status da OpenAI
4. Verificar se tenant esta ativo

### Dashboard lento
1. Verificar pool de conexoes (`GET /api/health/pool`)
2. Verificar se Redis esta ativo
3. Verificar queries lentas no PostgreSQL

### OpenAI timeout
1. Verificar status em status.openai.com
2. Sistema tem retry automatico (2 tentativas, 30s timeout)
3. Fallback com mensagem generica se indisponivel

## Escalabilidade

### Limites atuais

| Recurso | Soft Limit | Hard Limit |
|---------|-----------|-----------|
| Tenants | 10 | 50 |
| Leads/tenant/dia | 500 | 2000 |
| Msgs/min/tenant | 100 | 500 |
| Conexoes DB | 45 | 60 |

### Sinais de que precisa escalar
- Response time > 1s (media)
- Pool de conexoes > 80%
- Timeouts frequentes na OpenAI

### Como escalar
1. Aumentar tier do banco no Railway
2. Ajustar `DB_POOL_SIZE` e `DB_MAX_OVERFLOW`
3. Ativar Redis se nao estiver ativo
4. Adicionar replicas (requer Redis para rate limiting distribuido)

## Backup e Recuperacao

### Railway (automatico)
- Snapshots diarios com retencao de 7 dias
- Restauracao via dashboard Railway

### Manual

```bash
# Exportar
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restaurar
psql $DATABASE_URL < backup.sql
```

## Contatos

| Nivel | Quando | Contato |
|-------|--------|---------|
| Suporte | Bugs simples, duvidas | suporte@vellarys.app |
| Dev | Bugs complexos, features urgentes | dev@vellarys.app |
| Emergencia | Sistema fora, vazamento de dados | Tech Lead (WhatsApp) |
