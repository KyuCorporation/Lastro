-- orgaos_fornecedor@v1 — ranking de órgãos por valor contratado e participação (derivado dos contratos abaixo)
with por_orgao as (
  select c.uf, c.orgao_id,
         count(*)              as n_contratos,
         sum(c.valor_global)   as valor_contratado
    from contratos c
   where c.fornecedor_cnpj = %(cnpj)s
     and c.uf::text = any (%(ufs)s::text[])
   group by c.uf, c.orgao_id
)
select p.uf, p.orgao_id, o.nome as orgao_nome, o.esfera,
       p.n_contratos,
       coalesce(p.valor_contratado, 0) as valor_contratado,
       round(100 * coalesce(p.valor_contratado, 0) / nullif(sum(p.valor_contratado) over (), 0), 2)
         as participacao
  from por_orgao p
  left join orgaos o on o.id = p.orgao_id
 order by valor_contratado desc, p.orgao_id
 limit %(limite)s
