# Dockerfile para Frontend Next.js

# Estágio 1: Build
FROM node:20-alpine AS builder

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de gerenciamento de pacotes
COPY package*.json ./

# Instala as dependências
RUN npm install

# Copia o restante do código da aplicação
COPY . .

# Constrói a aplicação para produção
RUN npm run build

# Estágio 2: Produção
FROM node:20-alpine

WORKDIR /app

# Define o ambiente como produção
ENV NODE_ENV=production

# Copia os artefatos de build do estágio anterior
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expõe a porta em que a aplicação vai rodar
EXPOSE 3000

# Comando para iniciar a aplicação
CMD ["npm", "start"]
