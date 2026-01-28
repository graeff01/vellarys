# 🔐 Arquitetura de Permissões e Features - Vellarys

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Hierarquia de Permissões](#hierarquia-de-permissões)
3. [Estrutura de Dados](#estrutura-de-dados)
4. [Lógica de Resolução](#lógica-de-resolução)
5. [Fluxo de Funcionamento](#fluxo-de-funcionamento)
6. [Exemplos Práticos](#exemplos-práticos)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

O sistema Vellarys implementa um **controle de permissões hierárquico e granular** inspirado em plataformas enterprise como Salesforce, HubSpot e Intercom.

### Princípios Fundamentais

1. **Hierarquia Clara**: SuperAdmin → Gestor → Vendedor
2. **Planos como Base**: Features são definidas pelo plano contratado
3. **Overrides Controlados**: SuperAdmin pode fazer exceções
4. **Controle do Gestor**: Gestor decide o que a equipe vê
5. **Segurança por Padrão**: Vendedores só veem o necessário

---

## 🏢 Hierarquia de Permissões

```
┌──────────────────────────────────────────────────────────────┐
│                     🔴 SUPER ADMIN                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ✓ Controla PLANOS de todos os clientes                      │
│  ✓ Define features de cada plano (starter/premium/enterprise)│
│  ✓ Pode fazer OVERRIDES especiais por cliente                │
│  ✓ Bypass completo (vê e faz tudo)                           │
│  ✓ Acessa qualquer tenant com target_tenant_id               │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                   🟡 GESTOR (Manager/Admin)                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ✓ Recebe features do SEU PLANO                               │
│  ✓ Vê features do plano + overrides do SuperAdmin            │
│  ✓ Pode DESATIVAR features para a equipe                     │
│  ✓ NÃO pode ativar além do que o plano permite                │
│  ✓ Controla o que vendedores veem                            │
│  ✓ Salva em tenant.settings['team_features']                 │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    🟢 VENDEDOR (Seller)                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ✓ Usa apenas o que o GESTOR liberou                         │
│  ✓ Vê APENAS team_features (não vê features do plano)        │
│  ✓ Sem controle sobre configurações                          │
│  ✓ Interface limpa e focada em vendas                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 📦 Estrutura de Dados

### 1. Planos (Tabela `plans` ou `PLAN_FEATURES`)

Define o **máximo** de features disponíveis para cada plano:

```python
PLAN_FEATURES = {
    "starter": {
        "calendar_enabled": True,
        "templates_enabled": True,
        "metrics_enabled": False,  # Não disponível
        "copilot_enabled": False,  # Não disponível
        "security_export_lock_enabled": True,  # BLOQUEADO
        # ...
    },
    "premium": {
        "calendar_enabled": True,
        "templates_enabled": True,
        "metrics_enabled": True,  # Liberado
        "copilot_enabled": True,  # Liberado
        "security_export_lock_enabled": False,  # Liberado
        # ...
    },
    "enterprise": {
        # TUDO habilitado
        "ai_guard_enabled": True,
        "knowledge_base_enabled": True,
        # ...
    }
}
```

### 2. SuperAdmin Overrides (Casos Especiais)

Quando SuperAdmin precisa liberar/bloquear algo específico para um cliente:

```json
// tenant.settings
{
  "feature_overrides": {
    "metrics_enabled": true,  // SuperAdmin liberou mesmo sem estar no plano
    "calendar_enabled": false // SuperAdmin bloqueou temporariamente
  }
}
```

### 3. Gestor Team Controls

O que o gestor decidiu liberar para a equipe:

```json
// tenant.settings
{
  "team_features": {
    "calendar_enabled": true,   // Gestor ativou
    "templates_enabled": false, // Gestor desativou
    "notes_enabled": true       // Gestor ativou
  }
}
```

---

## ⚙️ Lógica de Resolução

### Fórmula de Merge

```javascript
Final Features = Plan Features
               + SuperAdmin Overrides (feature_overrides)
               + Gestor Team Controls (team_features)
```

### Por Role

#### 🔴 SuperAdmin
```javascript
// Bypass completo - ALL_FEATURES_ENABLED
return ALL_FEATURES_ENABLED;
```

#### 🟡 Gestor/Admin
```javascript
// Vê tudo que o plano permite + overrides + team
final_features = {
  ...plan_features,           // Do plano contratado
  ...superadmin_overrides,    // Overrides do SuperAdmin
  ...team_features            // O que ele mesmo configurou
}
return final_features;
```

#### 🟢 Vendedor
```javascript
// Vê APENAS o que o gestor liberou
return team_features;  // NÃO vê plan_features nem overrides
```

---

## 🔄 Fluxo de Funcionamento

### 1. SuperAdmin Gerenciando Cliente

```
SuperAdmin acessa: /dashboard/settings?tab=subscription&target_tenant_id=5

1. Frontend: SubscriptionSettings detecta target_tenant_id
2. Frontend: Faz GET /settings/features?target_tenant_id=5
3. Backend: Valida user.role === "superadmin"
4. Backend: Carrega tenant_id=5
5. Backend: Retorna plan_features + overrides + team_features
6. Frontend: SuperAdmin pode editar qualquer feature
7. Frontend: Faz PATCH /settings/features?target_tenant_id=5
8. Backend: Salva em tenant.settings['feature_overrides']
```

### 2. Gestor Configurando Equipe

```
Gestor acessa: /dashboard/settings?tab=subscription

1. Frontend: SEM target_tenant_id (usa seu próprio tenant)
2. Frontend: Faz GET /settings/features
3. Backend: Carrega features do tenant do token
4. Backend: Valida que gestor NÃO pode ativar além do plano
5. Frontend: Gestor vê switches habilitados/desabilitados
6. Frontend: Faz PATCH /settings/features
7. Backend: Salva em tenant.settings['team_features']
8. Backend: Valida: feature_value TRUE requer plan_allows TRUE
```

### 3. Vendedor Usando Sistema

```
Vendedor acessa: /dashboard/inbox

1. Frontend: FeaturesContext carrega features
2. Backend: Detecta user.role === "vendedor"
3. Backend: Retorna APENAS team_features (ignora plano)
4. Frontend: FeatureGate bloqueia páginas não liberadas
5. Vendedor: Vê apenas Inbox, Leads e o que gestor liberou
```

---

## 📝 Exemplos Práticos

### Exemplo 1: Cliente no Starter quer Métricas

**Situação**: Cliente tem plano Starter, mas SuperAdmin quer liberar métricas como cortesia.

**Solução**:
1. SuperAdmin acessa cliente com `target_tenant_id=X`
2. Ativa `metrics_enabled`
3. Backend salva em `feature_overrides.metrics_enabled = true`
4. Cliente agora vê dashboard de métricas mesmo em Starter

**Código**:
```python
# Backend - settings.py
if user.role == "superadmin" and is_managing_other_tenant:
    current_settings["feature_overrides"]["metrics_enabled"] = True
```

### Exemplo 2: Gestor quer esconder Calendário dos Vendedores

**Situação**: Gestor tem Premium (calendário incluído), mas não quer que vendedores usem.

**Solução**:
1. Gestor acessa Assinatura → Features
2. Desativa `calendar_enabled`
3. Backend salva em `team_features.calendar_enabled = false`
4. Vendedores NÃO veem a página de calendário

**Código**:
```python
# Backend - settings.py
if user.role in ["admin", "gestor"] and not is_managing_other_tenant:
    current_settings["team_features"]["calendar_enabled"] = False
```

### Exemplo 3: Vendedor tentando acessar Copilot

**Situação**: Vendedor tenta acessar `/dashboard/copilot` mas gestor não liberou.

**Resultado**:
1. Frontend: FeatureGate verifica `isEnabled('copilot_enabled')`
2. FeaturesContext: Vendedor usa `team_features` (não tem copilot)
3. FeatureGate: Renderiza FeatureBlockedCard com upgrade prompt

**Código**:
```typescript
// frontend/src/app/dashboard/copilot/page.tsx
export default function CopilotPage() {
  return (
    <FeatureGate feature="copilot_enabled">
      <CopilotContent />
    </FeatureGate>
  );
}
```

---

## 🔍 Troubleshooting

### Problema: "Admin não consegue salvar features de cliente"

**Causa**: Endpoint PATCH /settings/features ignorava `target_tenant_id`

**Solução**: ✅ CORRIGIDO
```python
@router.patch("/features")
async def update_features(
    features: dict,
    target_tenant_id: Optional[int] = None,  # AGORA FUNCIONA!
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    if target_tenant_id and user.role == "superadmin":
        tenant = await get_target_tenant(db, target_tenant_id)
```

### Problema: "Gestor consegue ativar features fora do plano"

**Causa**: Faltava validação no backend

**Solução**: ✅ CORRIGIDO
```python
# Validar: Gestor só pode DESATIVAR
if user.role in ["admin", "gestor"]:
    for feature_key, feature_value in features.items():
        plan_allows = plan_features.get(feature_key, False)
        if feature_value and not plan_allows:
            raise HTTPException(403, "Feature não disponível no seu plano")
```

### Problema: "Vendedor vendo features que gestor desativou"

**Causa**: FeaturesContext não diferenciava role

**Solução**: ✅ CORRIGIDO
```typescript
if (user?.role === 'vendedor') {
  // Vendedor vê APENAS team_features
  effectiveFeatures = data.team_features || {};
} else {
  // Gestor vê final_features (plano + overrides + team)
  effectiveFeatures = data.final_features || data;
}
```

---

## 🧪 Testando o Sistema

### Teste 1: SuperAdmin Override
```bash
# Login como SuperAdmin
# Acessar cliente: /dashboard/settings?tab=subscription&target_tenant_id=5
# Ativar "metrics_enabled" (mesmo se plano não tem)
# Verificar que salvou em feature_overrides
# Fazer logout
# Login como cliente ID 5
# Verificar que métricas aparecem
```

### Teste 2: Gestor Bloqueio
```bash
# Login como Gestor (plano Premium)
# Acessar: /dashboard/settings?tab=subscription
# Desativar "calendar_enabled"
# Verificar que salvou em team_features
# Fazer logout
# Login como Vendedor do mesmo tenant
# Verificar que /dashboard/calendar está bloqueado
```

### Teste 3: Upgrade de Plano
```bash
# Login como SuperAdmin
# Acessar cliente no Starter
# Mudar plano para Premium
# Verificar que novas features aparecem
# Gestor pode agora ativar metrics_enabled
```

---

## 📚 Referências de Código

### Backend
- **`backend/src/api/routes/settings.py`**
  - `GET /settings/features` (linha 1275)
  - `PATCH /settings/features` (linha 1329)
  - `PLAN_FEATURES` (linha 332)

### Frontend
- **`frontend/src/contexts/FeaturesContext.tsx`**
  - `fetchFeatures()` (linha 255)
  - `FeaturesProvider` (linha 305)
  - Lógica por role (linha 279)

- **`frontend/src/components/FeatureGate.tsx`**
  - Componente de controle de acesso (linha 182)

- **`frontend/src/components/dashboard/settings/SubscriptionSettings.tsx`**
  - Interface de gerenciamento (linha 65)

---

## 🎓 Princípios Arquiteturais

1. **Zero Trust**: Ninguém tem acesso por padrão (exceto SuperAdmin)
2. **Least Privilege**: Vendedores só veem o necessário
3. **Fail Secure**: Em caso de erro, bloqueia acesso
4. **Audit Trail**: Logs de todas as alterações
5. **Graceful Degradation**: Features desabilitadas não quebram a UI

---

## ✅ Checklist de Implementação

- [x] Backend: Endpoint GET /settings/features com target_tenant_id
- [x] Backend: Endpoint PATCH /settings/features com target_tenant_id
- [x] Backend: Validação de permissões por role
- [x] Backend: Lógica de resolução (plan + overrides + team)
- [x] Frontend: FeaturesContext entende nova estrutura
- [x] Frontend: FeatureGate funciona para todos os roles
- [x] Frontend: SubscriptionSettings gerencia overrides
- [x] Documentação: Arquitetura completa (este arquivo)
- [ ] Testes: Fluxo completo SuperAdmin → Gestor → Vendedor

---

**Última atualização**: 2026-01-28
**Versão**: 1.0
**Autor**: Claude Code + Equipe Vellarys
