# llm/ — planejador, redator e verificador

- `providers/base.py`: interface `gerar(prompt, *, json, timeout_s, temperatura) -> str` e o erro `ProvedorIndisponivel`.
- `providers/gemini.py`: provedor Gemini. `providers/__init__.py` escolhe pelo `LLM_PROVIDER`; com `mock` (ou `gemini` sem chave) não há provedor e o planejador usa as regras.
- `plano.py`: modelo Pydantic do plano (espelha `contracts/plano_consulta.schema.json`) e `validar_plano`, que também confere os parâmetros obrigatórios de cada intent.
- `regras.py`: planejador por regras (CNPJ, UF, período e palavras-chave). É o modo mock e o fallback quando a LLM cai.
- `planejador.py`: monta o prompt (`prompts/planejador_v1.md`) com o catálogo de `modules/catalogo/intents.py`, valida a saída, tenta mais 1 vez se vier inválida e depois devolve `esclarecer`. Se o provedor falhar, usa as regras.
- `redator.py`: monta o prompt (`prompts/redator_v1.md`) com o resultado; texto externo sempre dentro de `<dado_nao_confiavel>`. (a fazer)
- `verificador.py`: SPEC §8.3. Insere valores nos marcadores, reprova números, CNPJs e URLs que não vieram do resultado, e padrões de vazamento. Em reprovação, devolve o modelo determinístico. (a fazer)

O planejador nunca recebe dado do banco. O redator nunca recebe ferramentas nem o contexto de acesso.

Testes: `pytest app/llm`. O teste do gabarito lê `eval/gabarito/perguntas.yaml` (montado em `/eval` no container da API).
