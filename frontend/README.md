# frontend/ — interface

Criar com: `npm create vite@latest . -- --template react-ts`, depois `npm i @tanstack/react-query react-router-dom` e Tailwind.

```
src/
  api/client.ts     # fetch com token; base em import.meta.env.VITE_API_URL
  api/types.ts      # espelha contracts/api.md e contracts/recibo.schema.json
  pages/            # Login, Consulta (central), Recibo, Carteira, Dossie, Auditoria, Fontes, Metricas
  components/       # Citacao, SeloIntegridade, SinalBadge, SeloSintetico, TabelaFontes
```

Prioridade e requisitos: SPEC §12. Acessibilidade AA, teclado, nada só por cor, selo "dado sintético" fixo quando aplicável.
Texto de sinal: "sinal para investigar". Nunca "fraude", "irregular", "suspeito".
