# 🇧🇷 Configuração do Google Cloud TTS (Vozes Brasileiras)

## Por que usar Google Cloud TTS?

- ✅ **Vozes em português brasileiro nativo**
- ✅ **Mesmo custo da OpenAI** (~R$ 0,03 por áudio)
- ✅ **Qualidade Neural** superior em PT-BR

---

## 📋 Passo a Passo

### 1. Criar conta no Google Cloud

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie uma conta (tem $300 de crédito grátis)
3. Crie um novo projeto

### 2. Ativar API do Text-to-Speech

1. No menu, vá em **APIs e Serviços** → **Biblioteca**
2. Busque por **"Cloud Text-to-Speech API"**
3. Clique em **Ativar**

### 3. Criar credenciais (Service Account)

1. Vá em **APIs e Serviços** → **Credenciais**
2. Clique em **Criar credenciais** → **Conta de serviço**
3. Preencha:
   - Nome: `velaris-tts`
   - Função: **Editor**
4. Clique em **Concluir**
5. Na lista de contas de serviço, clique na que você criou
6. Vá em **Chaves** → **Adicionar chave** → **Criar nova chave**
7. Escolha **JSON** e clique em **Criar**
8. Um arquivo JSON será baixado

### 4. Configurar no Railway

1. No Railway, vá no seu serviço de **backend**
2. Em **Variables**, adicione:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/app/google-credentials.json
   ```
3. Cole o conteúdo do arquivo JSON como uma nova variável:
   ```
   GOOGLE_CREDENTIALS_JSON=<conteúdo do arquivo JSON aqui>
   ```

### 5. Atualizar Dockerfile (se necessário)

Se estiver usando Docker, adicione ao `Dockerfile`:

```dockerfile
# Copiar credenciais do Google
RUN echo $GOOGLE_CREDENTIALS_JSON > /app/google-credentials.json
```

---

## 🧪 Testar

Após configurar, as vozes brasileiras aparecerão automaticamente no painel:

- 🇧🇷 **Camila** (feminina, recomendada)
- 🇧🇷 **Vitória** (feminina, jovem)
- 🇧🇷 **Ricardo** (masculina, profissional)

---

## 💡 Observações

- **Custo**: ~$0.016/1000 chars (igual OpenAI)
- **Sem configuração**: O sistema continua funcionando com OpenAI
- **Com configuração**: Vozes brasileiras ficam disponíveis
- **Escolha automática**: O sistema detecta qual provedor usar baseado na voz selecionada
