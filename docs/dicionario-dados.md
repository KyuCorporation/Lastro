# Dicionário de dados

Gerado a partir de `db/migrations/001_schema.sql` (com 002 a 006) e dos normalizadores da pipeline. O mapeamento campo a campo de cada fonte está em `docs/catalogo-fontes.md`. Este documento diz o que cada coluna guarda e qual regra a protege.

Convenções:
- dinheiro é `numeric(18,2)` no banco e string decimal na API (`"1234.56"`), nunca float;
- datas sem hora são `date`; momentos são `timestamptz`;
- CNPJ são 14 dígitos sem máscara (`char(14)`).

**Quem lê o quê.** Uma tabela marcada com **RLS por UF** só mostra à API as linhas das UFs da sessão. Uma marcada com **RLS por tenant** só mostra as linhas do cliente da sessão. As políticas estão em `db/migrations/002_rls.sql`.

## Proveniência (comum a todo fato público)

`contratos`, `pagamentos` e `sancoes` têm as mesmas colunas de origem:

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `fonte_id` | text → `fontes.id` | De onde veio a linha | Obrigatório |
| `id_origem` | text | Identificador na fonte (`numeroControlePNCP`, `ctr:…` do TCE-PE, `CÓDIGO DA SANÇÃO`) | Único com `fonte_id`: coletar de novo atualiza, não duplica |
| `url_origem` | text | Link para o registro na fonte, quando a fonte tem um | A interface só abre `http`/`https` |
| `arquivo_bruto_id` | uuid → `arquivos_brutos.id` | Resposta bruta da qual a linha saiu | Vazio só em dado sintético de seed |
| `coletado_em` | timestamptz | Momento da coleta | Obrigatório |
| `hash_conteudo` | char(64) | sha256 do conteúdo normalizado em JSON canônico, sem a hora da coleta | Mudou o conteúdo, mudou o hash; o recibo copia este valor |

## Fontes e ingestão

**`fontes`**: uma linha por fonte, inserida pelas migrations 004 e 005.

| Campo | Tipo | Descrição | Exemplo |
|---|---|---|---|
| `id` | text, PK | Identificador estável | `pe_portal`, `pncp`, `ceis`, `cnep`, `receita_qsa`, `demo_sintetico` |
| `nome` | text | Nome exibido | `TCE-PE Dados Abertos` |
| `tipo` | text | `api`, `arquivo` ou `sintetico` | `api` |
| `url_base`, `licenca`, `observacoes` | text | Metadados da fonte | `Dados abertos (LAI)` |

**`execucoes_ingestao`**: uma linha por execução da pipeline, gravada mesmo quando a execução falha.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `id` | uuid, PK | | |
| `fonte_id` | text → `fontes` | | |
| `iniciada_em`, `finalizada_em` | timestamptz | Início e fim | `finalizada_em` vazio = execução sem conclusão |
| `status` | text | `rodando`, `ok`, `parcial`, `falhou` | `parcial` = queda de volume em relação à execução anterior com os mesmos filtros |
| `parametros` | jsonb | Filtros usados e relatório de qualidade | |
| `registros_lidos`, `_novos`, `_atualizados`, `_descartados` | int | Contagens | Descartado = pessoa física ou registro sem CNPJ válido |
| `erro` | text | Tipo e mensagem do erro, até 2.000 caracteres | Só em `falhou` |

**`arquivos_brutos`**: camada bronze; o arquivo fica em `data/raw/<fonte>/`.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `id` | uuid, PK | | |
| `execucao_id` | uuid → `execucoes_ingestao` | Execução que baixou | |
| `fonte_id` | text → `fontes` | | |
| `caminho` | text | Caminho relativo do arquivo, ou `fixture:<fonte>/<nome>` em modo offline | |
| `url_origem` | text | URL exata da requisição | |
| `sha256` | char(64) | Hash do arquivo | Único com `fonte_id`: o mesmo arquivo não entra duas vezes |
| `bytes` | bigint | Tamanho | |
| `coletado_em` | timestamptz | Momento do download | |

## Fatos públicos

**`fornecedores`**: só pessoa jurídica. RLS: qualquer usuário autenticado.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `cnpj` | char(14), PK | | `^[0-9]{14}$`; a pipeline exige dígito verificador válido e descarta CPF |
| `razao_social` | text | Como veio da fonte | Pode conter qualquer texto, inclusive tentativa de injeção: é tratado como dado |
| `uf_sede` | char(2) | | |
| `atualizado_em` | timestamptz | | |

**`orgaos`**: RLS: qualquer usuário autenticado.

| Campo | Tipo | Descrição | Exemplo |
|---|---|---|---|
| `id` | text, PK | `<fonte>:<código>` | `pncp:<cnpj do órgão>:<unidade>`, `pe_portal:<código da UG>` |
| `nome` | text | | `Secretaria de Saúde` |
| `uf` | char(2) | | `PE` |
| `esfera` | text | `estadual`, `municipal`, `federal` (ou `distrital`, no PNCP) | |

**`contratos`**: RLS por UF. Proveniência completa.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `id` | uuid, PK | Citado nas respostas e nos recibos | |
| `uf` | char(2) | UF do órgão contratante | Filtro da RLS |
| `orgao_id` | text → `orgaos` | | |
| `fornecedor_cnpj` | char(14) → `fornecedores` | | |
| `objeto` | text | Descrição do objeto | Base da busca textual |
| `valor_global` | numeric(18,2) | Valor global (PNCP: `valorGlobal`, senão `valorInicial`) | Decimal, nunca float |
| `data_assinatura`, `vigencia_inicio`, `vigencia_fim` | date | | "Vigente" = `vigencia_fim >= hoje` |
| `objeto_tsv` | tsvector, gerado | `to_tsvector('portuguese', objeto)` com índice GIN | Usado por `busca_objeto` |

**`pagamentos`**: RLS por UF. Proveniência completa. No TCE-PE, empenhos e liquidações viram linhas desta tabela.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `id` | uuid, PK | | |
| `uf`, `orgao_id`, `fornecedor_cnpj` | | Como em `contratos` | |
| `contrato_id` | uuid → `contratos` | Quando a fonte liga o pagamento ao contrato | Opcional |
| `data_pagamento` | date | Data do empenho ou da liquidação | |
| `valor` | numeric(18,2) | | |
| `descricao` | text | No TCE-PE, começa com `empenho` ou `liquidação` | O catálogo (v2) não soma empenho como pago: separa pelo prefixo `emp:` do `id_origem` |

**`sancoes`**: CEIS e CNEP. RLS: qualquer usuário autenticado (a sanção é nacional). Proveniência completa.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `id` | uuid, PK | | |
| `cnpj` | char(14) | Sancionado | Sem FK: a empresa sancionada pode não ter contrato carregado |
| `tipo` | text | `CATEGORIA DA SANÇÃO` | |
| `orgao_sancionador`, `uf_orgao` | text, char(2) | | |
| `data_inicio`, `data_fim` | date | | Vigente = início até hoje e fim vazio ou a partir de hoje |
| `fundamentacao` | text | Até 2.000 caracteres | |

**`socios`**: quadro societário. A tabela existe, mas nenhum conector a preenche ainda (ver `premissas-limitacoes.md`). RLS: analista, auditor e admin.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `cnpj` | char(14) | Empresa | |
| `socio_chave` | char(64) | sha256 que identifica o sócio sem guardar o nome de pessoa física | |
| `socio_tipo` | text | `PF` ou `PJ` | |
| `socio_exibicao` | text | Texto exibido; PF sempre mascarado | |
| `fonte_id`, `coletado_em` | | | |

## Derivados

**`sinais`**: calculados pela pipeline (`pipeline/lastro_pipeline/sinais/`). RLS por UF, e os sinais nacionais (`uf` nula) ficam visíveis a todos.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `id` | uuid, PK | | |
| `fornecedor_cnpj` | char(14) | | |
| `uf` | char(2) | UF do cálculo | Nula só para sinal nacional; os demais são sempre por UF para não misturar estados |
| `tipo` | text | `sancao_direta`, `penhasco`, `concentracao` (calculados); `contagio`, `liquidez` (previstos no schema, sem regra) | |
| `gravidade` | text | `forte`, `atencao`, `info` | Peso na fila: 10, 3, 1 |
| `valor` | numeric | Fração ou valor que disparou o sinal | |
| `explicacao` | text | Uma frase em português | Linguagem de "sinal para investigar" |
| `evidencias` | jsonb | `[{"tabela", "id", "url_origem"}]` | Aponta para as linhas de origem |
| `versao_regra` | text | | `v1` |
| `calculado_em` | timestamptz | | |

## Dados do tenant

**`tenants`**, **`usuarios`** e **`escopos`**: identidade. A senha é bcrypt (`senha_hash`). `escopos` liga o usuário às UFs autorizadas. O login usa a função `auth_buscar_usuario`, que é `security definer` e roda antes de existir contexto.

**`carteiras`** e **`carteira_itens`**: RLS por tenant; só analista e admin gravam.

| Campo | Tipo | Descrição | Regra |
|---|---|---|---|
| `carteiras.finalidade` | text | `homologacao`, `monitoramento`, `renovacao` | Contexto da consulta além de UF e perfil (I5) |
| `carteira_itens.fornecedor_cnpj` | char(14) | | `^[0-9]{14}$`; a API valida o dígito e devolve os inválidos em `cnpjs_invalidos` |

**`consultas`**: uma por pergunta, inclusive as negadas e as que deram erro. RLS: o próprio usuário, ou auditor e admin para o tenant inteiro.

| Campo | Tipo | Descrição |
|---|---|---|
| `pergunta` | text | Até 500 caracteres (validado na API) |
| `plano` | jsonb | `PlanoConsulta` usado (`contracts/plano_consulta.schema.json`) |
| `intent` | text | Intent do catálogo |
| `status` | text | `respondida`, `abstencao`, `esclarecimento`, `negada`, `erro` |
| `resposta`, `modelo`, `versao_prompt`, `latencia_ms` | | Texto final e metadados da IA |

**`recibos`**: imutável (`lastro_app` não tem `update` nem `delete`).

| Campo | Tipo | Descrição |
|---|---|---|
| `conteudo` | jsonb | Recibo conforme `contracts/recibo.schema.json` |
| `hash` | char(64) | sha256 do JSON canônico de `conteudo`; `GET /recibos/{id}/verificar` recalcula |

**`alertas`**: RLS por tenant. Status `aberto`, `visto`, `resolvido`. A API lê; nenhum processo cria alertas ainda.

**`auditoria`**: imutável e encadeada por tenant.

| Campo | Tipo | Descrição |
|---|---|---|
| `seq` | bigserial, PK | Sorteado dentro do trigger, depois do lock do tenant |
| `evento` | text | Gravados hoje: `consulta`, `abstencao`, `negado`, `erro`, `ataque_detectado`, `dossie`, `carteira_criada`. O schema prevê também `login` e `export`, que o código ainda não grava |
| `detalhes` | jsonb | Motivo, intent, ids; nunca senha, token ou prompt |
| `hash_anterior`, `hash` | char(64) | `sha256(hash_anterior \| tenant \| usuario \| evento \| detalhes \| epoch)` |

## Views

Todas com `security_invoker = true`, ou seja, respeitam a RLS de quem consulta (`003_views.sql`): `v_contratos_vigentes`, `v_resumo_fornecedor` e `v_pagamentos_fornecedor`.
