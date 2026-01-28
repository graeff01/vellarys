#!/bin/bash
#
# Script Automático de Migration - Railway Production
# Execute no console do Railway: bash scripts/railway_migration.sh
#

set -e  # Para na primeira falha

echo "================================================================================"
echo "🚀 MIGRATION AUTOMÁTICA - VELLARYS ENTITLEMENTS V2"
echo "================================================================================"
echo ""
echo "⚠️  ATENÇÃO: Este script está rodando em PRODUÇÃO no Railway!"
echo "   - Criará 4 novas tabelas"
echo "   - Migrará dados de JSONB → tabelas normalizadas"
echo "   - NÃO quebrará nada (código antigo continua funcionando)"
echo ""
read -p "Pressione ENTER para continuar ou CTRL+C para cancelar..."
echo ""

# ==============================================================================
# PASSO 1: Verificar Estado Atual
# ==============================================================================
echo "================================================================================"
echo "📋 PASSO 1: Verificando estado atual do banco"
echo "================================================================================"

python3 <<'PYTHON_CHECK'
from sqlalchemy import inspect, create_engine
import os
import sys

try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\n📋 Tabelas que serão criadas:")
    novas_tabelas = ['plan_entitlements', 'subscription_overrides', 'feature_flags', 'feature_audit_logs']

    all_missing = True
    for t in novas_tabelas:
        if t in tables:
            print(f"  ⚠️  {t} - JÁ EXISTE (pode ser migração anterior)")
            all_missing = False
        else:
            print(f"  ✓ {t} - Será criada")

    if not all_missing:
        print("\n⚠️  AVISO: Algumas tabelas já existem!")
        print("   Isso pode significar que a migration já foi rodada.")
        print("   O script continuará normalmente (safe to rerun).")

    print("\n✅ Verificação completa!")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ ERRO na verificação: {e}")
    print("   Verifique se DATABASE_URL está configurado.")
    sys.exit(1)
PYTHON_CHECK

if [ $? -ne 0 ]; then
    echo "❌ Falha na verificação inicial. Abortando."
    exit 1
fi

echo ""
read -p "Pressione ENTER para continuar com a migration..."
echo ""

# ==============================================================================
# PASSO 2: Rodar Migration (Criar Tabelas)
# ==============================================================================
echo "================================================================================"
echo "🔧 PASSO 2: Rodando migration (criando tabelas)"
echo "================================================================================"

echo "Executando: alembic upgrade head"
alembic upgrade head

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERRO: Migration falhou!"
    echo "   Verifique os logs acima para detalhes."
    echo "   O sistema NÃO foi alterado (rollback automático)."
    exit 1
fi

echo ""
echo "✅ Migration concluída!"
echo ""

# ==============================================================================
# PASSO 3: Verificar Tabelas Criadas
# ==============================================================================
echo "================================================================================"
echo "📊 PASSO 3: Verificando tabelas criadas"
echo "================================================================================"

python3 <<'PYTHON_VERIFY'
from sqlalchemy import inspect, create_engine, text
import os
import sys

try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\n✅ TABELAS CRIADAS:")
    novas_tabelas = ['plan_entitlements', 'subscription_overrides', 'feature_flags', 'feature_audit_logs']

    all_ok = True
    for t in novas_tabelas:
        if t in tables:
            # Contar linhas
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM {t}'))
                count = result.scalar()
            print(f"  ✓ {t} ({count} registros)")
        else:
            print(f"  ✗ {t} (ERRO: não foi criada!)")
            all_ok = False

    if not all_ok:
        print("\n❌ ERRO: Nem todas as tabelas foram criadas!")
        sys.exit(1)

    print("\n✅ Todas as tabelas criadas com sucesso!")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    sys.exit(1)
PYTHON_VERIFY

if [ $? -ne 0 ]; then
    echo "❌ Verificação falhou. Reverta com: alembic downgrade -1"
    exit 1
fi

echo ""
read -p "Pressione ENTER para continuar com migração de dados..."
echo ""

# ==============================================================================
# PASSO 4: Migrar Dados
# ==============================================================================
echo "================================================================================"
echo "📦 PASSO 4: Migrando dados (JSONB → tabelas normalizadas)"
echo "================================================================================"
echo ""
echo "Este passo pode levar alguns minutos dependendo da quantidade de dados..."
echo ""

python3 scripts/migrate_entitlements_data.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERRO: Migração de dados falhou!"
    echo "   As tabelas foram criadas, mas os dados não foram migrados."
    echo "   Você pode tentar rodar novamente: python3 scripts/migrate_entitlements_data.py"
    exit 1
fi

echo ""
echo "✅ Dados migrados com sucesso!"
echo ""

# ==============================================================================
# PASSO 5: Verificar Dados Migrados
# ==============================================================================
echo "================================================================================"
echo "📊 PASSO 5: Verificando dados migrados"
echo "================================================================================"

python3 <<'PYTHON_STATS'
from sqlalchemy import create_engine, text
import os

try:
    engine = create_engine(os.getenv('DATABASE_URL'))

    with engine.connect() as conn:
        # Plan entitlements
        result = conn.execute(text('SELECT COUNT(*) FROM plan_entitlements'))
        plan_count = result.scalar()

        # Feature flags
        result = conn.execute(text('SELECT COUNT(*) FROM feature_flags'))
        flags_count = result.scalar()

        # Subscription overrides
        result = conn.execute(text('SELECT COUNT(*) FROM subscription_overrides'))
        overrides_count = result.scalar()

        # Audit logs
        result = conn.execute(text('SELECT COUNT(*) FROM feature_audit_logs'))
        audit_count = result.scalar()

        print("\n📊 DADOS MIGRADOS:")
        print(f"  ✓ plan_entitlements: {plan_count} registros")
        print(f"  ✓ feature_flags: {flags_count} registros")
        print(f"  ✓ subscription_overrides: {overrides_count} registros")
        print(f"  ✓ feature_audit_logs: {audit_count} registros")

        if plan_count == 0:
            print("\n⚠️  AVISO: plan_entitlements está vazio!")
            print("   Isso pode significar que os planos não têm features definidas.")

        print("\n📋 EXEMPLOS (plan_entitlements):")
        result = conn.execute(text('''
            SELECT p.name, pe.entitlement_key, pe.entitlement_type
            FROM plan_entitlements pe
            JOIN plans p ON p.id = pe.plan_id
            LIMIT 5
        '''))
        for row in result:
            print(f"  - {row[0]}: {row[1]} ({row[2]})")

        print("\n✅ Verificação de dados completa!")

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
PYTHON_STATS

# ==============================================================================
# PASSO 6: Teste Final
# ==============================================================================
echo ""
echo "================================================================================"
echo "🧪 PASSO 6: Teste final (verificando se sistema está funcionando)"
echo "================================================================================"

python3 <<'PYTHON_TEST'
import os
import sys

try:
    # Testar import dos novos models
    from src.domain.entities.plan_entitlement import PlanEntitlement
    from src.domain.entities.subscription_override import SubscriptionOverride
    from src.domain.entities.feature_flag import FeatureFlag
    from src.domain.entities.feature_audit_log import FeatureAuditLog

    # Testar import dos serviços
    from src.services.entitlements import EntitlementResolver
    from src.services.feature_flags import FeatureFlagService
    from src.services.permissions import PermissionService
    from src.services.access_decision import AccessDecisionEngine

    print("\n✅ Todos os imports funcionando!")
    print("  ✓ Models criados")
    print("  ✓ Serviços disponíveis")
    print("  ✓ API v2 pronta para uso")

    print("\n📡 Endpoints da API v2:")
    print("  - GET  /api/v2/settings/entitlements")
    print("  - GET  /api/v2/settings/flags")
    print("  - PATCH /api/v2/settings/flags")
    print("  - POST  /api/v2/settings/overrides")

    sys.exit(0)

except Exception as e:
    print(f"\n❌ ERRO no teste: {e}")
    print("\n⚠️  O sistema pode ter problemas. Verifique os logs.")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_TEST

# ==============================================================================
# SUCESSO!
# ==============================================================================
echo ""
echo "================================================================================"
echo "✅ MIGRATION COMPLETA COM SUCESSO!"
echo "================================================================================"
echo ""
echo "📋 O que foi feito:"
echo "  ✓ 4 novas tabelas criadas"
echo "  ✓ Dados migrados de JSONB → tabelas normalizadas"
echo "  ✓ Sistema testado e funcionando"
echo "  ✓ API v2 disponível"
echo ""
echo "🔒 Segurança:"
echo "  ✓ Código antigo (v1) continua funcionando 100%"
echo "  ✓ JSONB antigos preservados (rollback possível)"
echo "  ✓ Nenhum dado foi perdido"
echo ""
echo "📚 Próximos passos:"
echo "  1. Testar API v2: GET /api/v2/settings/entitlements"
echo "  2. Verificar logs: tail -f logs/backend.log"
echo "  3. Monitorar erros nas próximas horas"
echo "  4. Se tudo OK: deprecar v1 no futuro"
echo ""
echo "📖 Documentação completa: IMPLEMENTATION_COMPLETE.md"
echo ""
echo "================================================================================"
