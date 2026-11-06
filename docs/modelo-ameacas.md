# Modelo de ameaças

> Completar. Base: OWASP Top 10 para LLM. Para cada ameaça: vetor, impacto, controle no Lastro, teste que comprova (id em eval/ataques ou tests).

| Ameaça | Vetor | Controle | Teste |
|---|---|---|---|
| Injeção direta | pergunta do usuário | Action-Selector, validação do plano, escopo da sessão | A001, A005 |
| Injeção armazenada | razão social, objeto do contrato | redator em quarentena, marcadores, verificador | A002 |
| Acesso a outra UF | plano pedindo UF fora do escopo | interseção com ctx_ufs + RLS | A001, test_acesso |
| Acesso a outro tenant / IDOR | ID direto na URL | RLS por tenant; 404 sem revelar existência | A003, A004 |
| Vazamento de prompt | pedido explícito | planejador → fora_de_escopo; verificador | A005 |
| SQL injection | parâmetro | SQL parametrizado, Pydantic, catálogo fechado | A006 |
| Adulteração de registro | update direto no banco | recibo com hash, auditoria encadeada, sem update/delete para a API | testes de recibos e auditoria |
| Consumo ilimitado | rajada de perguntas | limite de 30/min, pergunta ≤ 500 caracteres, timeouts | (criar) |
