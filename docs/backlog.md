# Backlog

Tarefas identificadas por ID (`T01`…`T30`). As seções citadas (§6.4, §10 etc.) são do `SPEC.md`.

Lanes: **DADOS** (Sistema 1), **PLAT** (Sistema 2: API, segurança, infra), **IA**, **FRONT** (Designer), **NEG** (Negócio e documentação).
Níveis: **N1** obrigatório · **N2** diferenciais e inovação central · **N3** se sobrar tempo.
Cada tarefa só fecha com o critério de aceite verde (ver `AGENTS.md`, "Definição de pronto").

| ID | Lane | Nível | Tarefa | Critério de aceite |
|---|---|---|---|---|
| T01 | PLAT | N1 | Compose com db, api e web; migrations aplicadas no init; `backend/app/main.py` mínimo com `/health`; scaffold Vite mínimo em `frontend/` (a FRONT completa depois); `pipeline/lastro_pipeline/cli.py` mínimo | `make up && make test-db` verde a partir de clone limpo |
| T02 | PLAT | N1 | `core/db.py`: sessão por requisição com `set_config` local e `statement_timeout` | Teste: sem contexto, `contratos` retorna 0 linhas |
| T03 | PLAT | N1 | `auth`: login com bcrypt (`auth_buscar_usuario`), JWT, `/me` | Login dos 5 usuários de seed; 401 sem token |
| T04 | PLAT | N1 | `policy`: contexto de acesso e permissão por perfil (§6.2) | Testes 5 e 6 do §6.4 |
| T05 | DADOS | N1 | Conector TCE-PE (`pe_portal`): cliente da API com paginação, cache e 1 req/s; filtros por esfera e ano; bronze com a resposta bruta; normalização (§10, regra 6); upsert idempotente; qualidade; `--amostra N` grava a fixture | Contagens estáveis em duas execuções com a fixture; PF descartado; fixture salva; contrato da resposta testado com a fixture (teste de rede marcado `@pytest.mark.rede`, rodado só por humano em rede brasileira) |
| T06 | DADOS | N1 | Conector PNCP (contratos de AL e demais UFs de `PNCP_UFS`, de um período; PE só se `PNCP_PE_FALLBACK=true`) | Idem T05; contrato da rota testado com fixture; nenhuma linha de PE vinda do PNCP com o fallback desligado |
| T07 | DADOS | N1 | Conector CEIS e CNEP | Idem T05 |
| T08 | IA | N1 | Catálogo: SQL das intents N1 com proveniência | Cada intent testada contra fixtures, sob RLS |
| T09 | IA | N1 | Planejador (gemini e mock) + validação do plano | 20 perguntas do gabarito com intent certa no mock por regras |
| T10 | IA | N1 | Redator + verificador + modelos determinísticos | Teste: número fora do resultado é reprovado e cai no fallback |
| T11 | PLAT | N1 | `consulta`: orquestração completa + gravação de consulta, recibo e auditoria | E2E da API: pergunta → resposta com citações e `recibo_id` |
| T12 | FRONT | N1 | Telas de login e consulta ligadas à API | Fluxo do passo 3 da demo funcionando |
| T13 | PLAT | N1 | Matriz de acesso completa (§6.4) | 8 casos verdes |
| T14 | NEG | N1 | README com execução do zero; `docs/catalogo-fontes.md` | Pessoa de fora sobe o sistema seguindo o README |
| T15 | PLAT | N2 | Recibo: hash canônico e `/recibos/{id}/verificar` | Alterar uma linha do recibo no banco (como superusuário) faz o selo virar "alterado" |
| T16 | PLAT | N2 | Auditoria encadeada e `/auditoria/verificar` | Idem, para a cadeia |
| T17 | DADOS | N2 | Sinais `sancao_direta`, `penhasco`, `concentracao`, por UF | Testes com fixtures; sinal de AL invisível para ana |
| T18 | PLAT | N2 | Carteiras, fila e dossiê | Fluxo dos passos 2 e 5 da demo |
| T19 | IA | N2 | `busca_objeto` (full-text) e `orgaos_fornecedor` | Testes sob RLS |
| T20 | IA | N2 | Gabarito de 100 perguntas com `sql_referencia` independente + harness | `make eval` gera `eval/reports/` |
| T21 | IA | N2 | Suíte de 50 ataques + seed do fornecedor envenenado | `make eval-ataques`; zero vazamento |
| T22 | FRONT | N2 | Telas de recibo, carteira e fila, dossiê, auditoria | Passos 2 a 5 da demo pela interface |
| T23 | NEG | N2 | Cronômetro com 3 CNPJs; validar hipótese com 3 especialistas | Registro em `docs/relatorio-avaliacao.md` |
| T24 | NEG | N2 | Documentos: arquitetura + 3 ADRs, dicionário, matriz de requisitos, modelo de ameaças, premissas e limitações | Gerados **a partir do código real** depois das 10h |
| T25 | PLAT | N2 | Resiliência: LLM fora, fonte fora | Testes do §14.5 |
| T26 | FRONT | N2 | Telas de fontes e métricas | Mostram dados reais do banco e do eval |
| T27 | DADOS | N3 | Quadro societário (só carteiras e sancionadas) + sinal `contagio` | Teste com fixture; sócio PF mascarado |
| T28 | PLAT | N3 | Alertas por evento | Nova sanção em fixture gera alerta no tenant certo |
| T29 | DADOS | N3 | Sinal `liquidez`, se o dado de PE permitir | Regra documentada e testada |
| T30 | NEG | N1 | Slides do pitch e vídeo de reserva | Entregues até 11h30 |
