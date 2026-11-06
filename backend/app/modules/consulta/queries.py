# A RLS faz o resto: consulta só entra no tenant e no nome do usuário da sessão (002_rls.sql);
# a listagem mostra as próprias consultas, ou as do tenant para auditor e admin.

INSERIR_CONSULTA = """
insert into consultas (tenant_id, usuario_id, carteira_id, pergunta, plano, intent, status, resposta,
                       modelo, versao_prompt, latencia_ms)
values (ctx_tenant(), ctx_usuario(), %(carteira_id)s, %(pergunta)s, %(plano)s, %(intent)s, %(status)s,
        %(resposta)s, %(modelo)s, %(versao_prompt)s, %(latencia_ms)s)
returning id
"""

LISTAR_CONSULTAS = """
select c.id, c.usuario_id, c.carteira_id, c.pergunta, c.intent, c.status, c.criada_em, r.id as recibo_id
  from consultas c
  left join recibos r on r.consulta_id = c.id
 order by c.criada_em desc, c.id
 limit %(limite)s
"""

BUSCAR_CARTEIRA = "select id, finalidade from carteiras where id = %(id)s"

# fontes e execucoes_ingestao não têm RLS: são metadados públicos de proveniência.
FONTES = "select id, nome, tipo from fontes where id = any(%(ids)s)"

EXECUCAO_DOS_ARQUIVOS = """
select id, execucao_id from arquivos_brutos where id = any(%(ids)s)
"""

ULTIMA_COLETA = """
select max(finalizada_em)
  from execucoes_ingestao
 where fonte_id = any(%(fontes)s) and status in ('ok', 'parcial')
"""
