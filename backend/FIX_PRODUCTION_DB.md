# 🔧 FIX: Colunas Faltantes no Banco de Produção

## Problema

O backend está falhando com erro:
```
asyncpg.exceptions.UndefinedColumnError: column leads.attended_by does not exist
```

## Causa

As migrations criadas não foram aplicadas corretamente no banco de produção do Railway.

## Solução: Executar SQL Diretamente

### Opção 1: Via Railway CLI (Recomendado)

```bash
# 1. Instalar Railway CLI (se ainda não tiver)
npm install -g @railway/cli

# 2. Fazer login
railway login

# 3. Conectar ao projeto
railway link

# 4. Conectar ao banco de dados
railway connect postgres

# 5. Copiar e colar o conteúdo do arquivo fix_missing_columns.sql
```

### Opção 2: Via Interface do Railway

1. Acesse https://railway.app
2. Vá no serviço **PostgreSQL**
3. Clique em **Data** → **Query**
4. Cole o conteúdo de `fix_missing_columns.sql`
5. Execute

### Opção 3: Forçar Re-deploy com Migrations

```bash
# 1. Fazer um commit vazio para forçar rebuild
git commit --allow-empty -m "chore: force redeploy to run migrations"
git push origin main

# 2. Monitorar logs do Railway
# Verificar se as migrations rodaram com sucesso
```

## Script SQL

O script `fix_missing_columns.sql` adiciona:

1. ✅ `leads.attended_by` - Quem está atendendo (ai, seller, manager)
2. ✅ `leads.seller_took_over_at` - Quando corretor assumiu
3. ✅ `messages.sender_type` - Tipo do remetente (ai, seller, system)
4. ✅ `messages.sender_user_id` - ID do usuário que enviou
5. ✅ `sellers.user_id` - Vínculo entre seller e user
6. ✅ Enum `corretor` no tipo UserRole

## Verificação

Após executar o SQL, verifique se as colunas foram criadas:

```sql
-- Verificar colunas na tabela leads
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'leads'
  AND column_name IN ('attended_by', 'seller_took_over_at');

-- Verificar colunas na tabela messages
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'messages'
  AND column_name IN ('sender_type', 'sender_user_id');

-- Verificar coluna na tabela sellers
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'sellers'
  AND column_name = 'user_id';
```

## Após Fix

1. O backend deve iniciar sem erros
2. As rotas do CRM Inbox devem funcionar
3. Corretores podem fazer login e ver seus leads

## Próximos Passos

Depois que o fix for aplicado:

1. ✅ Ativar modo CRM Inbox via configurações
2. ✅ Criar usuário corretor
3. ✅ Vincular corretor ao seller
4. ✅ Testar fluxo completo

Documentação completa em: `QUICK_START_CRM_INBOX.md`
