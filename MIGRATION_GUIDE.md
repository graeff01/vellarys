# 🚀 Guia de Migração - Planos B2B Premium

## Status Atual

✅ **Código atualizado e commitado**
- Backend: `seed_default_plans()` atualizado
- Migration: `001_migrate_to_2_premium_plans.py` criada
- Scripts: `apply_premium_plans.sh` e `apply_premium_plans.py` prontos

⏳ **Pendente: Aplicar no banco de dados**

---

## Opções de Migração

### Opção 1: Via API (Mais Simples) ⭐

**Pré-requisitos:**
- Backend rodando (local ou produção)
- Credenciais de admin

**Passos:**

1. **Iniciar o backend** (se local):
```bash
cd backend
# Configurar .env primeiro (copiar de .env.example)
uvicorn src.main:app --reload
```

2. **Executar script de migração**:
```bash
chmod +x apply_premium_plans.sh

# Para ambiente local
ADMIN_PASSWORD=sua_senha ./apply_premium_plans.sh

# Para produção
API_URL=https://sua-api.com/api ADMIN_PASSWORD=sua_senha ./apply_premium_plans.sh
```

**O que o script faz:**
- ✅ Faz login como admin
- ✅ Chama endpoint `/admin/plans/seed-defaults`
- ✅ Cria/atualiza planos Professional e Enterprise
- ✅ Lista planos criados

---

### Opção 2: Via Alembic Migration

**Pré-requisitos:**
- Acesso direto ao banco de dados
- Python com dependências instaladas

**Passos:**

1. **Configurar ambiente**:
```bash
cd backend
cp .env.example .env
# Editar .env com DATABASE_URL correto
```

2. **Instalar dependências**:
```bash
pip install -r requirements.txt
```

3. **Executar migration**:
```bash
alembic upgrade head
```

**O que a migration faz:**
- ✅ Atualiza plano Professional (R$ 897, 2.000 leads)
- ✅ Atualiza plano Enterprise (R$ 1.997, ilimitado)
- ✅ Migra clientes de "Essencial" para "Professional"
- ✅ Remove plano "Essencial"

---

### Opção 3: Via Script Python Direto

**Pré-requisitos:**
- Python com SQLAlchemy instalado
- DATABASE_URL configurado

**Passos:**

1. **Configurar DATABASE_URL**:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
```

2. **Executar script**:
```bash
cd backend
python3 apply_premium_plans.py
```

---

## Verificação Pós-Migração

### 1. Verificar planos criados

**Via API:**
```bash
curl -X GET "http://localhost:8000/api/v1/admin/plans" \
  -H "Authorization: Bearer $TOKEN" | jq '.plans[] | {slug, name, price_monthly}'
```

**Resultado esperado:**
```json
{
  "slug": "professional",
  "name": "Professional",
  "price_monthly": 897.00
}
{
  "slug": "enterprise",
  "name": "Enterprise",
  "price_monthly": 1997.00
}
```

### 2. Verificar features por plano

**Professional deve ter:**
- ✅ `appointment_mode: "assisted"`
- ✅ `reengagement_limit: 1`
- ❌ `api_access_enabled: false`
- ❌ `white_label: false`

**Enterprise deve ter:**
- ✅ `appointment_mode: "automatic"`
- ✅ `reengagement_limit: -1` (ilimitado)
- ✅ `api_access_enabled: true`
- ✅ `white_label: true`

### 3. Verificar clientes migrados

```sql
SELECT 
    t.name as tenant_name,
    p.slug as plan_slug,
    p.price_monthly
FROM tenant_subscriptions ts
JOIN tenants t ON ts.tenant_id = t.id
JOIN plans p ON ts.plan_id = p.id
ORDER BY p.price_monthly;
```

---

## Troubleshooting

### Erro: "Backend não está rodando"

**Solução:**
```bash
cd backend
# Verificar se .env existe
ls -la .env

# Se não existir, copiar de .env.example
cp .env.example .env

# Editar .env com suas configurações
nano .env

# Iniciar backend
uvicorn src.main:app --reload
```

### Erro: "No module named 'sqlalchemy'"

**Solução:**
```bash
cd backend
pip install -r requirements.txt
```

### Erro: "Plano já existe"

**Solução:**
O endpoint `seed-defaults` é idempotente. Se o plano já existe, ele apenas pula.
Isso é esperado e não é um erro.

### Erro: "Migration já foi aplicada"

**Solução:**
```bash
# Verificar status das migrations
alembic current

# Se já foi aplicada, não precisa fazer nada
# Se quiser reverter:
alembic downgrade -1
```

---

## Próximos Passos Após Migração

1. ✅ **Verificar planos no admin**
   - Acessar `/admin/plans`
   - Confirmar Professional (R$ 897) e Enterprise (R$ 1.997)

2. ✅ **Testar criação de novo cliente**
   - Criar tenant de teste
   - Verificar se pode escolher Professional ou Enterprise
   - Confirmar features habilitadas

3. ✅ **Atualizar frontend**
   - Atualizar `FeaturesContext.tsx`
   - Criar página `/pricing`
   - Remover referências a "Essencial"

4. ✅ **Notificar clientes existentes**
   - Enviar email sobre upgrade (Essencial → Professional)
   - Comunicar novos valores e features

---

## Comandos Rápidos

```bash
# Verificar status do backend
curl http://localhost:8000/api/v1/health

# Aplicar migração via API (mais simples)
ADMIN_PASSWORD=senha ./apply_premium_plans.sh

# Aplicar via Alembic
cd backend && alembic upgrade head

# Verificar planos
curl -X GET "http://localhost:8000/api/v1/admin/plans" -H "Authorization: Bearer $TOKEN"

# Reverter migração (se necessário)
cd backend && alembic downgrade -1
```

---

## 📞 Suporte

Se encontrar problemas:
1. Verificar logs do backend
2. Verificar se DATABASE_URL está correto
3. Confirmar que admin tem permissões
4. Revisar walkthrough.md para detalhes técnicos
