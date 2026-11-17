# db/ — contrato do modelo de dados

- `migrations/` roda no init do container (ordem alfabética): papéis, schema, RLS, views, login e fontes.
  **Nunca edite uma migration aplicada.** Mudança aprovada vira arquivo novo (a próxima é `008_...sql`).
- `006_auditoria_seq_no_trigger.sql` (aprovada em 06/11): o `seq` da auditoria passa a ser sorteado dentro do
  trigger, depois do lock, para a ordem do `seq` ser a ordem da cadeia com escrita simultânea. Banco criado antes
  dela: `make reset-db`, ou aplicar à mão com
  `docker compose exec -T db psql -U postgres -d lastro -f /docker-entrypoint-initdb.d/006_auditoria_seq_no_trigger.sql`.
- `007_alertas_sinal.sql` (aprovada em 17/11): o alerta guarda a cópia do sinal (tipo, gravidade, UF, explicação) e
  o vínculo com o sinal vira nulo quando a pipeline apaga um sinal vencido; um alerta por sinal e carteira. Banco
  criado antes dela: `make reset-db`, ou
  `docker compose exec -T db psql -U postgres -d lastro -f /docker-entrypoint-initdb.d/007_alertas_sinal.sql`.
- `seeds/` roda com `make seed`: usuários de demo e fornecedor sintético com injeção (cena do ataque).

Testado em 06/11 às 03h num Postgres 16: migrations e seeds aplicam limpas; RLS conferida para os casos 1, 3, 4, 7 e 8 do SPEC §6.4, auditoria encadeada, bloqueio de gestor criando carteira e isolamento de carteiras entre tenants.
Detalhes do contexto de acesso: SPEC §6 e ADR-001.
