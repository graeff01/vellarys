#!/bin/bash

# ============================================================================
# SCRIPT DE TESTE - CRM INBOX
# ============================================================================
# Testa todo o fluxo do CRM Inbox automaticamente
#
# Uso:
#   chmod +x test_crm_inbox.sh
#   ./test_crm_inbox.sh
# ============================================================================

set -e  # Para em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
API_URL="${API_URL:-http://localhost:8000}"
TENANT_SLUG="${TENANT_SLUG:-demo}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@demo.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
SELLER_EMAIL="${SELLER_EMAIL:-pedro@demo.com}"
SELLER_PASSWORD="${SELLER_PASSWORD:-senha123}"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}🧪 TESTE COMPLETO - CRM INBOX${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# ============================================================================
# 1. LOGIN ADMIN
# ============================================================================
echo -e "${YELLOW}[1/10]${NC} Fazendo login como admin..."

ADMIN_LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${ADMIN_EMAIL}\",
    \"password\": \"${ADMIN_PASSWORD}\"
  }")

ADMIN_TOKEN=$(echo $ADMIN_LOGIN_RESPONSE | jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo -e "${RED}❌ Erro no login admin${NC}"
  echo "Response: $ADMIN_LOGIN_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ Admin logado com sucesso${NC}"
echo ""

# ============================================================================
# 2. VERIFICAR MODO ATUAL
# ============================================================================
echo -e "${YELLOW}[2/10]${NC} Verificando modo de handoff atual..."

CURRENT_MODE=$(curl -s "${API_URL}/api/v1/tenants/${TENANT_SLUG}/handoff-mode" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")

echo "Modo atual: $(echo $CURRENT_MODE | jq -r '.handoff_mode')"
echo ""

# ============================================================================
# 3. ATIVAR MODO CRM INBOX
# ============================================================================
echo -e "${YELLOW}[3/10]${NC} Ativando modo CRM Inbox..."

ACTIVATE_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/tenants/${TENANT_SLUG}/handoff-mode" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"handoff_mode": "crm_inbox"}')

if [ "$(echo $ACTIVATE_RESPONSE | jq -r '.success')" != "true" ]; then
  echo -e "${RED}❌ Erro ao ativar modo CRM Inbox${NC}"
  echo "Response: $ACTIVATE_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ Modo CRM Inbox ativado${NC}"
echo "$(echo $ACTIVATE_RESPONSE | jq -r '.message')"
echo ""

# ============================================================================
# 4. CRIAR USUÁRIO CORRETOR (se não existir)
# ============================================================================
echo -e "${YELLOW}[4/10]${NC} Criando usuário corretor..."

# Busca tenant_id
TENANT_INFO=$(curl -s "${API_URL}/api/v1/tenants/${TENANT_SLUG}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")
TENANT_ID=$(echo $TENANT_INFO | jq -r '.id')

REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Pedro Corretor\",
    \"email\": \"${SELLER_EMAIL}\",
    \"password\": \"${SELLER_PASSWORD}\",
    \"role\": \"corretor\",
    \"tenant_id\": ${TENANT_ID}
  }")

# Pode falhar se usuário já existe - OK
if echo "$REGISTER_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Usuário corretor criado${NC}"
else
  echo -e "${YELLOW}⚠️ Usuário pode já existir (ignorando erro)${NC}"
fi
echo ""

# ============================================================================
# 5. LOGIN CORRETOR
# ============================================================================
echo -e "${YELLOW}[5/10]${NC} Fazendo login como corretor..."

SELLER_LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${SELLER_EMAIL}\",
    \"password\": \"${SELLER_PASSWORD}\"
  }")

SELLER_TOKEN=$(echo $SELLER_LOGIN_RESPONSE | jq -r '.access_token')
SELLER_USER_ID=$(echo $SELLER_LOGIN_RESPONSE | jq -r '.user.id')

if [ "$SELLER_TOKEN" == "null" ] || [ -z "$SELLER_TOKEN" ]; then
  echo -e "${RED}❌ Erro no login corretor${NC}"
  echo "Response: $SELLER_LOGIN_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ Corretor logado (user_id: ${SELLER_USER_ID})${NC}"
echo ""

# ============================================================================
# 6. VINCULAR CORRETOR AO SELLER
# ============================================================================
echo -e "${YELLOW}[6/10]${NC} Vinculando corretor ao seller..."

# Assume seller_id = 1 (ajustar se necessário)
SELLER_ID=1

LINK_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/seller/inbox/admin/link-seller-user" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{
    \"seller_id\": ${SELLER_ID},
    \"user_id\": ${SELLER_USER_ID}
  }")

if [ "$(echo $LINK_RESPONSE | jq -r '.success')" != "true" ]; then
  echo -e "${YELLOW}⚠️ Erro ao vincular (pode já estar vinculado)${NC}"
  echo "Response: $LINK_RESPONSE"
else
  echo -e "${GREEN}✅ Corretor vinculado ao seller ${SELLER_ID}${NC}"
fi
echo ""

# ============================================================================
# 7. VERIFICAR DISPONIBILIDADE DO INBOX
# ============================================================================
echo -e "${YELLOW}[7/10]${NC} Verificando disponibilidade do inbox..."

CHECK_RESPONSE=$(curl -s "${API_URL}/api/v1/seller/info/check-inbox-available" \
  -H "Authorization: Bearer ${SELLER_TOKEN}")

if [ "$(echo $CHECK_RESPONSE | jq -r '.available')" != "true" ]; then
  echo -e "${RED}❌ Inbox não disponível para o corretor${NC}"
  echo "Motivo: $(echo $CHECK_RESPONSE | jq -r '.reason')"
  exit 1
fi

echo -e "${GREEN}✅ Inbox disponível para o corretor${NC}"
echo "Motivo: $(echo $CHECK_RESPONSE | jq -r '.reason')"
echo ""

# ============================================================================
# 8. BUSCAR INFORMAÇÕES DO CORRETOR
# ============================================================================
echo -e "${YELLOW}[8/10]${NC} Buscando informações do corretor..."

SELLER_INFO=$(curl -s "${API_URL}/api/v1/seller/info/me" \
  -H "Authorization: Bearer ${SELLER_TOKEN}")

echo "Nome: $(echo $SELLER_INFO | jq -r '.seller_name')"
echo "Total de leads: $(echo $SELLER_INFO | jq -r '.total_leads')"
echo "Taxa de conversão: $(echo $SELLER_INFO | jq -r '.conversion_rate')%"
echo "Inbox disponível: $(echo $SELLER_INFO | jq -r '.can_use_inbox')"
echo ""

# ============================================================================
# 9. LISTAR LEADS NO INBOX
# ============================================================================
echo -e "${YELLOW}[9/10]${NC} Listando leads no inbox..."

LEADS_RESPONSE=$(curl -s "${API_URL}/api/v1/seller/inbox/leads" \
  -H "Authorization: Bearer ${SELLER_TOKEN}")

LEAD_COUNT=$(echo $LEADS_RESPONSE | jq '. | length')

echo "Leads encontrados: ${LEAD_COUNT}"

if [ "$LEAD_COUNT" -gt "0" ]; then
  echo ""
  echo "Primeiros leads:"
  echo $LEADS_RESPONSE | jq '.[:3] | .[] | {id, name, phone, status, qualification, attended_by}'
fi
echo ""

# ============================================================================
# 10. TESTAR FLUXO DE ASSUMIR CONVERSA (se houver leads)
# ============================================================================
if [ "$LEAD_COUNT" -gt "0" ]; then
  echo -e "${YELLOW}[10/10]${NC} Testando assumir conversa..."

  FIRST_LEAD_ID=$(echo $LEADS_RESPONSE | jq -r '.[0].id')

  echo "Assumindo lead ${FIRST_LEAD_ID}..."

  TAKEOVER_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/seller/inbox/leads/${FIRST_LEAD_ID}/take-over" \
    -H "Authorization: Bearer ${SELLER_TOKEN}")

  if [ "$(echo $TAKEOVER_RESPONSE | jq -r '.success')" == "true" ]; then
    echo -e "${GREEN}✅ Conversa assumida com sucesso${NC}"
    echo "Lead agora está sendo atendido por: $(echo $TAKEOVER_RESPONSE | jq -r '.attended_by')"

    # Testar envio de mensagem
    echo ""
    echo "Enviando mensagem de teste..."

    MESSAGE_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/seller/inbox/leads/${FIRST_LEAD_ID}/send-message" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${SELLER_TOKEN}" \
      -d '{"content": "Olá! Aqui é o Pedro, corretor. Teste automatizado."}')

    if [ "$(echo $MESSAGE_RESPONSE | jq -r '.success')" == "true" ]; then
      echo -e "${GREEN}✅ Mensagem enviada com sucesso${NC}"
    else
      echo -e "${RED}❌ Erro ao enviar mensagem${NC}"
      echo $MESSAGE_RESPONSE | jq .
    fi
  else
    echo -e "${RED}❌ Erro ao assumir conversa${NC}"
    echo $TAKEOVER_RESPONSE | jq .
  fi
else
  echo -e "${YELLOW}[10/10]${NC} Nenhum lead disponível para testar take-over"
fi

echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}🎉 TESTE COMPLETO FINALIZADO${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo "Modo CRM Inbox: ✅ ATIVO"
echo "Corretor vinculado: ✅ OK"
echo "Inbox disponível: ✅ OK"
echo ""
echo -e "${YELLOW}Próximos passos:${NC}"
echo "1. Enviar lead de teste via WhatsApp"
echo "2. IA qualifica automaticamente"
echo "3. Corretor vê lead no inbox"
echo "4. Corretor assume e responde via CRM"
echo "5. IA para de responder automaticamente"
echo ""
echo -e "${BLUE}============================================================================${NC}"
