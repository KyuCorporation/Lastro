import { Fragment, useMemo } from "react";

import { dividirEmTrechos } from "../../lib/destaques";

/** Texto da resposta com valores destacados, lidos por extenso no leitor de tela, e citações [n] clicáveis. */
export function TextoResposta({ texto, idCitacao }: { texto: string; idCitacao: (n: number) => string }) {
  const trechos = useMemo(() => dividirEmTrechos(texto), [texto]);
  return (
    <p className="text-lg leading-relaxed text-slate-900">
      {trechos.map((t, i) => {
        switch (t.tipo) {
          case "moeda":
          case "data":
            return (
              <mark key={i} className="rounded bg-blue-100 px-1 font-semibold text-blue-950">
                <span aria-hidden="true">{t.texto}</span>
                <span className="sr-only">{t.falado}</span>
              </mark>
            );
          case "numero":
            return (
              <mark key={i} className="rounded bg-blue-100 px-1 font-semibold text-blue-950">
                {t.texto}
              </mark>
            );
          case "citacao":
            return (
              <a
                key={i}
                href={`#${idCitacao(t.n)}`}
                className="align-super text-sm font-semibold text-blue-800 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"
                aria-label={`fonte ${t.n}`}
              >
                {t.texto}
              </a>
            );
          default:
            return <Fragment key={i}>{t.texto}</Fragment>;
        }
      })}
    </p>
  );
}
