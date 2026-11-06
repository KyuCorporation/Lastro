-- resumo_fornecedor@v2 — pagamentos usados no resumo, com proveniência
select p.id, p.fonte_id, p.id_origem, p.url_origem, p.coletado_em, p.hash_conteudo, p.arquivo_bruto_id,
       p.uf, p.orgao_id, o.nome as orgao_nome, p.contrato_id, p.data_pagamento, p.valor, p.descricao,
       count(*) over () as total_linhas
  from pagamentos p
  left join orgaos o on o.id = p.orgao_id
 where p.fornecedor_cnpj = %(cnpj)s
   and p.uf::text = any (%(ufs)s::text[])
 order by p.data_pagamento desc nulls last, p.id
 limit %(limite)s
