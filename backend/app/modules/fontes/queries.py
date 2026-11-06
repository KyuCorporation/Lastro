# Fontes e execuções de ingestão: metadados públicos para qualquer usuário autenticado (sem RLS em 002_rls.sql,
# só grant de select para lastro_app). Mesmo assim tudo passa pela sessão com contexto, como o resto da API.

LISTAR_FONTES = """
select f.id, f.nome, f.tipo,
       e.id as execucao_id, e.status, e.finalizada_em, e.registros_novos
  from fontes f
  left join lateral (
    select id, status, finalizada_em, registros_novos
      from execucoes_ingestao
     where fonte_id = f.id
     order by iniciada_em desc
     limit 1
  ) e on true
 order by f.id
"""

LISTAR_EXECUCOES = """
select id, fonte_id, status, iniciada_em, finalizada_em, registros_lidos, registros_novos,
       registros_descartados, left(erro, 500) as erro
  from execucoes_ingestao
 where %(fonte_id)s::text is null or fonte_id = %(fonte_id)s
 order by iniciada_em desc
 limit %(limite)s
"""
