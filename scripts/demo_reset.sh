#!/bin/bash
# Deixa o ambiente pronto para a demo: banco limpo, seeds, ingestão a partir das fixtures, sinais, avaliação,
# API e web de pé.
#
# A avaliação (ataques e gabarito) grava consultas, recibos e auditoria, e esse histórico é imutável. Por isso ela
# roda primeiro, sobre um banco completo, e o banco é recriado em seguida: os relatórios ficam em eval/reports/
# (lidos por GET /metricas) e a demo começa com o histórico vazio.
set -euo pipefail
DC="docker compose"

preparar_banco() {
  make reset-db
  make ingest-offline
  $DC run --rm pipeline python -m lastro_pipeline.cli sinais
}

$DC build api web pipeline
preparar_banco
make eval-ataques || echo "AVISO: a suíte de ataques não atingiu a meta; veja eval/reports/resumo.md."
make eval || echo "AVISO: o gabarito não atingiu a meta; veja eval/reports/resumo.md."

preparar_banco
$DC up -d --wait api
$DC up -d web

echo "Pronto para a demo: http://localhost:5173 (API em http://localhost:8000/health)."
