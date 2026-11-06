-- pagamentos_periodo@v1 — pagamentos ao fornecedor no período, com total
select p.id, p.fonte_id, p.id_origem, p.url_origem, p.coletado_em, p.hash_conteudo, p.arquivo_bruto_id,
       p.uf, p.orgao_id, o.nome as orgao_nome, p.contrato_id, p.data_pagamento, p.valor, p.descricao,
       count(*) over ()     as total_linhas,
       sum(p.valor) over () as valor_total
  from pagamentos p
  left join orgaos o on o.id = p.orgao_id
 where p.fornecedor_cnpj = %(cnpj)s
   and p.uf::text = any (%(ufs)s::text[])
   and p.data_pagamento between %(data_inicio)s and %(data_fim)s
 order by p.data_pagamento, p.id
 limit %(limite)s
