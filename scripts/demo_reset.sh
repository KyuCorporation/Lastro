#!/bin/bash
# Deixa o ambiente pronto para a demo: banco limpo, seeds, ingestão a partir das fixtures, sinais, avaliação,
# API e web de pé.
#
# A avaliação (ataques e gabarito) grava consultas, recibos e auditoria, e esse histórico é imutável. Por isso ela
# roda primeiro, sobre um banco completo, e o banco é recriado em seguida: os relatórios ficam em eval/reports/
# (lidos por GET /metricas) e a demo começa com o histórico vazio.
#
# Por padrão a avaliação roda sem LLM. EVAL_COM_GEMINI=1 roda antes também com o Gemini (gasta cota: cerca de
# 158 perguntas, cada uma com planejador e redator), e a tela de métricas mostra os dois resultados lado a lado.
set -euo pipefail
DC="docker compose"

preparar_banco() {
  make reset-db
  make ingest-offline
  $DC run --rm pipeline python -m lastro_pipeline.cli sinais
}

$DC build api web pipeline
preparar_banco
if [ "${EVAL_COM_GEMINI:-0}" = "1" ]; then
  make eval-ataques EVAL_LLM=gemini || echo "AVISO: ataques com o Gemini abaixo da meta; veja eval/reports/."
  make eval EVAL_LLM=gemini || echo "AVISO: gabarito com o Gemini abaixo da meta; veja eval/reports/."
fi
make eval-ataques EVAL_LLM=mock || echo "AVISO: a suíte de ataques não atingiu a meta; veja eval/reports/resumo.md."
make eval EVAL_LLM=mock || echo "AVISO: o gabarito não atingiu a meta; veja eval/reports/resumo.md."

preparar_banco
$DC up -d --wait api
$DC up -d web

echo "Pronto para a demo: http://localhost:5173 (API em http://localhost:8000/health)."
