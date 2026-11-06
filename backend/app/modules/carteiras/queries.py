# Carteiras são do tenant: a RLS (002_rls.sql) limita leitura ao tenant da sessão e escrita a analista e admin.
# Fatos públicos (contratos, sinais) já chegam filtrados pela RLS às UFs do usuário; o filtro explícito por
# ctx_ufs() abaixo é defesa em profundidade, não a barreira principal.

INSERIR_CARTEIRA = """
insert into carteiras (tenant_id, nome, finalidade, criada_por)
values (ctx_tenant(), %(nome)s, %(finalidade)s, ctx_usuario())
returning id, criada_em
"""

INSERIR_ITEM = """
insert into carteira_itens (carteira_id, tenant_id, fornecedor_cnpj)
values (%(carteira_id)s, ctx_tenant(), %(cnpj)s)
on conflict (carteira_id, fornecedor_cnpj) do nothing
"""

LISTAR_CARTEIRAS = """
select c.id, c.nome, c.finalidade, c.criada_em, count(i.fornecedor_cnpj)::int as n_itens
  from carteiras c
  left join carteira_itens i on i.carteira_id = c.id
 group by c.id
 order by c.criada_em desc, c.id
 limit %(limite)s
"""

BUSCAR_CARTEIRA = """
select id, nome, finalidade, criada_em
  from carteiras
 where id = %(id)s
"""

# Um registro por item da carteira: identidade, valor vigente nas UFs do usuário e sinais visíveis.
FILA = """
with itens as (
  select fornecedor_cnpj as cnpj
    from carteira_itens
   where carteira_id = %(id)s
),
exposto as (
  select c.fornecedor_cnpj as cnpj, sum(c.valor_global) as valor
    from contratos c
    join itens i on i.cnpj = c.fornecedor_cnpj
   where c.vigencia_fim >= %(hoje)s
     and c.uf::text = any (ctx_ufs())
   group by c.fornecedor_cnpj
),
sinais_item as (
  select s.fornecedor_cnpj as cnpj,
         jsonb_agg(
           jsonb_build_object('tipo', s.tipo, 'gravidade', s.gravidade, 'explicacao', s.explicacao,
                              'evidencias', s.evidencias)
           order by case s.gravidade when 'forte' then 0 when 'atencao' then 1 else 2 end, s.tipo, s.uf
         ) as lista
    from sinais s
    join itens i on i.cnpj = s.fornecedor_cnpj
   where s.uf is null or s.uf::text = any (ctx_ufs())
   group by s.fornecedor_cnpj
)
select i.cnpj, f.razao_social, coalesce(e.valor, 0) as valor_exposto, coalesce(si.lista, '[]'::jsonb) as sinais
  from itens i
  left join fornecedores f on f.cnpj = i.cnpj
  left join exposto e on e.cnpj = i.cnpj
  left join sinais_item si on si.cnpj = i.cnpj
"""
