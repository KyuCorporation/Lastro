#!/bin/bash
# Deixa o ambiente pronto para a demo: banco limpo, seeds, ingestão a partir das fixtures, API e web de pé.
# Etapas ainda não implementadas (sinais: T17; eval: T20/T21) avisam e não interrompem a preparação.
set -euo pipefail
DC="docker compose"

make reset-db
make ingest-offline
$DC run --rm pipeline python -m lastro_pipeline.cli sinais || echo "AVISO: sinais ainda não calculados (T17)."
$DC up -d --build --wait api
$DC up -d --build web
make eval eval-ataques || echo "AVISO: eval ainda não disponível (T20/T21)."

echo "Pronto para a demo: http://localhost:5173 (API em http://localhost:8000/health)."
