-- busca_objeto@v2 — contratos cujo objeto casa com o termo (full-text em português), os 20 mais relevantes.
-- O termo entra só como parâmetro de plainto_tsquery: nunca vira sintaxe de consulta nem SQL.
-- Acento não conta, dos dois lados: o roteador por regras tira o acento do termo, quem pergunta pode digitar sem
-- acento, e a fonte grava objeto com e sem acento ("manutenção", "MANUTENCAO"). Custo conhecido: sem acento,
-- "médica" e "medicamentos" têm o mesmo radical. Roda sem índice (objeto_tsv guarda o texto com acento).
with termo as (
  select plainto_tsquery(
           'portuguese',
           translate(lower(%(termo)s), 'áàâãäåéèêëíìîïóòôõöúùûüçñ', 'aaaaaaeeeeiiiiooooouuuucn')
         ) as q
),
achados as (
  select c.*,
         to_tsvector(
           'portuguese',
           translate(lower(coalesce(c.objeto, '')), 'áàâãäåéèêëíìîïóòôõöúùûüçñ', 'aaaaaaeeeeiiiiooooouuuucn')
         ) as objeto_sem_acento
    from contratos c
   where c.uf::text = any (%(ufs)s::text[])
)
select c.id, c.fonte_id, c.id_origem, c.url_origem, c.coletado_em, c.hash_conteudo, c.arquivo_bruto_id,
       c.uf, c.orgao_id, o.nome as orgao_nome, c.fornecedor_cnpj, f.razao_social,
       c.objeto, c.valor_global, c.data_assinatura, c.vigencia_inicio, c.vigencia_fim,
       count(*) over ()            as total_linhas,
       sum(c.valor_global) over () as valor_total
  from achados c
  cross join termo t
  left join orgaos o on o.id = c.orgao_id
  left join fornecedores f on f.cnpj = c.fornecedor_cnpj
 where c.objeto_sem_acento @@ t.q
 order by ts_rank(c.objeto_sem_acento, t.q) desc, c.valor_global desc nulls last, c.id
 limit 20
