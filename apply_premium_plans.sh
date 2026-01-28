#!/bin/bash
#
# Script para aplicar nova estrutura de planos B2B Premium via API
# ================================================================
#
# Este script usa a API do admin para:
# 1. Criar/atualizar os 2 planos premium (Professional e Enterprise)
# 2. Listar planos existentes
#
# Uso:
#   chmod +x apply_premium_plans.sh
#   ./apply_premium_plans.sh
#

set -e

# Configuração
API_URL="${API_URL:-http://localhost:8000/api}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@vellarys.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD}"

echo "🚀 Aplicando planos B2B Premium no Vellarys"
echo "============================================"
echo ""

# Verificar se senha foi fornecida
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ Erro: ADMIN_PASSWORD não definida"
    echo ""
    echo "Uso:"
    echo "  ADMIN_PASSWORD=sua_senha ./apply_premium_plans.sh"
    echo ""
    exit 1
fi

# 1. Login como admin
echo "📝 Fazendo login como admin..."
TOKEN=$(curl -s -X POST "$API_URL/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Erro ao fazer login. Verifique as credenciais."
    exit 1
fi

echo "✅ Login realizado com sucesso"
echo ""

# 2. Seed dos planos padrão (cria ou atualiza)
echo "📝 Aplicando planos padrão..."
RESULT=$(curl -s -X POST "$API_URL/v1/admin/plans/seed-defaults" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo "$RESULT" | jq '.'
echo ""

# 3. Listar planos criados
echo "📊 Planos disponíveis:"
echo "===================="
curl -s -X GET "$API_URL/v1/admin/plans" \
    -H "Authorization: Bearer $TOKEN" \
    | jq '.plans[] | {slug, name, price_monthly, price_yearly, limits}'

echo ""
echo "✅ Planos B2B Premium aplicados com sucesso!"
echo ""
echo "📊 Resumo:"
echo "  • Professional: R$ 897/mês (2.000 leads, 15 corretores)"
echo "  • Enterprise: R$ 1.997/mês (ilimitado)"
echo ""
