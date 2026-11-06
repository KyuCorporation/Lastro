include .env
export
DC = docker compose
PSQL_SU = $(DC) exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -v ON_ERROR_STOP=1

.PHONY: up down reset-db seed ingest-pe ingest-pncp ingest-sancoes ingest-qsa ingest-offline demo sinais test test-db test-pipeline test-api test-eval test-web test-integracao test-e2e eval eval-ataques lint tag-good

up:            ; $(DC) up -d --build
down:          ; $(DC) down
reset-db:      ; $(DC) down -v && $(DC) up -d --wait db && $(MAKE) seed
seed:          ; for f in db/seeds/*.sql; do $(PSQL_SU) -f /seeds/$$(basename $$f); done
ingest-pe:     ; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest pe_portal
ingest-pncp:   ; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest pncp
ingest-sancoes:; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest sancoes
ingest-qsa:    ; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest qsa
ingest-offline:; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest todas --offline
demo:          ; bash scripts/demo_reset.sh
sinais:        ; $(DC) run --rm pipeline python -m lastro_pipeline.cli sinais
test:          test-db test-pipeline test-api test-eval test-web
test-db:       seed ; $(DC) run --rm api pytest -q app/tests/test_acesso.py
test-pipeline: ; $(DC) run --rm pipeline pytest -q
test-api:      seed ; $(DC) run --rm api pytest -q
test-eval:     ; $(DC) run --rm --no-deps api pytest -q -p no:cacheprovider /eval/tests
test-web:      ; $(DC) run --rm --no-deps web npm test
# Integração e E2E: precisam do sistema de pé e com dados (make demo). Não entram no make test.
test-integracao: ; $(DC) run --rm -e LASTRO_API_URL=http://api:8000 api pytest -q -m integracao app/tests/integracao
test-e2e:      ; cd frontend && npm run e2e
eval:          seed ; $(DC) run --rm api python /eval/run_eval.py gabarito
eval-ataques:  seed ; $(DC) run --rm api python /eval/run_eval.py ataques
lint:          ; cd backend && ruff check . && cd ../pipeline && ruff check . && cd ../eval && ruff check . && cd ../frontend && npm run lint
tag-good:      ; git tag good-$$(date +%H%M) && echo "tag criada"
