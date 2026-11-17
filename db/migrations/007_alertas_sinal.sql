-- 007_alertas_sinal.sql — alerta por evento (SPEC §3.3 I7, T28) sem travar a limpeza de sinais.
-- Aprovada em 17/11/2026 (AGENTS.md §4, plano 4.8). Só altera `alertas`; grants e policies continuam os de 002_rls.sql.
--
-- Problema: `alertas.sinal_id` referenciava `sinais(id)` sem `on delete`. Um alerta apontando para um sinal impedia a
-- pipeline de apagar esse sinal quando ele deixava de valer, e o sinal vencido ficava na fila e no dossiê.
-- Correção: o alerta guarda uma cópia do que o sinal dizia (tipo, gravidade, UF, explicação) e o vínculo vira nulo
-- quando o sinal é apagado. A ação da chave estrangeira roda como dono da tabela e ignora a RLS, então o
-- `lastro_ingest` continua sem acesso a `alertas`.
alter table alertas
  drop constraint alertas_sinal_id_fkey,
  add constraint alertas_sinal_id_fkey foreign key (sinal_id) references sinais(id) on delete set null,
  add column sinal_tipo text,
  add column sinal_gravidade text,
  add column sinal_uf char(2),
  add column sinal_explicacao text;

update alertas a
   set sinal_tipo = s.tipo, sinal_gravidade = s.gravidade, sinal_uf = s.uf, sinal_explicacao = s.explicacao
  from sinais s
 where s.id = a.sinal_id;

-- Um alerta por sinal e carteira, mesmo com duas filas abertas ao mesmo tempo.
create unique index alertas_carteira_sinal_uq on alertas (carteira_id, sinal_id) where sinal_id is not null;
