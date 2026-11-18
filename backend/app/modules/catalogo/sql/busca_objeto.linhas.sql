-- busca_objeto@v3 — contratos cujo objeto casa com o termo (full-text em português), os 20 mais relevantes.
-- O termo entra só como parâmetro (plainto_tsquery e ts_lexize): nunca vira sintaxe de consulta nem SQL.
-- Acento não conta, dos dois lados (v2): o roteador por regras tira o acento do termo, quem pergunta pode digitar
-- sem acento, e a fonte grava objeto com e sem acento ("manutenção", "MANUTENCAO").
-- v3: sem acento, palavras diferentes podem cair no mesmo radical ("médica" e "medicamentos" viram "medic").
-- Cada palavra do termo precisa de uma palavra do objeto com o mesmo radical e quase o mesmo tamanho (até 2 letras
-- de diferença: plural, "-es"). Roda sem índice (objeto_tsv guarda o texto com acento).
with termo as (
  select plainto_tsquery('portuguese', t) as q, t
    from (
      select translate(lower(%(termo)s), 'áàâãäåéèêëíìîïóòôõöúùûüçñ', 'aaaaaaeeeeiiiiooooouuuucn') as t
    ) sem_acento
),
-- Palavras do termo que contam para a busca (palavra vazia, como "de", não tem radical) e o radical de cada uma.
palavras_termo as (
  select p.palavra, (ts_lexize('portuguese_stem', p.palavra))[1] as radical
    from termo, regexp_split_to_table(termo.t, '[^a-z0-9]+') as p(palavra)
   where p.palavra <> ''
),
achados as (
  select c.*, x.texto,
         to_tsvector('portuguese', x.texto) as objeto_sem_acento
    from contratos c
   cross join lateral (
     select translate(lower(coalesce(c.objeto, '')), 'áàâãäåéèêëíìîïóòôõöúùûüçñ', 'aaaaaaeeeeiiiiooooouuuucn')
            as texto
   ) x
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
   and not exists (
     select 1
       from palavras_termo pt
      where pt.radical is not null
        and not exists (
          select 1
            from regexp_split_to_table(c.texto, '[^a-z0-9]+') as o(palavra)
           where (ts_lexize('portuguese_stem', o.palavra))[1] = pt.radical
             and abs(length(o.palavra) - length(pt.palavra)) <= 2
        )
   )
 order by ts_rank(c.objeto_sem_acento, t.q) desc, c.valor_global desc nulls last, c.id
 limit 20
