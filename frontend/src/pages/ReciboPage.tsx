import { Link, useParams } from "react-router-dom";

/** Destino do botão "Ver recibo". A tela completa (plano, linhas, selo de integridade) é a T22. */
export function ReciboPage() {
  const { id } = useParams();
  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Recibo</h1>
      <p className="mt-2 text-slate-800">
        Identificador: <code className="break-all">{id}</code>
      </p>
      <p className="mt-6">
        <Link to="/" className="text-blue-800 underline">
          Voltar para a consulta
        </Link>
      </p>
    </main>
  );
}
