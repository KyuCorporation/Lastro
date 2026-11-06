# Contrato da API (v1) — congelado

Base: `http://localhost:8000`. Autenticação por `Authorization: Bearer <jwt>` em tudo, exceto `/health` e `/auth/login`.
Dinheiro como string decimal (`"1234.56"`). Datas em ISO 8601. Erros sempre:

```json
{ "erro": { "codigo": "ESCOPO_NEGADO", "mensagem": "Você não tem acesso a dados de AL.", "request_id": "uuid" } }
```

Códigos de erro: `NAO_AUTENTICADO` (401), `PERFIL_SEM_PERMISSAO` (403), `ESCOPO_NEGADO` (403), `NAO_ENCONTRADO` (404, também usado para recurso de outro tenant, para não revelar existência), `ENTRADA_INVALIDA` (422), `LIMITE_EXCEDIDO` (429), `FONTE_INDISPONIVEL` (503), `ERRO_INTERNO` (500).

| Método | Rota | Perfis | Entrada | Saída |
|---|---|---|---|---|
| GET | `/health` | público | — | `{status, db, llm}` |
| POST | `/auth/login` | público | `{email, senha}` | `{token, usuario: {id, nome, perfil, tenant, ufs}}` |
| GET | `/me` | todos | — | `{id, nome, perfil, tenant: {id, nome}, ufs}` |
| GET | `/fontes` | todos | — | `[{id, nome, tipo, ultima_execucao: {id, status, finalizada_em, registros_novos}}]` |
| GET | `/fontes/execucoes` | todos | `?fonte_id` | `[{id, fonte_id, status, iniciada_em, finalizada_em, registros_lidos, registros_novos, registros_descartados, erro}]` |
| POST | `/carteiras` | analista, admin | `{nome, finalidade, cnpjs: [string]}` | `{id, nome, finalidade, n_itens, cnpjs_invalidos: []}` |
| GET | `/carteiras` | todos | — | `[{id, nome, finalidade, n_itens, criada_em}]` |
| GET | `/carteiras/{id}/fila` | todos | — | `{carteira, itens: [{cnpj, razao_social, prioridade, valor_exposto, sinais: [{tipo, gravidade, explicacao, evidencias}]}]}` |
| GET | `/fornecedores/{cnpj}/dossie` | todos | — | `{fornecedor, resumo_por_uf, contratos_vigentes, vencendo_180d, sancoes, sinais, socios?, fontes}` (cada item com `fonte_id`, `url_origem`, `coletado_em`) |
| POST | `/consultas` | analista, admin | `{pergunta (≤500 chars), carteira_id?}` | `{consulta_id, status, resposta, citacoes: [{n, tabela, id, fonte_id, url_origem, coletado_em}], recibo_id, sintetico: bool}` |
| GET | `/consultas` | todos | `?limite` | consultas visíveis pela RLS |
| GET | `/recibos/{id}` | dono, auditor, admin | — | `{id, conteudo (recibo.schema.json), hash, criado_em}` |
| GET | `/recibos/{id}/verificar` | dono, auditor, admin | — | `{integro: bool, hash_gravado, hash_recalculado}` |
| GET | `/alertas` | todos | `?status` | `[{id, carteira_id, cnpj, sinal, status, criado_em}]` |
| GET | `/auditoria` | auditor, admin | `?evento&limite` | `[{seq, usuario_id, evento, detalhes, criado_em, hash}]` |
| GET | `/auditoria/verificar` | auditor, admin | — | `{integra: bool, n_eventos, primeiro_seq_quebrado?}` |
| GET | `/metricas` | todos | — | `{eval: {...}, ataques: {...}, cronometro: {...}, ultima_atualizacao}` (lê `eval/reports/`) |

Regras transversais:
- Todo acesso negado (perfil ou escopo) grava `auditoria.evento = 'negado'` com motivo.
- `POST /consultas` tem limite de 30 por minuto por usuário.
- A resposta de `POST /consultas` nunca contém dados fora do escopo, nem a contagem de registros de UFs não autorizadas.
