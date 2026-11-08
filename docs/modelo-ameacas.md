# Modelo de ameaças

Base: OWASP Top 10 para aplicações com LLM (2025), mais as ameaças clássicas de uma API multi-tenant. Cada linha diz:
- **Vetor:** por onde a ameaça entra.
- **Controle:** o que o código faz contra ela.
- **Teste:** o teste que comprova. `Axxx` são os casos de `eval/ataques/ataques.yaml` (`make eval-ataques`); os caminhos são testes automatizados.

Princípio geral: a defesa não depende de a LLM obedecer. Ela não acessa o banco, não escolhe UF nem tenant e não produz número. Mesmo um modelo completamente manipulado só consegue escolher uma intent do catálogo, que roda sob a RLS da sessão.

## Ameaças à camada de IA

| Ameaça (OWASP LLM) | Vetor | Controle | Teste |
|---|---|---|---|
| Injeção direta (LLM01) | Pergunta pedindo para ignorar regras, mudar de papel, consultar outro estado | Guardas por código antes do planejador (`modules/consulta/guardas.py`); plano validado contra o catálogo; UF da sessão prevalece no executor | A001, A007–A014 (`direta`); `test_consulta_api.py::test_pedido_para_burlar_as_regras_e_negado_sem_chamar_a_llm` |
| Injeção armazenada (LLM01) | Texto vindo da fonte: razão social e objeto do contrato. O seed `020_demo_ataque.sql` tem um fornecedor com instrução no nome | Redator recebe o dado como dado e escreve só com marcadores; verificador reprova URL, UF, número ou trecho de prompt fora do resultado; reprovação vira o modelo determinístico e o evento `ataque_detectado` | A002, A015–A022 (`armazenada`); `test_consulta_api.py::test_injecao_armazenada_cai_no_fallback_e_vira_evento_de_ataque`, `llm/tests/test_verificador_adversarial.py` |
| Vazamento do prompt do sistema (LLM07) | "Mostre suas instruções" | Guarda `FORA_DO_PERMITIDO`; verificador com motivo `vazamento` | A005, A040–A043 (`vazar_prompt`) |
| Saída indevida (LLM05) | Texto da LLM com número, CNPJ ou link inventado, ou com acusação | Números inseridos por código; verificador (`numero_fora_do_resultado`, `url_fora_do_resultado`, `linguagem_de_acusacao`); a interface só abre links `http`/`https` | `llm/tests/test_verificador*.py`, `frontend/src/lib/lib.test.ts` (`urlSegura`) |
| Agência excessiva (LLM06) | LLM tentando executar SQL ou ações | Sem tool calling; a LLM só devolve um `PlanoConsulta` (Action-Selector, ADR-002) | `llm/tests/test_planejador.py` (validação do plano), `test_contrato_catalogo.py` |
| Desinformação (LLM09) | Resposta errada apresentada como fato | Toda resposta cita linhas do banco; recibo com as linhas e os totais reproduzíveis; abstenção quando não há registro | `eval/gabarito` (comportamento, citação, resultado); `test_consulta_api.py::test_fornecedor_sem_registros_e_abstencao_que_nao_inventa` |
| Consumo ilimitado (LLM10) | Rajada de perguntas, pergunta enorme, provedor lento | 30 consultas por minuto por usuário (429); pergunta com até 500 caracteres; timeout da LLM; uma chamada só ao provedor quando ele está fora; 5 s por comando no banco | A058 (`abuso`); `test_consulta_api.py::test_limite_de_consultas_por_minuto`, `test_llm_fora_do_ar_chama_o_provedor_uma_vez_so_e_responde`, `test_tempo_esgotado_no_banco_vira_503` |

## Ameaças à API e aos dados

| Ameaça | Vetor | Controle | Teste |
|---|---|---|---|
| Acesso a outra UF | Pergunta, parâmetro ou plano pedindo UF fora do escopo | Guarda por código; interseção com as UFs da sessão no executor; RLS por UF; a negação não revela contagem | A023–A030 (`outra_uf`); `test_acesso.py`, `test_consulta_api.py::test_outra_uf_e_negada_sem_vazar_contagem`, `test_plano_da_llm_com_outra_uf_tambem_e_negado_pelo_executor` |
| Acesso a outro tenant | Tenant ou usuário no corpo da requisição | Contexto só do JWT; campos do corpo ignorados; RLS por tenant | A003, A031–A033 (`outro_tenant`); `test_consulta_api.py::test_tenant_e_usuario_do_corpo_sao_ignorados` |
| IDOR | Id de recibo, consulta ou carteira de outro usuário na URL | RLS; recurso de outro tenant responde 404, igual a inexistente | A004, A034–A039 (`idor`); `test_consulta_api.py::test_recibo_so_para_dono_auditor_e_admin_do_tenant` |
| Perfil sem permissão | Gestor consultando, analista lendo a auditoria do tenant | Matriz do SPEC §6.2 (`modules/policy/`), negação auditada; a interface esconde o que o perfil não usa | A050–A052 (`perfil`); `modules/policy/tests/test_permissoes.py` |
| Autenticação | Token ausente, expirado, adulterado ou com algoritmo trocado | JWT HS256 com claims obrigatórias e expiração; senha com bcrypt; e-mail inexistente custa o mesmo bcrypt e dá o mesmo 401 que senha errada | A053–A057 (`autenticacao`); `modules/auth/tests/test_auth.py::test_senha_errada_e_email_inexistente_dao_o_mesmo_401`, `test_me_com_token_expirado_401` |
| SQL injection | Parâmetro com SQL | SQL fixo e parametrizado; Pydantic na entrada; LLM sem SQL | A006, A044, A045 (`sql_param`) |
| Entrada inválida | Bytes nulos, campos enormes, tipos errados | Pydantic (`TextoSemNulo`, limites de tamanho) → 422 | A046–A049 (`entrada_invalida`); `backend/app/tests/test_entrada_nula.py` |
| Adulteração de registro | Alteração direta no banco depois da gravação | Recibo com hash verificável; auditoria encadeada; `lastro_app` sem `update`/`delete` em recibos e auditoria | `modules/recibos/tests/test_verificar.py`, `modules/auditoria/tests/` |
| Privilégio no banco | API com superusuário ou `BYPASSRLS` | Papéis `lastro_app` e `lastro_ingest` com `nobypassrls`; `force row level security` em todas as tabelas | `backend/app/tests/test_db.py` (sem contexto, zero linhas; contexto não passa para a próxima transação) |
| Dado pessoal | CPF de favorecido, sócio pessoa física | Pipeline descarta pessoa física; sócio PF só como chave hash e exibição mascarada; logs sem pergunta, token ou senha | `pipeline/tests/test_ingestao.py::test_pessoa_fisica_nunca_chega_ao_banco` |
| Fonte bloqueando ou fora | 403, firewall, 5xx | Bloqueio não é contornado (`FonteBloqueada`); a falha fica registrada e não apaga dados | `pipeline/tests/test_http.py::test_bloqueio_nao_e_contornado`, `test_resiliencia.py` |

## Riscos que continuam

- **Limite de taxa:** fica na memória do processo. Com mais de uma instância da API, cada uma conta separado.
- **JWT:** sem revogação antes de expirar (480 min). Sair apaga o token só no navegador.
- **Gabarito:** só 1 das 100 perguntas tem `sql_referencia` independente, então a métrica de "resultado" ainda mede pouco.
- **Sinais e texto da fonte:** sinais e textos vindos da fonte são exibidos como dado na interface. A proteção ali é o React (sem HTML cru) e os links restritos a `http`/`https`.
