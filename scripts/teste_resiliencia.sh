#!/bin/bash
# Resiliência do sistema de pé (SPEC §14.5). Pré-requisito: make demo. Uso: bash scripts/teste_resiliencia.sh
# 1. API reiniciada no meio da sessão: o token emitido antes continua valendo.
# 2. Banco fora do ar: /health fica "degradado", a consulta responde erro no formato do contrato, e a API
#    volta sozinha quando o banco volta (sem reiniciar a API).
# 3. Fonte fora do ar na ingestão: a execução fica "falhou" e nenhum dado já gravado é apagado.
set -uo pipefail
DC="docker compose"
API="${LASTRO_API_URL:-http://localhost:8000}"
falhas=0

ok() { echo "  ok    $1"; }
falha() { echo "  FALHA $1"; falhas=$((falhas + 1)); }
confere() { if [ "$2" = "$3" ]; then ok "$1"; else falha "$1 (esperado '$3', veio '$2')"; fi; }

token() {
  curl -s "$API/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"senha\":\"demo123\"}" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])'
}
consultar() {
  curl -s -o /dev/null -w '%{http_code}' "$API/consultas" -H "Authorization: Bearer $1" \
    -H 'Content-Type: application/json' -d '{"pergunta":"O fornecedor 01.609.785/0001-67 tem sanção?"}'
}
esperar_api() {
  for _ in $(seq 1 60); do curl -s "$API/health" >/dev/null && return 0; sleep 1; done
  return 1
}
contar() { $DC exec -T db psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-lastro}" -tAc "$1"; }

echo "1. API reiniciada no meio da sessão"
TOKEN=$(token admin@alfa.demo)
confere "consulta antes do reinício" "$(consultar "$TOKEN")" 200
$DC restart api >/dev/null 2>&1 && esperar_api
confere "mesmo token depois do reinício" "$(consultar "$TOKEN")" 200

echo "2. Banco fora do ar e de volta"
$DC stop db >/dev/null 2>&1
confere "/health degradado" "$(curl -s "$API/health")" '{"status":"degradado","db":"indisponivel","llm":"mock"}'
corpo=$(curl -s "$API/consultas" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"pergunta":"O fornecedor 01.609.785/0001-67 tem sanção?"}')
codigo=$(echo "$corpo" | python3 -c 'import json,sys; print(json.load(sys.stdin)["erro"]["codigo"])' 2>/dev/null)
confere "consulta sem banco responde 503 do contrato" "$codigo" "FONTE_INDISPONIVEL"
$DC start db >/dev/null 2>&1 && $DC up -d --wait db >/dev/null 2>&1
for _ in $(seq 1 30); do [ "$(consultar "$TOKEN")" = 200 ] && break; sleep 1; done
confere "API volta sozinha com o banco" "$(consultar "$TOKEN")" 200

echo "3. Fonte fora do ar na ingestão"
antes=$(contar "select count(*) from contratos where fonte_id = 'pncp'")
$DC run --rm -e PNCP_BASE_URL=http://127.0.0.1:9/api/consulta -e PNCP_DATA_INICIAL=20261001 \
  -e PNCP_DATA_FINAL=20261001 pipeline python -m lastro_pipeline.cli ingest pncp >/dev/null 2>&1
confere "ingestão termina com erro" "$?" 1
confere "execução registrada como falhou" \
  "$(contar "select status from execucoes_ingestao where fonte_id = 'pncp' order by iniciada_em desc limit 1")" falhou
confere "contratos do PNCP intactos" "$(contar "select count(*) from contratos where fonte_id = 'pncp'")" "$antes"

echo
if [ "$falhas" -eq 0 ]; then echo "Resiliência: tudo ok."; else echo "Resiliência: $falhas falha(s)."; fi
exit "$falhas"
