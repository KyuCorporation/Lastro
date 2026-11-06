-- contratos_vencendo@v1 — contratos vigentes que terminam no prazo em dias, com o valor vigente total
with vigentes as (
  select c.*
    from contratos c
   where c.fornecedor_cnpj = %(cnpj)s
     and c.uf::text = any (%(ufs)s::text[])
     and c.vigencia_fim >= %(hoje)s
)
select v.id, v.fonte_id, v.id_origem, v.url_origem, v.coletado_em, v.hash_conteudo, v.arquivo_bruto_id,
       v.uf, v.orgao_id, o.nome as orgao_nome, v.objeto, v.valor_global,
       v.data_assinatura, v.vigencia_inicio, v.vigencia_fim,
       count(*) over ()                               as total_linhas,
       sum(v.valor_global) over ()                    as valor_total,
       (select sum(valor_global) from vigentes)       as valor_vigente_total
  from vigentes v
  left join orgaos o on o.id = v.orgao_id
 where v.vigencia_fim <= %(hoje)s::date + %(dias)s::int
 order by v.vigencia_fim, v.id
 limit %(limite)s
