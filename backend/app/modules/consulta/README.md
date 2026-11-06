# consulta/ — POST /consultas e GET /consultas

```
pergunta → guardas (código) → planejador → executor do catálogo (RLS) → redator + verificador
         → consulta + recibo + auditoria numa transação → resposta com citações e recibo_id
```

| Arquivo | Papel |
|---|---|
| `router.py` | Rotas. `POST` exige perfil que consulta (`policy`, 403 auditado) e limite de 30/min por usuário (429). `GET` lista o que a RLS mostra (próprias; auditor e admin veem o tenant) |
| `dependencias.py` | Provedor de LLM, relógio e limitador, trocáveis nos testes (`app.dependency_overrides`) |
| `guardas.py` | Antes de qualquer LLM: pedido para burlar regras e UF fora do escopo viram negação |
| `service.py` | Orquestração. Cada caminho vira um `Desfecho`; `_gravar` persiste todos do mesmo jeito |
| `citacoes.py` | Linhas citáveis do resultado → citações (até 50) e linhas do recibo (todas). A LLM nunca escreve citação |
| `fontes.py` | Fonte, coleta e execução de cada linha citada (recibo) e a data da última coleta (abstenção) |
| `queries.py` | SQL |

## Desfechos

| Situação | HTTP | `status` | Recibo | Auditoria |
|---|---|---|---|---|
| Resposta (modelo ou LLM aprovada) | 200 | `respondida` | sim (`aprovado`/`fallback`) | `consulta` (+ `ataque_detectado` se o verificador pegou injeção) |
| Resultado vazio, fora do catálogo, intent sem SQL | 200 | `abstencao` | sim (`abstencao`) | `abstencao` |
| Pergunta vaga, CNPJ com dígito errado | 200 | `esclarecimento` | não | `consulta` |
| Outra UF (pergunta ou plano), pedido para burlar regras | 403 `ESCOPO_NEGADO` | `negada` (gravada) | não | `negado` com `motivo` |
| Carteira inexistente ou de outro tenant | 404 | — | — | — |
| Erro inesperado / tempo esgotado no banco | 500 / 503 | `erro` (gravada) | não | `erro` |

A negação nunca diz quantos registros existem fora do escopo. O escopo vem só do token: campo a mais no corpo é ignorado.

## Recibo

Montado em `modules/recibos/montagem.py` conforme `contracts/recibo.schema.json` e gravado com
`hash = sha256(JSON canônico)` (`modules/recibos/canonico.py`). `GET /recibos/{id}` devolve 404 para quem
não é dono, auditor ou admin do tenant. O teste confere o schema e que o hash recalculado do que voltou do
banco é igual ao gravado (base do `/recibos/{id}/verificar`, T15).

Testes: `pytest app/modules/consulta app/modules/recibos` (Postgres do Compose com seeds).
