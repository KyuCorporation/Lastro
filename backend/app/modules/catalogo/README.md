# catalogo/ — consultas parametrizadas

- `intents.py`: as 11 intents do SPEC §7, com parâmetros obrigatórios e opcionais e a descrição curta que vai no prompt do planejador.
- `registry.py`: intents que consultam o banco, com versão (vai para o recibo como `intent@versao`) e conjuntos de SQL. Hoje: as 5 intents N1 (`resumo_fornecedor`, `contratos_vigentes`, `contratos_vencendo`, `pagamentos_periodo`, `sancoes_fornecedor`).
- `sql/<intent>.<conjunto>.sql`: SQL fixo e parametrizado. `resumo_fornecedor` tem três conjuntos (`por_uf_orgao`, `contratos`, `pagamentos`); as demais têm `linhas`.
- `executor.py`: `executar(plano, ctx, hoje)` valida o CNPJ (dígitos verificadores), resolve a UF efetiva, roda os conjuntos dentro de `sessao(ctx)` e devolve um `ResultadoConsulta` com linhas, totais e a marca de truncado.

Regras:
- Toda linha citável traz as colunas de proveniência (`id`, `fonte_id`, `id_origem`, `url_origem`, `coletado_em`, `hash_conteudo`, `arquivo_bruto_id`).
- A UF efetiva é `parametros.uf ∩ ufs da sessão`. Se o plano pedir UF fora do escopo, o executor levanta `ESCOPO_NEGADO` (403) sem consultar. A RLS filtra de novo no banco.
- Sanções são nacionais: `sancoes_fornecedor` não filtra por UF.
- Totais vêm do SQL (funções de janela antes do `LIMIT`), então ficam certos mesmo quando as linhas são cortadas em 200.
- Nada de SQL dinâmico além de parâmetros. `statement_timeout` de 5 s pela sessão.
- `fora_de_escopo` e `esclarecer` não consultam o banco (`IntentSemConsulta`). As intents N2 e N3 ainda não têm SQL.

Os marcadores e o modelo de resposta determinístico de cada intent ficam em `app/llm/marcadores.py`.

Testes: `pytest app/modules/catalogo`. Eles gravam linhas sintéticas (`id_origem` `TCAT-*`) como superusuário só para montar o cenário, e apagam no fim; as consultas rodam como `lastro_app`, sob RLS.
