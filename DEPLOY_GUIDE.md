# 🚀 GUIA DE DEPLOY - NOVAS FUNCIONALIDADES

**Data:** 15/01/2026  
**Versão:** Velaris 3.0

---

## 📦 FUNCIONALIDADES IMPLEMENTADAS

### ✅ 1. **TRANSCRIÇÃO DE ÁUDIO** (Whisper API)
- Lead pode mandar áudio no WhatsApp
- Sistema transcreve automaticamente
- IA responde normalmente

### ✅ 2. **HISTÓRICO ILIMITADO** (Com Resumos Automáticos)
- Armazena 100% das mensagens
- A cada 50 mensagens, gera resumo via IA
- Performance otimizada (usa resumo + últimas 30)

### ✅ 3. **BUSCA SEMÂNTICA** (RAG com pgvector)
- Query: "apartamento perto de escolas boas"
- Sistema busca por similaridade (não só palavras-chave)
- Embeddings via OpenAI text-embedding-3-small

---

## 🛠️ PASSOS PARA ATIVAR

### PASSO 1: Rodar Migrations

```bash
cd backend
alembic upgrade head
```

**O que faz:**
- Adiciona campo `conversation_summary` na tabela `leads`
- Instala extensão `pgvector` no PostgreSQL
- Cria tabela `property_embeddings`

### PASSO 2: Testar Transcrição de Áudio

**Status:** ✅ JÁ ATIVO (não precisa configurar nada)

**Como testar:**
1. Mande um áudio no WhatsApp conectado
2. Verifique nos logs:
   ```
   🎙️ Áudio recebido de 9999
   🎙️ Transcrevendo áudio...
   ✅ Áudio transcrito: "olá, quero um apartamento..."
   ```
3. IA deve responder normalmente

### PASSO 3: Verificar Histórico Ilimitado

**Status:** ✅ JÁ ATIVO (não precisa configurar nada)

**Comportamento:**
- Primeiras 50 mensagens: Histórico normal
- A partir da 50ª: Gera resumo automático
- Próximas mensagens: Usa resumo + últimas 30

**Como monitorar:**
- Verifique campo `conversation_summary` no banco:
  ```sql
  SELECT id, name, conversation_summary 
  FROM leads 
  WHERE conversation_summary IS NOT NULL;
  ```

### PASSO 4: Ativar Busca Semântica

**⚠️ REQUER AÇÃO MANUAL**

#### 4.1. Gerar Embeddings (Primeira Vez)

Chame o endpoint (via Postman/Insomnia):

```http
POST /api/admin/embeddings/bulk-generate
Authorization: Bearer {seu_token_admin}
Content-Type: application/json

{
  "tenant_id": 1,
  "force_regenerate": false
}
```

**Tempo estimado:** ~2s por produto (10 produtos = 20s)

#### 4.2. Verificar Status

```http
GET /api/admin/embeddings/status/1
Authorization: Bearer {seu_token_admin}
```

Resposta esperada:
```json
{
  "total_products": 15,
  "total_embeddings": 15,
  "coverage_percentage": 100,
  "status": "complete"
}
```

---

## 💰 CUSTOS

### OpenAI Embeddings
- Modelo: `text-embedding-3-small`
- Custo: **$0.02 por 1M tokens**
- Exemplo real:
  - 100 imóveis com descrições de 200 palavras cada
  - ~40k tokens total
  - Custo: **$0.0008** (menos de 1 centavo!)

### OpenAI Whisper (Transcrição)
- Custo: **$0.006 por minuto**
- Exemplo: 100 áudios de 10s cada
  - ~16 minutos total
  - Custo: **$0.096** (10 centavos!)

### Resumos Automáticos
- Modelo: GPT-4o-mini
- Custo: **~$0.01 por 100 resumos**
- Roda automaticamente a cada 50 mensagens

---

## ✅ CHECKLIST DE VALIDAÇÃO

- [ ] Migrations rodaram sem erro
- [ ] Transcrição de áudio funcionando
- [ ] Resumos automáticos sendo gerados (após 50 msgs)
- [ ] Embeddings criados para todos os produtos
- [ ] Busca semântica retornando resultados relevantes
- [ ] Logs sem erros críticos

---

**Dúvidas?** Consulte os logs ou abra issue no GitHub! 🚀
