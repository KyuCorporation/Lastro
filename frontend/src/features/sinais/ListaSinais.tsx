import type { Evidencia, Gravidade } from "../../api/types";
import { LinkOrigem } from "../../components/LinkOrigem";
import { Selo } from "../../components/Selo";
import { GRAVIDADE, nomeSinal } from "../../lib/apresentacao";
import { nomeTabela } from "../../lib/formato";

export interface SinalExibido {
  tipo: string;
  gravidade: Gravidade;
  explicacao: string;
  evidencias: Evidencia[];
  /** Só no dossiê: versão da regra que gerou o sinal. */
  versao_regra?: string;
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
              {s.versao_regra && <span className="text-sm text-kyu-suave">regra {s.versao_regra}</span>}
            </div>
            <p className="mt-2 text-kyu-texto">{s.explicacao}</p>
            {s.evidencias.length > 0 && (
              <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
                <span className="text-kyu-suave">Evidências:</span>
                {s.evidencias.map((e, j) => (
                  <LinkOrigem key={`${e.id ?? j}`} url={e.url_origem}>
                    {nomeTabela(e.tabela ?? "registro")} {j + 1}
                  </LinkOrigem>
                ))}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
