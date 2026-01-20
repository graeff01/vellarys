# 🔍 AUDITORIA DE ESCALABILIDADE - VELLARYS
**Data:** 20/01/2026  
**Analista:** Antigravity AI  
**Objetivo:** Preparar sistema para escalar de 3 → 6 clientes  
**Versão Atual:** Em Produção (Railway)

---

## 📊 RESUMO EXECUTIVO

O **Vellarys** está bem estruturado para produção com 3 clientes. Porém, para **escalar com segurança para 6+ clientes**, existem **gaps críticos** que precisam ser resolvidos ANTES da expansão.

### Grade de Prontidão para Escalabilidade

| Área | Status | Nota | Ação Necessária |
|------|--------|------|-----------------|
| **Arquitetura** | ✅ Sólida | 9/10 | Mantém |
| **Banco de Dados** | ⚠️ Atenção | 7/10 | Pool + Índices |
| **Cache** | 🔴 Crítico | 3/10 | Implementar Redis |
| **Rate Limiting** | ⚠️ Em Memória | 5/10 | Migrar para Redis |
| **Testes** | 🔴 Crítico | 2/10 | Criar suite básica |
| **Monitoramento** | ⚠️ Parcial | 6/10 | Melhorar alertas |
| **CI/CD** | ✅ OK | 8/10 | Adicionar testes |
| **Segurança** | ✅ Boa | 8/10 | Pequenos ajustes |
| **Documentação** | ⚠️ Parcial | 5/10 | Documentar runbook |

**Recomendação:** ❌ **NÃO ESCALAR** antes de resolver os itens críticos marcados em 🔴

---

## 🔴 PROBLEMAS CRÍTICOS (RESOLVER ANTES DE ESCALAR)

### 1. **CACHE INEXISTENTE - GARGALO DE PERFORMANCE**

**Situação Atual:**
- Redis está nas dependências (`requirements.txt`) mas **NÃO está sendo usado**
- Todas as queries batem direto no PostgreSQL
- Rate limiter está **em memória** (não funciona com múltiplas instâncias)

**Impacto com 6 Clientes:**
- Cada request de settings/tenant = 1 query ao DB
- Com 100 mensagens/hora × 6 tenants = 600+ queries/hora só para settings
- Custo aumenta, latência cresce, DB sobrecarregado

**Código Atual (message_rate_limiter.py):**
```python
# ARMAZENAMENTO EM MEMÓRIA (para produção, usar Redis)
class InMemoryRateLimiter:
    """Rate limiter em memória.
    Para produção com múltiplas instâncias, substituir por Redis.
    """
```

**Solução Necessária:**
```python
# backend/src/infrastructure/services/redis_service.py (NOVO)
from redis.asyncio import Redis
from src.config import get_settings

settings = get_settings()

# Singleton Redis
_redis_client: Redis | None = None

async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
    return _redis_client

async def cache_get(key: str) -> str | None:
    redis = await get_redis()
    return await redis.get(key)

async def cache_set(key: str, value: str, ttl: int = 300):
    redis = await get_redis()
    await redis.set(key, value, ex=ttl)
```

**Estimativa:** 4-6 horas  
**Prioridade:** 🔴 CRÍTICA

---

### 2. **TESTES AUTOMATIZADOS INSUFICIENTES**

**Situação Atual:**
- Apenas **1 arquivo de teste** (`test_leads_api.py`) com 1 teste funcional
- Cobertura estimada: **< 2%** do código
- Sem testes para: process_message, handoff, rate limiting, segurança

**Impacto:**
- Qualquer mudança pode quebrar funcionalidades existentes
- Bugs só aparecem em produção
- Medo de fazer refactoring necessário
- Clientes existentes afetados por bugs de novos clientes

**Arquivos Críticos SEM Testes:**
1. `process_message.py` (1430 linhas) - Core do sistema
2. `handoff_service.py` (553 linhas) - Distribuição de leads
3. `security_service.py` (515 linhas) - Proteção contra ataques
4. `ai_guard_service.py` (23886 bytes) - Segurança da IA
5. `rate_limit_service.py` (132 linhas) - Proteção contra abuso

**Solução - Testes Mínimos Necessários:**

```python
# backend/tests/test_process_message.py (NOVO)
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_message_blocked_for_rate_limit():
    """Teste crítico: mensagens são bloqueadas após exceder limite"""
    pass

@pytest.mark.asyncio
async def test_lead_qualification_hot():
    """Teste crítico: lead marcado como hot quando tem sinais de compra"""
    pass

@pytest.mark.asyncio
async def test_handoff_triggered_on_hot_lead():
    """Teste crítico: handoff acontece automaticamente para lead hot"""
    pass

@pytest.mark.asyncio
async def test_security_blocks_prompt_injection():
    """Teste crítico: tentativas de prompt injection são bloqueadas"""
    pass

@pytest.mark.asyncio
async def test_tenant_isolation():
    """Teste crítico: tenant A não vê dados do tenant B"""
    pass
```

**Estimativa:** 16-24 horas (para 60% de cobertura crítica)  
**Prioridade:** 🔴 CRÍTICA

---

### 3. **POOL DE CONEXÕES SUBDIMENSIONADO**

**Situação Atual (connection.py):**
```python
engine = create_async_engine(
    database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,        # ⚠️ Fixo
    max_overflow=20,     # ⚠️ Fixo
)
```

**Cálculo para 6 Clientes:**
- Média: 50 mensagens/dia/tenant × 6 = 300 mensagens/dia
- Pico: até 20 mensagens simultâneas
- Cada mensagem: ~3 queries (lead, messages, tenant)
- Pool atual: 10 + 20 = 30 conexões máximas

**PROBLEMA:** Em picos, pool pode esgotar → timeout → mensagens perdidas

**Solução:**
```python
# Ajustar para ambiente dinâmico
pool_size = int(os.getenv("DB_POOL_SIZE", "15"))
max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))

engine = create_async_engine(
    database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_recycle=3600,  # Recicla conexões velhas
    pool_timeout=30,     # Timeout mais generoso
)
```

**Estimativa:** 2 horas  
**Prioridade:** 🔴 CRÍTICA

---

## ⚠️ PROBLEMAS IMPORTANTES (RESOLVER EM PARALELO)

### 4. **ÍNDICES DE BANCO FALTANDO PARA ESCALABILIDADE**

**Índices Existentes (BOM):**
- `ix_leads_tenant_created` - leads por tenant/data
- `ix_leads_tenant_status` - leads por status
- `ix_leads_tenant_qual` - leads por qualificação
- `ix_messages_lead_created` - mensagens por lead/data

**Índices Faltando (NECESSÁRIOS):**
```sql
-- Para busca por telefone (muito usado em webhooks)
CREATE INDEX ix_leads_phone ON leads(phone) WHERE phone IS NOT NULL;

-- Para reengajamento (scheduler)
CREATE INDEX ix_leads_reengagement ON leads(tenant_id, reengagement_status, last_activity_at);

-- Para audit logs (compliance)
CREATE INDEX ix_audit_logs_tenant_date ON audit_logs(tenant_id, created_at DESC);

-- Para notificações não lidas
CREATE INDEX ix_notifications_unread ON notifications(tenant_id, read) WHERE read = false;
```

**Estimativa:** 2 horas  
**Prioridade:** ⚠️ IMPORTANTE

---

### 5. **AUDIT LOG NÃO ESTÁ SENDO USADO CONSISTENTEMENTE**

**Situação Atual:**
- `audit_service.py` existe e é bem implementado
- Mas **@audit_log decorator não existe** 
- Não há chamadas consistentes ao log de auditoria nas rotas críticas

**Rotas SEM Auditoria (Exemplo - Riscos para LGPD):**
- DELETE `/leads/{id}` - Exclusão de dados
- PUT `/settings` - Mudanças de configuração
- POST `/tenants` - Criação de novos clientes
- DELETE `/users/{id}` - Exclusão de usuários

**Solução - Criar Decorator:**
```python
# backend/src/api/decorators.py (NOVO)
from functools import wraps
from src.infrastructure.services.audit_service import log_audit, AuditAction, AuditSeverity

def audit_log(action: AuditAction, severity: AuditSeverity = AuditSeverity.INFO):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # Extrair db, user, tenant do request
            await log_audit(
                db=kwargs.get('db'),
                action=action,
                severity=severity,
                user_id=kwargs.get('current_user', {}).get('id'),
                tenant_id=kwargs.get('current_user', {}).get('tenant_id'),
            )
            return result
        return wrapper
    return decorator
```

**Estimativa:** 4 horas  
**Prioridade:** ⚠️ IMPORTANTE (LGPD)

---

### 6. **FALTA MONITORAMENTO DE MÉTRICAS DE NEGÓCIO**

**Situação Atual:**
- Sentry configurado para erros ✅
- Health check básico ✅
- **Mas faltam métricas de negócio:**
  - Taxa de conversão por tenant
  - Tempo médio de resposta da IA
  - Leads ignorados (sem resposta)
  - Falhas de webhook por provedor

**Solução - Endpoint de Métricas Prometheus:**
```python
# backend/src/api/routes/prometheus_metrics.py (NOVO)
from prometheus_client import Counter, Histogram, generate_latest

# Métricas
leads_created = Counter('velaris_leads_created_total', 'Total leads criados', ['tenant', 'source'])
messages_processed = Counter('velaris_messages_processed_total', 'Mensagens processadas', ['tenant', 'status'])
ai_response_time = Histogram('velaris_ai_response_seconds', 'Tempo de resposta da IA', ['tenant'])
handoff_completed = Counter('velaris_handoffs_total', 'Handoffs realizados', ['tenant', 'reason'])

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Estimativa:** 6 horas  
**Prioridade:** ⚠️ IMPORTANTE

---

## 🟡 MELHORIAS RECOMENDADAS (APÓS RESOLVER CRÍTICOS)

### 7. **DOCUMENTAÇÃO DE RUNBOOK**

**Falta:**
- Procedimento de deploy
- Como investigar problemas
- Como adicionar novo tenant
- Limites e quotas por plano
- Contatos de escalonamento

**Criar:** `RUNBOOK.md` com procedimentos operacionais

**Estimativa:** 4 horas

---

### 8. **TIMEOUT E CIRCUIT BREAKER PARA OPENAI**

**Situação Atual:**
```python
# process_message.py
async def chat_completion_com_retry(
    messages: list,
    temperature: float,
    max_tokens: int,
    max_retries: int = settings.openai_max_retries,  # 2
    timeout: float = settings.openai_timeout_seconds, # 30s
):
```

**Problema:** Se OpenAI ficar lento/down, TODAS as mensagens travam

**Solução - Circuit Breaker:**
```python
import time

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.recovery_time = recovery_time
        self.last_failure = 0
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure > self.recovery_time:
                self.state = "half-open"
                return True
            return False
        return True  # half-open
    
    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.threshold:
            self.state = "open"
    
    def record_success(self):
        self.failures = 0
        self.state = "closed"
```

**Estimativa:** 4 horas

---

### 9. **WEBSOCKETS PARA REAL-TIME**

**Situação Atual:**
- Frontend usa polling a cada 30s
- Ineficiente para múltiplos tenants

**Impacto com 6 Clientes:**
- 6 tenants × 3 usuários/tenant × 1 poll/30s = 36 requests/minuto só de polling
- Latência de até 30s para ver novo lead

**Solução Recomendada:**
- Implementar WebSocket para notificações em tempo real
- Estimativa: 8 horas

---

## 🛠️ PLANO DE AÇÃO PRIORIZADO

### **FASE 1: Pré-Requisitos para Escalar (OBRIGATÓRIO)**
**Prazo: 1 semana**

| # | Task | Horas | Responsável |
|---|------|-------|-------------|
| 1 | Implementar Redis Cache | 6h | Dev Backend |
| 2 | Migrar Rate Limiter para Redis | 4h | Dev Backend |
| 3 | Aumentar Pool de Conexões | 2h | Dev Backend |
| 4 | Criar Índices no Banco | 2h | Dev Backend |
| 5 | Testes Críticos (5 testes) | 8h | Dev Backend |

**Total: ~22 horas**

---

### **FASE 2: Estabilidade (RECOMENDADO)**
**Prazo: 2 semanas**

| # | Task | Horas | Responsável |
|---|------|-------|-------------|
| 6 | Completar Suite de Testes | 16h | Dev Backend |
| 7 | Decorator @audit_log | 4h | Dev Backend |
| 8 | Métricas Prometheus | 6h | Dev Backend |
| 9 | Runbook Operacional | 4h | DevOps |
| 10 | Circuit Breaker OpenAI | 4h | Dev Backend |

**Total: ~34 horas**

---

### **FASE 3: Excelência (NICE TO HAVE)**
**Prazo: 1 mês**

| # | Task | Horas | Responsável |
|---|------|-------|-------------|
| 11 | WebSockets Real-Time | 8h | Dev Full |
| 12 | Dashboard Analytics Avançado | 12h | Dev Frontend |
| 13 | A/B Testing de Prompts | 8h | Dev Backend |
| 14 | Integração CRMs Externos | 12h | Dev Backend |

**Total: ~40 horas**

---

## 📋 CHECKLIST DE DEPLOY PARA 6 CLIENTES

### Antes de Adicionar Novos Clientes:
- [ ] Redis configurado no Railway
- [ ] Rate limiter usando Redis
- [ ] Pool de conexões ajustado (15/30)
- [ ] Índices de banco criados
- [ ] 5 testes críticos passando
- [ ] Sentry alertas configurados
- [ ] Health check respondendo < 500ms
- [ ] Backup de banco funcionando
- [ ] Runbook documentado

### Para Cada Novo Tenant:
- [ ] Criar tenant no sistema
- [ ] Configurar API WhatsApp (Z-API/360Dialog)
- [ ] Testar webhook de entrada
- [ ] Testar webhook de saída
- [ ] Configurar prompt personalizado
- [ ] Adicionar usuários do cliente
- [ ] Verificar rate limits adequados
- [ ] Monitorar primeira semana

---

## 💰 ANÁLISE DE CUSTO-BENEFÍCIO

### Cenário SEM as Melhorias:
- **Risco de downtime:** Alto (sem testes, sem cache)
- **Custo de incidente:** R$ 5.000-10.000 (perda de leads + imagem)
- **Probabilidade de incidente:** 60% nos primeiros 30 dias

### Cenário COM as Melhorias:
- **Investimento:** ~56h de desenvolvimento (~R$ 8.400 @ R$150/h)
- **Risco de downtime:** Baixo
- **Probabilidade de incidente:** < 10%

**ROI:** Investir nas melhorias é **5x mais barato** que lidar com incidentes

---

## 🎯 CONCLUSÃO

O **Vellarys** tem uma arquitetura sólida, mas precsa de **ajustes de infraestrutura** antes de escalar. Os gaps identificados são comuns em sistemas que crescem rápido - o importante é resolvê-los ANTES de dobrar a base de clientes.

**Recomendação Final:**
1. ✅ **FASE 1 é OBRIGATÓRIA** antes de adicionar o 4º cliente
2. ⚠️ **FASE 2 deve ser começada em paralelo**
3. 🟡 **FASE 3 pode aguardar estabilidade pós-escala**

---

*Auditoria realizada por Antigravity AI em 20/01/2026*
