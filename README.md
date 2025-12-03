# Velaris - IA Atendente B2B

Sistema de IA para atendimento inicial de leads, multi-tenant.

## Estrutura

```
velaris/
├── backend/          # API FastAPI + PostgreSQL
├── frontend/         # Dashboard Next.js (em breve)
└── docker-compose.yml
```

## Como rodar

### 1. Configurar variáveis de ambiente

```bash
cd backend
cp .env.example .env
# Edite o .env e coloque sua OPENAI_API_KEY
```

### 2. Subir com Docker

```bash
# Na pasta raiz (velaris/)
docker compose up -d

# Ver logs
docker compose logs -f

# Parar
docker compose down
```

### 3. Acessar

- API: http://localhost:8000
- Documentação: http://localhost:8000/docs

## Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: Next.js (em desenvolvimento)
- **IA**: OpenAI GPT-4o-mini
