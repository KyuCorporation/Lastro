-- 002_rls.sql — papéis, contexto de acesso e Row-Level Security (contrato congelado)
-- Os papéis lastro_app e lastro_ingest são criados em 000_roles.sh com senhas do .env.

-- ===================== Contexto de acesso =====================
-- A API faz, por transação: select set_config('app.tenant_id', $1, true), idem app.usuario_id, app.perfil, app.ufs ('PE,AL').
create or replace function ctx_tenant() returns uuid language sql stable as
$$ select nullif(current_setting('app.tenant_id', true), '')::uuid $$;

create or replace function ctx_usuario() returns uuid language sql stable as
$$ select nullif(current_setting('app.usuario_id', true), '')::uuid $$;

create or replace function ctx_perfil() returns text language sql stable as
$$ select nullif(current_setting('app.perfil', true), '') $$;

create or replace function ctx_ufs() returns text[] language sql stable as
$$ select coalesce(string_to_array(nullif(current_setting('app.ufs', true), ''), ','), array[]::text[]) $$;

-- ===================== Privilégios =====================
revoke all on all tables in schema public from public;
grant usage on schema public to lastro_app, lastro_ingest;

-- API
grant select on tenants, usuarios, escopos to lastro_app;
grant select on fontes, execucoes_ingestao, arquivos_brutos to lastro_app;
grant select on orgaos, fornecedores, contratos, pagamentos, sancoes, socios, sinais to lastro_app;
grant select, insert, update, delete on carteiras, carteira_itens to lastro_app;
grant select, insert, update on consultas, alertas to lastro_app;
grant select, insert on recibos, auditoria to lastro_app;           -- sem update/delete: imutáveis
grant usage on sequence auditoria_seq_seq to lastro_app;

-- Pipeline
grant select, insert, update on fontes, execucoes_ingestao, arquivos_brutos to lastro_ingest;
grant select, insert, update on orgaos, fornecedores, contratos, pagamentos, sancoes, socios to lastro_ingest;
grant select, insert, update, delete on sinais to lastro_ingest;
grant select on carteira_itens to lastro_ingest;                    -- N3: quadro societário só da carteira
grant usage on sequence auditoria_seq_seq to lastro_ingest;
grant insert on auditoria to lastro_ingest;

-- ===================== RLS: fatos públicos =====================
alter table contratos enable row level security;
alter table contratos force row level security;
create policy contratos_app on contratos for select to lastro_app
  using (ctx_tenant() is not null and uf::text = any (ctx_ufs()));
create policy contratos_ingest on contratos for all to lastro_ingest using (true) with check (true);

alter table pagamentos enable row level security;
alter table pagamentos force row level security;
create policy pagamentos_app on pagamentos for select to lastro_app
  using (ctx_tenant() is not null and uf::text = any (ctx_ufs()));
create policy pagamentos_ingest on pagamentos for all to lastro_ingest using (true) with check (true);

-- Sinais são por UF; sinais nacionais (uf nula) visíveis a qualquer usuário autenticado
alter table sinais enable row level security;
alter table sinais force row level security;
create policy sinais_app on sinais for select to lastro_app
  using (ctx_tenant() is not null and (uf is null or uf::text = any (ctx_ufs())));
create policy sinais_ingest on sinais for all to lastro_ingest using (true) with check (true);

-- Identidade pública do fornecedor, órgãos e sanções: qualquer usuário autenticado
alter table fornecedores enable row level security;
alter table fornecedores force row level security;
create policy fornecedores_app on fornecedores for select to lastro_app using (ctx_tenant() is not null);
create policy fornecedores_ingest on fornecedores for all to lastro_ingest using (true) with check (true);

alter table orgaos enable row level security;
alter table orgaos force row level security;
create policy orgaos_app on orgaos for select to lastro_app using (ctx_tenant() is not null);
create policy orgaos_ingest on orgaos for all to lastro_ingest using (true) with check (true);

alter table sancoes enable row level security;
alter table sancoes force row level security;
create policy sancoes_app on sancoes for select to lastro_app using (ctx_tenant() is not null);
create policy sancoes_ingest on sancoes for all to lastro_ingest using (true) with check (true);

-- Sócios (mascarados): gestor não vê
alter table socios enable row level security;
alter table socios force row level security;
create policy socios_app on socios for select to lastro_app
  using (ctx_tenant() is not null and ctx_perfil() in ('analista', 'auditor', 'admin'));
create policy socios_ingest on socios for all to lastro_ingest using (true) with check (true);

-- ===================== RLS: identidade =====================
alter table tenants enable row level security;
alter table tenants force row level security;
create policy tenants_app on tenants for select to lastro_app using (id = ctx_tenant());

alter table usuarios enable row level security;
alter table usuarios force row level security;
create policy usuarios_app on usuarios for select to lastro_app using (tenant_id = ctx_tenant());

alter table escopos enable row level security;
alter table escopos force row level security;
create policy escopos_app on escopos for select to lastro_app
  using (usuario_id = ctx_usuario()
         or (ctx_perfil() = 'admin'
             and usuario_id in (select id from usuarios where tenant_id = ctx_tenant())));

-- ===================== RLS: dados do tenant =====================
alter table carteiras enable row level security;
alter table carteiras force row level security;
create policy carteiras_app on carteiras for all to lastro_app
  using (tenant_id = ctx_tenant())
  with check (tenant_id = ctx_tenant() and ctx_perfil() in ('analista', 'admin'));

alter table carteira_itens enable row level security;
alter table carteira_itens force row level security;
create policy carteira_itens_app on carteira_itens for all to lastro_app
  using (tenant_id = ctx_tenant())
  with check (tenant_id = ctx_tenant() and ctx_perfil() in ('analista', 'admin'));
create policy carteira_itens_ingest on carteira_itens for select to lastro_ingest using (true);

-- Consultas e recibos: o próprio usuário; auditor e admin veem o tenant inteiro
alter table consultas enable row level security;
alter table consultas force row level security;
create policy consultas_app_select on consultas for select to lastro_app
  using (tenant_id = ctx_tenant()
         and (usuario_id = ctx_usuario() or ctx_perfil() in ('auditor', 'admin')));
create policy consultas_app_insert on consultas for insert to lastro_app
  with check (tenant_id = ctx_tenant() and usuario_id = ctx_usuario());
create policy consultas_app_update on consultas for update to lastro_app
  using (tenant_id = ctx_tenant() and usuario_id = ctx_usuario())
  with check (tenant_id = ctx_tenant() and usuario_id = ctx_usuario());

alter table recibos enable row level security;
alter table recibos force row level security;
create policy recibos_app_select on recibos for select to lastro_app
  using (tenant_id = ctx_tenant()
         and (usuario_id = ctx_usuario() or ctx_perfil() in ('auditor', 'admin')));
create policy recibos_app_insert on recibos for insert to lastro_app
  with check (tenant_id = ctx_tenant() and usuario_id = ctx_usuario());

alter table alertas enable row level security;
alter table alertas force row level security;
create policy alertas_app on alertas for all to lastro_app
  using (tenant_id = ctx_tenant()) with check (tenant_id = ctx_tenant());

-- Auditoria: todos inserem no próprio tenant (inclusive negações); só auditor e admin leem
alter table auditoria enable row level security;
alter table auditoria force row level security;
create policy auditoria_app_insert on auditoria for insert to lastro_app
  with check (tenant_id is not distinct from ctx_tenant());
create policy auditoria_app_select on auditoria for select to lastro_app
  using (tenant_id = ctx_tenant() and ctx_perfil() in ('auditor', 'admin'));
-- O trigger de encadeamento (001) é SECURITY DEFINER do superusuário e lê o último hash sem depender destas políticas.
create policy auditoria_ingest on auditoria for insert to lastro_ingest with check (tenant_id is null);
create policy auditoria_ingest_select on auditoria for select to lastro_ingest using (tenant_id is null);
