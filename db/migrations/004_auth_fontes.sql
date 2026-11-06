-- 004_auth_fontes.sql — login sem contexto (SECURITY DEFINER) e fontes de referência

-- O login acontece antes de existir contexto de acesso. Esta função devolve só o necessário para autenticar.
create or replace function auth_buscar_usuario(p_email text)
returns table (id uuid, tenant_id uuid, nome text, perfil text, senha_hash text, ufs text[])
language sql stable security definer set search_path = public, pg_temp as $$
  select u.id, u.tenant_id, u.nome, u.perfil, u.senha_hash,
         coalesce(array_agg(e.uf::text order by e.uf) filter (where e.uf is not null), array[]::text[])
    from usuarios u
    left join escopos e on e.usuario_id = u.id
   where lower(u.email) = lower(p_email) and u.ativo
   group by u.id;
$$;
revoke all on function auth_buscar_usuario(text) from public;
grant execute on function auth_buscar_usuario(text) to lastro_app;

insert into fontes (id, nome, tipo, url_base, licenca, observacoes) values
  ('pe_portal', 'Portal da Transparência de Pernambuco', 'arquivo', null, 'Dados abertos (LAI)', 'Preencher URL e formato em docs/catalogo-fontes.md'),
  ('pncp', 'Portal Nacional de Contratações Públicas', 'api', 'https://pncp.gov.br/api/consulta', 'Dados abertos (Lei 14.133/2021)', 'Spec OpenAPI em /api/consulta/v3/api-docs'),
  ('ceis', 'Cadastro de Empresas Inidôneas e Suspensas', 'arquivo', 'https://portaldatransparencia.gov.br', 'Dados abertos (CGU)', 'Firewall pode bloquear cliente HTTP; fallback manual'),
  ('cnep', 'Cadastro Nacional de Empresas Punidas', 'arquivo', 'https://portaldatransparencia.gov.br', 'Dados abertos (CGU)', 'Idem CEIS'),
  ('receita_qsa', 'Quadro de sócios (dados abertos de CNPJ)', 'api', null, 'Dados abertos (Receita Federal)', 'N3; só carteiras e sancionadas'),
  ('demo_sintetico', 'Dados sintéticos de demonstração', 'sintetico', null, 'Sintético', 'Nunca misturar com dado real nas métricas')
on conflict (id) do nothing;
