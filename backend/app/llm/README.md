# llm/ — planejador, redator e verificador

- `providers/base.py`: interface `gerar(prompt, *, json=False, timeout) -> str`.
- `providers/gemini.py` e `providers/mock.py`. O mock é determinístico: planejador por regras (CNPJ e palavras-chave) e redator por modelo de resposta.
- `planejador.py`: monta o prompt (`prompts/planejador_v1.md`), valida contra `contracts/plano_consulta.schema.json`, tenta 1 vez, senão `esclarecer`. Se o provedor falhar, cai no planejador por regras.
- `redator.py`: monta o prompt (`prompts/redator_v1.md`) com o resultado; texto externo sempre dentro de `<dado_nao_confiavel>`.
- `verificador.py`: SPEC §8.3. Insere valores nos marcadores, reprova números, CNPJs e URLs que não vieram do resultado, e padrões de vazamento. Em reprovação, devolve o modelo determinístico.

O planejador nunca recebe dado do banco. O redator nunca recebe ferramentas nem o contexto de acesso.
