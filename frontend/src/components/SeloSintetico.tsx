/** Aviso fixo quando a resposta usa dado sintético (SPEC §12: banner fixo em dados sintéticos). */
export function SeloSintetico({ simulado = false }: { simulado?: boolean }) {
  return (
    <p
      role="note"
      className="rounded-md border-2 border-dashed border-kyu-ambar bg-kyu-ambar-fundo px-3 py-2 text-sm font-semibold text-kyu-ambar"
    >
      <span aria-hidden="true">⚠ </span>
      {simulado
        ? "Resposta simulada pela interface (a consulta real ainda não está ligada). Dados fictícios."
        : "Contém dado sintético de demonstração. Não use como informação real."}
    </p>
  );
}
