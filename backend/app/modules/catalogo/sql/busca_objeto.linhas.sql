-- busca_objeto@v1 — contratos cujo objeto casa com o termo (full-text em português), os 20 mais relevantes.
-- O termo entra só como parâmetro de plainto_tsquery: nunca vira sintaxe de consulta nem SQL.
with termo as (select plainto_tsquery('portuguese', %(termo)s) as q)
select c.id, c.fonte_id, c.id_origem, c.url_origem, c.coletado_em, c.hash_conteudo, c.arquivo_bruto_id,
       c.uf, c.orgao_id, o.nome as orgao_nome, c.fornecedor_cnpj, f.razao_social,
       c.objeto, c.valor_global, c.data_assinatura, c.vigencia_inicio, c.vigencia_fim,
       count(*) over ()            as total_linhas,
       sum(c.valor_global) over () as valor_total
  from contratos c
  cross join termo t
  left join orgaos o on o.id = c.orgao_id
  left join fornecedores f on f.cnpj = c.fornecedor_cnpj
 where c.objeto_tsv @@ t.q
   and c.uf::text = any (%(ufs)s::text[])
 order by ts_rank(c.objeto_tsv, t.q) desc, c.valor_global desc nulls last, c.id
 limit 20
