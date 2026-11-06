#!/bin/bash
# Deixa o ambiente pronto para a demo: banco limpo, seeds, ingestão a partir das fixtures, API e web de pé.
# Etapas ainda não implementadas (gabarito: T20) avisam e não interrompem a preparação.
set -euo pipefail
DC="docker compose"

make reset-db
make ingest-offline
$DC run --rm pipeline python -m lastro_pipeline.cli sinais
$DC up -d --build --wait api
$DC up -d --build web
make eval-ataques || echo "AVISO: a suíte de ataques não atingiu a meta; veja eval/reports/resumo.md."
make eval || echo "AVISO: gabarito ainda não disponível (T20)."

echo "Pronto para a demo: http://localhost:5173 (API em http://localhost:8000/health)."
