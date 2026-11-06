# llm/ — planejador, redator e verificador

- `providers/base.py`: interface `gerar(prompt, *, json, timeout_s, temperatura) -> str` e o erro `ProvedorIndisponivel`.
- `providers/gemini.py`: provedor Gemini. `providers/__init__.py` escolhe pelo `LLM_PROVIDER`; com `mock` (ou `gemini` sem chave) não há provedor e o planejador usa as regras.
- `plano.py`: modelo Pydantic do plano (espelha `contracts/plano_consulta.schema.json`) e `validar_plano`, que também confere os parâmetros obrigatórios de cada intent.
- `regras.py`: planejador por regras (CNPJ, UF, período e palavras-chave). É o modo mock e o fallback quando a LLM cai.
- `planejador.py`: monta o prompt (`prompts/planejador_v1.md`) com o catálogo de `modules/catalogo/intents.py`, valida a saída, tenta mais 1 vez se vier inválida e depois devolve `esclarecer`. Se o provedor falhar, usa as regras.
- `marcadores.py`: para cada intent (`@modelo_da_intent`), os marcadores (`{{v1}}` → valor, tipo, significado, origem), quais são **essenciais** (carregam a resposta; CNPJ, UFs, prazo e período não contam) e o modelo determinístico (texto pronto). Resultado vazio vira abstenção; com `fontes_coletadas_em`, ela termina com "Fontes coletadas até dd/mm/aaaa." (SPEC §8.4). Consulta do catálogo sem modelo derruba a importação.
- `formatacao.py`: R$ com duas casas, datas dd/mm/aaaa (também de texto ISO), percentual e CNPJ com máscara para o texto; valor cru para o recibo.
- `texto_externo.py`: quarentena. Texto de fonte vai em `<dado_nao_confiavel>` e a pergunta em `<pergunta_do_usuario>`, sem quebras de linha, `{{ }}`, links nem caracteres invisíveis, e sem como fechar a marcação em nenhuma grafia. Números de fonte viram `#`.
- `lexico.py`: listas que o verificador procura (quantidade e data por extenso, acusação, vazamento, negar registros). Palavra nova só deixa o verificador mais rígido.
- `redator.py`: monta o prompt (`prompts/redator_v2.md`) em uma passada só (nada inserido é relido como placeholder). Resultado vazio: abstenção sem chamar a LLM. Modo mock: modelo determinístico. Saída da LLM: tira cerca de código e aspas em volta e passa pelo verificador. Reprovado, provedor fora ou **qualquer** exceção do provedor: modelo determinístico com status `fallback`.
- `verificador.py`: SPEC §8.3, em regras independentes (`REGRAS`; regra nova = uma função). Reprova: texto vazio ou longo; caractere invisível, de controle, bidirecional ou letra não latina (homóglifo); marcador desconhecido ou quebrado; número, data ou quantidade fora dos marcadores, em algarismo de qualquer alfabeto ou por extenso (anos do plano são permitidos); link ou e-mail; vazamento; acusação; UF fora do escopo; negar registros que o resultado tem; não usar nenhum marcador essencial. Ao preencher, "R$ {{v}}" e "{{v}}%" não duplicam o símbolo.

### Para quem chama (T11)

```python
r = redigir(pergunta, resultado, ufs_autorizadas=ctx.ufs, provedor=obter_provedor(settings),
            fontes_coletadas_em=coleta_mais_recente)  # opcional
r.texto            # resposta final, valores já inseridos pelo código
r.status           # "aprovado" | "fallback" | "abstencao"  → recibo.verificacao.status
r.motivos          # por que caiu no fallback                → recibo.verificacao.motivos
r.valores          # {"v4": {"valor": "100000.00", "tipo": "moeda", "origem": ...}} → recibo.valores
r.provedor, r.modelo, r.versao_prompt                        → recibo.ia
```

O texto nunca traz `[n]` de citação: a LLM não pode escrever números. As citações vêm do código, a partir das linhas do resultado.

O planejador nunca recebe dado do banco. O redator nunca recebe ferramentas nem o contexto de acesso.

Testes: `pytest app/llm`. `test_contrato_catalogo.py` roda o executor do catálogo (T08) no Postgres e passa o resultado pela redação: quebra se o catálogo mudar um nome que os modelos usam. O teste do gabarito lê `eval/gabarito/perguntas.yaml` (montado em `/eval` no container da API).
