import { Fragment, useMemo } from "react";

import { dividirEmTrechos } from "../../lib/destaques";

/** Texto da resposta com valores destacados, lidos por extenso no leitor de tela, e citações [n] clicáveis. */
export function TextoResposta({ texto, idCitacao }: { texto: string; idCitacao: (n: number) => string }) {
  const trechos = useMemo(() => dividirEmTrechos(texto), [texto]);
  return (
    <p className="text-xl font-semibold leading-relaxed text-kyu-texto">
      {trechos.map((t, i) => {
        switch (t.tipo) {
          case "moeda":
          case "data":
            return (
              <mark key={i} className="bg-transparent font-bold text-kyu-texto">
                <span aria-hidden="true">{t.texto}</span>
                <span className="sr-only">{t.falado}</span>
              </mark>
            );
          case "numero":
            return (
              <mark key={i} className="bg-transparent font-bold text-kyu-texto">
                {t.texto}
              </mark>
            );
          case "citacao":
            return (
              <a
                key={i}
                href={`#${idCitacao(t.n)}`}
                className="foco align-super text-sm font-semibold text-kyu-laranja underline"
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
