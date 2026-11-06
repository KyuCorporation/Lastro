/** Rótulo quando a resposta usa um registro sintético de teste (SPEC §12). Só aparece se houver um. */
export function SeloSintetico({ simulado = false }: { simulado?: boolean }) {
  return (
    <p
      role="note"
      className="rounded-md bg-kyu-cabecalho px-3 py-1.5 text-sm text-kyu-suave"
    >
      {simulado
        ? "Resposta simulada pela interface, sem consulta ao servidor."
        : "Inclui registro sintético de teste, separado dos dados oficiais."}
    </p>
  );
}
