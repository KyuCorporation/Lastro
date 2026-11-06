export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <p role="status" aria-live="polite" className="p-6 text-kyu-suave">
      {texto}
    </p>
  );
}
