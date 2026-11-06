include .env
export
DC = docker compose
PSQL_SU = $(DC) exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -v ON_ERROR_STOP=1

.PHONY: up down reset-db seed ingest-pe ingest-pncp ingest-sancoes ingest-qsa sinais test test-db test-pipeline test-api eval eval-ataques lint tag-good

up:            ; $(DC) up -d --build
down:          ; $(DC) down
reset-db:      ; $(DC) down -v && $(DC) up -d db && sleep 5 && $(MAKE) seed
seed:          ; for f in db/seeds/*.sql; do $(PSQL_SU) -f /seeds/$$(basename $$f); done
ingest-pe:     ; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest pe_portal
ingest-pncp:   ; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest pncp
ingest-sancoes:; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest sancoes
ingest-qsa:    ; $(DC) run --rm pipeline python -m lastro_pipeline.cli ingest qsa
sinais:        ; $(DC) run --rm pipeline python -m lastro_pipeline.cli sinais
test:          test-db test-pipeline test-api
test-db:       seed ; $(DC) run --rm api pytest -q app/tests/test_acesso.py
test-pipeline: ; $(DC) run --rm pipeline pytest -q
test-api:      seed ; $(DC) run --rm api pytest -q
eval:          ; $(DC) run --rm -v $(PWD)/eval:/eval api python /eval/run_eval.py gabarito
eval-ataques:  ; $(DC) run --rm -v $(PWD)/eval:/eval api python /eval/run_eval.py ataques
lint:          ; cd backend && ruff check . && cd ../pipeline && ruff check . && cd ../frontend && npm run lint
tag-good:      ; git tag good-$$(date +%H%M) && echo "tag criada"
