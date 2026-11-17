import { useState } from "react";

import type { Evidencia, Gravidade } from "../../api/types";
import { LinkOrigem } from "../../components/LinkOrigem";
import { Selo } from "../../components/Selo";
import { GRAVIDADE, nomeSinal } from "../../lib/apresentacao";
import { dataCurta, nomeTabela } from "../../lib/formato";

export interface SinalExibido {
  tipo: string;
  gravidade: Gravidade;
  explicacao: string;
  evidencias: Evidencia[];
  /** Versão da regra que gerou o sinal e quando ele foi calculado (`make sinais`). */
  versao_regra?: string;
  calculado_em?: string;
}

/** Quantas evidências aparecem de início. Um sinal guarda até 50 e várias apontam para o mesmo recorte da fonte. */
const EVIDENCIAS_VISIVEIS = 3;

function Evidencias({ evidencias }: { evidencias: Evidencia[] }) {
  const [aberto, setAberto] = useState(false);
  const resto = evidencias.length - EVIDENCIAS_VISIVEIS;
  const visiveis = aberto ? evidencias : evidencias.slice(0, EVIDENCIAS_VISIVEIS);
  return (
    <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
      <span className="text-kyu-suave">Evidências:</span>
      {visiveis.map((e, j) => (
        <LinkOrigem key={`${e.id ?? j}`} url={e.url_origem}>
          {nomeTabela(e.tabela ?? "registro")} {j + 1}
        </LinkOrigem>
      ))}
      {resto > 0 && (
        <button
          type="button"
          aria-expanded={aberto}
          onClick={() => setAberto(!aberto)}
          className="foco rounded-md font-semibold text-kyu-laranja underline"
        >
          {aberto ? "mostrar menos" : `e mais ${resto} registro${resto === 1 ? "" : "s"}`}
        </button>
      )}
    </p>
  );
}

/** Sinais para investigar, cada um com gravidade em texto, a explicação e os links das linhas de origem. */
export function ListaSinais({ sinais, vazio = "Nenhum sinal para investigar." }: { sinais: SinalExibido[]; vazio?: string }) {
  if (sinais.length === 0) return <p className="text-kyu-suave">{vazio}</p>;
  return (
    <ul className="space-y-3">
      {sinais.map((s, i) => {
        const g = GRAVIDADE[s.gravidade] ?? GRAVIDADE.info;
        return (
          <li key={`${s.tipo}-${i}`} className="rounded-lg border border-kyu-linha p-4">
            <div className="flex flex-wrap items-center gap-3">
              <Selo tom={g.tom}>
                {g.rotulo} · {nomeSinal(s.tipo)}
              </Selo>
              {(s.versao_regra || s.calculado_em) && (
                <span className="text-sm text-kyu-suave">
                  {[s.versao_regra && `regra ${s.versao_regra}`, s.calculado_em && `calculado em ${dataCurta(s.calculado_em)}`]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              )}
            </div>
            <p className="mt-2 text-kyu-texto">{s.explicacao}</p>
            {s.evidencias.length > 0 && <Evidencias evidencias={s.evidencias} />}
          </li>
        );
      })}
    </ul>
  );
}
