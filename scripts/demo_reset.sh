#!/bin/bash
# Deixa o ambiente pronto para a demo: banco limpo, seeds, ingestão a partir das fixtures, sinais e eval.
set -euo pipefail
make reset-db
DC="docker compose"
$DC run --rm pipeline python -m lastro_pipeline.cli ingest todas --offline
$DC run --rm pipeline python -m lastro_pipeline.cli sinais
make eval eval-ataques || echo "eval falhou: conferir antes da demo"
echo "Pronto para a demo."
