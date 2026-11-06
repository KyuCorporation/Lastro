-- contratos_vigentes@v1 — contratos com vigência até hoje ou depois
select c.id, c.fonte_id, c.id_origem, c.url_origem, c.coletado_em, c.hash_conteudo, c.arquivo_bruto_id,
       c.uf, c.orgao_id, o.nome as orgao_nome, c.objeto, c.valor_global,
       c.data_assinatura, c.vigencia_inicio, c.vigencia_fim,
       count(*) over ()          as total_linhas,
       sum(c.valor_global) over () as valor_total
  from contratos c
  left join orgaos o on o.id = c.orgao_id
 where c.fornecedor_cnpj = %(cnpj)s
   and c.uf::text = any (%(ufs)s::text[])
   and c.vigencia_fim >= %(hoje)s
 order by c.vigencia_fim, c.id
 limit %(limite)s
