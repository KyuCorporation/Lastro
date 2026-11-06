import type { ReactNode } from "react";

/** Título numerado das telas do design ("01 Consulta inteligente"). O número não entra no nome acessível. */
export function TituloPagina({ numero, titulo, children }: { numero: string; titulo: string; children?: ReactNode }) {
  return (
    <div className="mb-6">
      <h1 className="text-3xl font-bold text-kyu-texto sm:text-4xl">
        <span aria-hidden="true">{numero} </span>
        {titulo}
      </h1>
      {children && <p className="mt-3 text-lg text-kyu-suave">{children}</p>}
    </div>
  );
}
