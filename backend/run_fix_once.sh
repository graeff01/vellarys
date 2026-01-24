#!/bin/bash
# Script para rodar o fix uma vez só automaticamente
# Cria um arquivo .fix_applied para não executar novamente

FIX_MARKER="/app/.fix_applied"

if [ -f "$FIX_MARKER" ]; then
    echo "ℹ️ Fix já foi aplicado anteriormente. Pulando..."
    exit 0
fi

echo "🔧 Aplicando fix de colunas faltantes..."

# Executa o script Python
python3 apply_fix.py

# Se sucesso, marca como aplicado
if [ $? -eq 0 ]; then
    touch "$FIX_MARKER"
    echo "✅ Fix aplicado e marcado como concluído"
else
    echo "❌ Fix falhou. Será tentado novamente no próximo deploy."
    exit 1
fi
