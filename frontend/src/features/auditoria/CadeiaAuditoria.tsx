import { useQuery } from "@tanstack/react-query";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { EventoAuditoria, VerificacaoCadeia } from "../../api/types";
import { Carregando } from "../../components/Carregando";
import { MensagemErro } from "../../components/MensagemErro";
import { Selo } from "../../components/Selo";
import { nomeEvento } from "../../lib/apresentacao";
import { dataHora } from "../../lib/formato";

const LIMITE_EVENTOS = 20;

/** Resumo de uma linha dos detalhes do evento (motivo, intent ou tipo de erro). Nunca a pergunta inteira. */
function resumoDetalhes(detalhes: EventoAuditoria["detalhes"]): string {
  if (!detalhes) return "—";
  for (const campo of ["motivo", "intent", "tipo", "cnpj"]) {
    const valor = detalhes[campo];
    if (typeof valor === "string" && valor) return valor;
  }
  return "—";
}

function SeloCadeia({ v }: { v: VerificacaoCadeia }) {
  if (v.integra) {
    return <Selo tom="verde">Cadeia íntegra · {v.n_eventos} eventos conferidos</Selo>;
  }
  return (
    <Selo tom="vermelho">
      Cadeia alterada a partir do evento {v.primeiro_seq_quebrado ?? "?"} · {v.n_eventos} eventos conferidos
    </Selo>
  );
}

/** Trilha encadeada por hash (GET /auditoria e /auditoria/verificar). Só para auditor e admin. */
export function CadeiaAuditoria() {
  const api = useApi();
  const verificacao = useQuery<VerificacaoCadeia, ErroApi>({
    queryKey: ["auditoria-verificar"],
    queryFn: () => api.auditoria.verificar(),
    staleTime: 0,
    retry: false,
  });
  const eventos = useQuery<EventoAuditoria[], ErroApi>({
    queryKey: ["auditoria-eventos"],
    queryFn: () => api.auditoria.listar(LIMITE_EVENTOS),
    retry: false,
  });

  return (
    <section aria-labelledby="titulo-cadeia" className="cartao p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="titulo-cadeia" className="text-xl font-bold text-kyu-texto">
            Cadeia de auditoria
          </h2>
          <p className="mt-1 text-sm text-kyu-suave">
            Cada evento guarda o hash do anterior. O servidor refaz a conta a cada abertura desta tela. Abaixo, os
            {` ${LIMITE_EVENTOS} `}eventos mais recentes.
          </p>
        </div>
        <p role="status" aria-live="polite">
          {verificacao.isPending ? (
            <Selo tom="neutro">Conferindo a cadeia…</Selo>
          ) : verificacao.isError ? (
            <Selo tom="neutro">Não foi possível conferir a cadeia agora</Selo>
          ) : (
            <SeloCadeia v={verificacao.data} />
          )}
        </p>
      </div>

      {eventos.isPending ? (
        <Carregando texto="Carregando os eventos…" />
      ) : eventos.isError ? (
        <div className="mt-4">
          <MensagemErro erro={eventos.error} titulo="Não foi possível carregar os eventos" />
        </div>
      ) : eventos.data.length === 0 ? (
        <p className="mt-4 text-kyu-suave">Nenhum evento registrado.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[44rem] border-collapse text-left">
            <caption className="sr-only">Eventos da cadeia de auditoria, do mais recente ao mais antigo</caption>
            <thead className="tabela-cabecalho">
              <tr>
                <th scope="col" className="rounded-l-md px-4 py-3">Evento nº</th>
                <th scope="col" className="px-4 py-3">Horário</th>
                <th scope="col" className="px-4 py-3">Tipo</th>
                <th scope="col" className="px-4 py-3">Detalhe</th>
                <th scope="col" className="rounded-r-md px-4 py-3">Hash</th>
              </tr>
            </thead>
            <tbody>
              {eventos.data.map((e) => (
                <tr key={e.seq} className="border-b border-kyu-linha">
                  <th scope="row" className="px-4 py-4 font-bold">{e.seq}</th>
                  <td className="px-4 py-4">{dataHora(e.criado_em)}</td>
                  <td className="px-4 py-4">{nomeEvento(e.evento)}</td>
                  <td className="px-4 py-4 font-mono text-sm">{resumoDetalhes(e.detalhes)}</td>
                  <td className="px-4 py-4 font-mono text-sm" title={e.hash}>
                    {e.hash.slice(0, 12)}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
