-- resumo_fornecedor@v2 — totais por UF e órgão (derivado das linhas de contratos e pagamentos abaixo)
-- v2: empenho (id_origem 'emp:', TCE-PE) não é pagamento. "pago" soma o que saiu (liquidação, pagamento);
--     o empenhado vem à parte.
with c as (
  select uf, orgao_id,
         count(*)                                                   as n_contratos,
         sum(valor_global)                                          as valor_contratado,
         sum(valor_global) filter (where vigencia_fim >= %(hoje)s)  as valor_vigente
    from contratos
   where fornecedor_cnpj = %(cnpj)s
     and uf::text = any (%(ufs)s::text[])
   group by uf, orgao_id
), p as (
  select uf, orgao_id,
         count(*) filter (where id_origem not like 'emp:%%')   as n_pagamentos,
         sum(valor) filter (where id_origem not like 'emp:%%') as valor_pago,
         count(*) filter (where id_origem like 'emp:%%')       as n_empenhos,
         sum(valor) filter (where id_origem like 'emp:%%')     as valor_empenhado
    from pagamentos
   where fornecedor_cnpj = %(cnpj)s
     and uf::text = any (%(ufs)s::text[])
   group by uf, orgao_id
)
select coalesce(c.uf, p.uf)                 as uf,
       coalesce(c.orgao_id, p.orgao_id)     as orgao_id,
       o.nome                               as orgao_nome,
       coalesce(c.n_contratos, 0)           as n_contratos,
       coalesce(c.valor_contratado, 0)      as valor_contratado,
       coalesce(c.valor_vigente, 0)         as valor_vigente,
       coalesce(p.n_pagamentos, 0)          as n_pagamentos,
       coalesce(p.valor_pago, 0)            as valor_pago,
       coalesce(p.n_empenhos, 0)            as n_empenhos,
       coalesce(p.valor_empenhado, 0)       as valor_empenhado
  from c
  full join p on p.uf = c.uf and coalesce(p.orgao_id, '') = coalesce(c.orgao_id, '')
  left join orgaos o on o.id = coalesce(c.orgao_id, p.orgao_id)
 order by valor_contratado desc, uf, orgao_id
 limit %(limite)s
