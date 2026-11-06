-- 001_schema.sql — modelo de dados do Lastro (contrato congelado; ver AGENTS.md §4)
create extension if not exists pgcrypto;

-- ===================== Identidade e escopo =====================
create table tenants (
  id uuid primary key default gen_random_uuid(),
  nome text not null unique,
  criado_em timestamptz not null default now()
);

create table usuarios (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  email text not null unique,
  nome text not null,
  perfil text not null check (perfil in ('analista', 'gestor', 'auditor', 'admin')),
  senha_hash text not null,
  ativo boolean not null default true
);

create table escopos (
  usuario_id uuid not null references usuarios(id) on delete cascade,
  uf char(2) not null,
  primary key (usuario_id, uf)
);

-- ===================== Proveniência =====================
create table fontes (
  id text primary key,            -- 'pe_portal', 'pncp', 'ceis', 'cnep', 'receita_qsa', 'demo_sintetico'
  nome text not null,
  tipo text not null,             -- 'api', 'arquivo', 'sintetico'
  url_base text,
  licenca text,
  observacoes text
);

create table execucoes_ingestao (
  id uuid primary key default gen_random_uuid(),
  fonte_id text not null references fontes(id),
  iniciada_em timestamptz not null default now(),
  finalizada_em timestamptz,
  status text not null default 'rodando' check (status in ('rodando', 'ok', 'falhou', 'parcial')),
  parametros jsonb,
  registros_lidos int default 0,
  registros_novos int default 0,
  registros_atualizados int default 0,
  registros_descartados int default 0,  -- ex.: favorecido pessoa física
  erro text
);

create table arquivos_brutos (
  id uuid primary key default gen_random_uuid(),
  execucao_id uuid references execucoes_ingestao(id),
  fonte_id text not null references fontes(id),
  caminho text not null,
  url_origem text,
  sha256 char(64) not null,
  bytes bigint,
  coletado_em timestamptz not null default now(),
  unique (fonte_id, sha256)
);

-- ===================== Fatos públicos =====================
create table orgaos (
  id text primary key,            -- '<fonte>:<codigo ou cnpj do órgão>'
  nome text not null,
  uf char(2),
  esfera text                     -- 'estadual', 'municipal', 'federal'
);

create table fornecedores (
  cnpj char(14) primary key check (cnpj ~ '^[0-9]{14}$'),
  razao_social text,
  uf_sede char(2),
  atualizado_em timestamptz not null default now()
);

create table contratos (
  id uuid primary key default gen_random_uuid(),
  fonte_id text not null references fontes(id),
  id_origem text not null,
  uf char(2) not null,
  orgao_id text references orgaos(id),
  fornecedor_cnpj char(14) not null references fornecedores(cnpj),
  objeto text,
  valor_global numeric(18,2),
  data_assinatura date,
  vigencia_inicio date,
  vigencia_fim date,
  url_origem text,
  arquivo_bruto_id uuid references arquivos_brutos(id),
  coletado_em timestamptz not null,
  hash_conteudo char(64) not null,
  objeto_tsv tsvector generated always as (to_tsvector('portuguese', coalesce(objeto, ''))) stored,
  unique (fonte_id, id_origem)
);
create index contratos_fornecedor_idx on contratos (fornecedor_cnpj, uf);
create index contratos_vigencia_idx on contratos (vigencia_fim);
create index contratos_objeto_idx on contratos using gin (objeto_tsv);

create table pagamentos (
  id uuid primary key default gen_random_uuid(),
  fonte_id text not null references fontes(id),
  id_origem text not null,
  uf char(2) not null,
  orgao_id text references orgaos(id),
  fornecedor_cnpj char(14) not null references fornecedores(cnpj),
  contrato_id uuid references contratos(id),
  data_pagamento date,
  valor numeric(18,2),
  descricao text,
  url_origem text,
  arquivo_bruto_id uuid references arquivos_brutos(id),
  coletado_em timestamptz not null,
  hash_conteudo char(64) not null,
  unique (fonte_id, id_origem)
);
create index pagamentos_fornecedor_idx on pagamentos (fornecedor_cnpj, uf, data_pagamento);

create table sancoes (
  id uuid primary key default gen_random_uuid(),
  fonte_id text not null references fontes(id),   -- 'ceis' ou 'cnep'
  id_origem text not null,
  cnpj char(14) not null,                         -- sem FK: sancionada pode não ser fornecedora carregada
  tipo text,
  orgao_sancionador text,
  uf_orgao char(2),
  data_inicio date,
  data_fim date,
  fundamentacao text,
  url_origem text,
  arquivo_bruto_id uuid references arquivos_brutos(id),
  coletado_em timestamptz not null,
  hash_conteudo char(64) not null,
  unique (fonte_id, id_origem)
);
create index sancoes_cnpj_idx on sancoes (cnpj);

create table socios (
  cnpj char(14) not null,
  socio_chave char(64) not null,     -- sha256(nome normalizado || documento mascarado); nunca o nome em claro para PF
  socio_tipo text not null check (socio_tipo in ('PF', 'PJ')),
  socio_exibicao text not null,      -- PF mascarado: 'J*** S*** (***.456.789-**)'
  fonte_id text not null default 'receita_qsa' references fontes(id),
  coletado_em timestamptz not null,
  primary key (cnpj, socio_chave)
);
create index socios_chave_idx on socios (socio_chave);

-- ===================== Derivados =====================
create table sinais (
  id uuid primary key default gen_random_uuid(),
  fornecedor_cnpj char(14) not null,
  uf char(2),                        -- null só para sinais nacionais (sanção); demais sempre por UF
  tipo text not null check (tipo in ('sancao_direta', 'penhasco', 'concentracao', 'contagio', 'liquidez')),
  gravidade text not null check (gravidade in ('forte', 'atencao', 'info')),
  valor numeric,
  explicacao text not null,
  evidencias jsonb not null,         -- [{"tabela": "...", "id": "...", "url_origem": "..."}]
  versao_regra text not null,
  calculado_em timestamptz not null default now()
);
create index sinais_fornecedor_idx on sinais (fornecedor_cnpj, uf);

-- ===================== Do tenant =====================
create table carteiras (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  nome text not null,
  finalidade text not null check (finalidade in ('homologacao', 'monitoramento', 'renovacao')),
  criada_por uuid references usuarios(id),
  criada_em timestamptz not null default now()
);

create table carteira_itens (
  carteira_id uuid not null references carteiras(id) on delete cascade,
  tenant_id uuid not null references tenants(id),
  fornecedor_cnpj char(14) not null check (fornecedor_cnpj ~ '^[0-9]{14}$'),
  adicionado_em timestamptz not null default now(),
  primary key (carteira_id, fornecedor_cnpj)
);

create table consultas (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  usuario_id uuid not null references usuarios(id),
  carteira_id uuid references carteiras(id),
  pergunta text not null,
  plano jsonb,
  intent text,
  status text not null check (status in ('respondida', 'abstencao', 'esclarecimento', 'negada', 'erro')),
  resposta text,
  modelo text,
  versao_prompt text,
  latencia_ms int,
  criada_em timestamptz not null default now()
);

create table recibos (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  usuario_id uuid not null references usuarios(id),
  consulta_id uuid not null references consultas(id),
  conteudo jsonb not null,           -- conforme contracts/recibo.schema.json
  hash char(64) not null,            -- sha256 do JSON canônico de conteudo
  criado_em timestamptz not null default now()
);

create table alertas (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  carteira_id uuid references carteiras(id),
  fornecedor_cnpj char(14) not null,
  sinal_id uuid references sinais(id),
  status text not null default 'aberto' check (status in ('aberto', 'visto', 'resolvido')),
  criado_em timestamptz not null default now()
);

create table auditoria (
  seq bigserial primary key,
  tenant_id uuid references tenants(id),
  usuario_id uuid references usuarios(id),
  evento text not null,              -- 'login', 'consulta', 'negado', 'abstencao', 'ataque_detectado', 'export', 'erro'
  detalhes jsonb,
  criado_em timestamptz not null default now(),
  hash_anterior char(64) not null,
  hash char(64) not null
);

-- Encadeamento da auditoria por tenant: hash = sha256(hash_anterior | tenant | usuario | evento | detalhes | epoch)
-- SECURITY DEFINER: criada pelo superusuário no init, lê o último hash mesmo quando o perfil não pode ler a auditoria.
create or replace function auditoria_encadear() returns trigger
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  anterior char(64);
begin
  perform pg_advisory_xact_lock(hashtext(coalesce(new.tenant_id::text, 'global')));
  select a.hash into anterior
    from auditoria a
   where a.tenant_id is not distinct from new.tenant_id
   order by a.seq desc
   limit 1;
  new.criado_em := coalesce(new.criado_em, now());
  new.hash_anterior := coalesce(anterior, repeat('0', 64));
  new.hash := encode(digest(
      new.hash_anterior || '|' ||
      coalesce(new.tenant_id::text, '') || '|' ||
      coalesce(new.usuario_id::text, '') || '|' ||
      new.evento || '|' ||
      coalesce(new.detalhes::text, '') || '|' ||
      extract(epoch from new.criado_em)::text,
    'sha256'), 'hex');
  return new;
end $$;

create trigger auditoria_encadear_trg
  before insert on auditoria
  for each row execute function auditoria_encadear();
