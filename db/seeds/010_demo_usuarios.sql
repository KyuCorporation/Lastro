-- 010_demo_usuarios.sql — tenants e usuários de demonstração (senha demo123; SOMENTE desenvolvimento)
insert into tenants (id, nome) values
  ('00000000-0000-0000-0000-00000000a1fa', 'Cliente Alfa'),
  ('00000000-0000-0000-0000-00000000be7a', 'Cliente Beta')
on conflict do nothing;

insert into usuarios (id, tenant_id, email, nome, perfil, senha_hash) values
  ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-00000000a1fa', 'ana@alfa.demo',   'Ana (analista)',  'analista', crypt('demo123', gen_salt('bf'))),
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-00000000a1fa', 'caio@alfa.demo',  'Caio (auditor)',  'auditor',  crypt('demo123', gen_salt('bf'))),
  ('00000000-0000-0000-0000-0000000000a3', '00000000-0000-0000-0000-00000000a1fa', 'gil@alfa.demo',   'Gil (gestor)',    'gestor',   crypt('demo123', gen_salt('bf'))),
  ('00000000-0000-0000-0000-0000000000a4', '00000000-0000-0000-0000-00000000a1fa', 'admin@alfa.demo', 'Admin Alfa',      'admin',    crypt('demo123', gen_salt('bf'))),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-00000000be7a', 'bia@beta.demo',   'Bia (analista)',  'analista', crypt('demo123', gen_salt('bf')))
on conflict do nothing;

insert into escopos (usuario_id, uf) values
  ('00000000-0000-0000-0000-0000000000a1', 'PE'),
  ('00000000-0000-0000-0000-0000000000a2', 'PE'),
  ('00000000-0000-0000-0000-0000000000a3', 'PE'),
  ('00000000-0000-0000-0000-0000000000a4', 'PE'),
  ('00000000-0000-0000-0000-0000000000a4', 'AL'),
  ('00000000-0000-0000-0000-0000000000b1', 'AL')
on conflict do nothing;
