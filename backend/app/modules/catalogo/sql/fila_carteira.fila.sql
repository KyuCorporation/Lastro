-- fila_carteira@v1 — um registro por fornecedor da carteira: valor exposto e sinais visíveis (derivado, sem limite)
-- A carteira é do tenant: para carteira de outro tenant a RLS de carteira_itens não devolve item, e a fila sai vazia.
-- Valor exposto (SPEC §9): contratos vigentes e regulares do fornecedor nas UFs da sessão, como na tela da fila.
-- A prioridade é calculada no executor com a mesma função da fila (app/modules/carteiras/prioridade.py).
with itens as (
  select fornecedor_cnpj as cnpj
    from carteira_itens
   where carteira_id = %(carteira_id)s
),
exposto as (
  select c.fornecedor_cnpj as cnpj, count(*) as n_contratos_vigentes, sum(c.valor_global) as valor
    from contratos c
    join itens i on i.cnpj = c.fornecedor_cnpj
   where c.vigencia_fim >= %(hoje)s
     and coalesce(c.situacao, 'Regular') = 'Regular'
     and c.uf::text = any (%(ufs)s::text[])
   group by c.fornecedor_cnpj
),
sinais_item as (
  select s.fornecedor_cnpj as cnpj,
         array_agg(s.gravidade order by s.gravidade) as gravidades,
         array_agg(distinct s.tipo order by s.tipo)  as tipos
    from sinais s
    join itens i on i.cnpj = s.fornecedor_cnpj
   where s.uf is null or s.uf::text = any (%(ufs)s::text[])
   group by s.fornecedor_cnpj
)
select i.cnpj, f.razao_social,
       coalesce(e.n_contratos_vigentes, 0)::int as n_contratos_vigentes,
       coalesce(e.valor, 0)                     as valor_exposto,
       coalesce(si.gravidades, '{}'::text[])    as gravidades,
       coalesce(si.tipos, '{}'::text[])         as tipos
  from itens i
  left join fornecedores f on f.cnpj = i.cnpj
  left join exposto e on e.cnpj = i.cnpj
  left join sinais_item si on si.cnpj = i.cnpj
 order by i.cnpj
