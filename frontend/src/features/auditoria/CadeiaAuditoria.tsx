import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { CabecaCadeia, EventoAuditoria, VerificacaoCadeia } from "../../api/types";
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

/**
 * Último evento da trilha (GET /auditoria/cabeca). Publicado fora do banco (ata, e-mail, repositório), torna
 * detectável reescrever a trilha inteira ou cortar o fim dela: o hash publicado deixa de estar no evento dele.
 */
export function CabecaDaCadeia() {
  const api = useApi();
  const cabeca = useQuery<CabecaCadeia, ErroApi>({
    queryKey: ["auditoria-cabeca"],
    queryFn: () => api.auditoria.cabeca(),
    staleTime: 0,
    retry: false,
  });
  const [copiado, setCopiado] = useState<"sim" | "falhou" | null>(null);

  async function copiar(hash: string) {
    try {
      await navigator.clipboard.writeText(hash);
      setCopiado("sim");
    } catch {
      setCopiado("falhou");
    }
  }

  return (
    <section aria-labelledby="titulo-cabeca" className="cartao p-6">
      <h2 id="titulo-cabeca" className="text-xl font-bold text-kyu-texto">
        Cabeça da cadeia
      </h2>
      <p className="mt-1 text-sm text-kyu-suave">
        Publique este hash fora do Lastro (ata, e-mail, repositório). Se alguém reescrever a trilha inteira ou apagar
        o fim dela, o evento deste número deixa de ter este hash.
      </p>
      {cabeca.isPending ? (
        <Carregando texto="Lendo a cabeça da cadeia…" />
      ) : cabeca.isError ? (
        <div className="mt-4">
          <MensagemErro erro={cabeca.error} titulo="Não foi possível ler a cabeça da cadeia" />
        </div>
      ) : cabeca.data.hash === null ? (
        <p className="mt-4 text-kyu-suave">A trilha ainda não tem eventos.</p>
      ) : (
        <div className="mt-4 space-y-3">
          <p>
            <strong>Evento nº {cabeca.data.seq}</strong>
            {cabeca.data.criado_em && <> · {dataHora(cabeca.data.criado_em)}</>} · {cabeca.data.n_eventos} eventos
            na trilha
          </p>
          <p className="break-all rounded-md bg-kyu-cabecalho px-3 py-2 font-mono text-sm">{cabeca.data.hash}</p>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              aria-label="Copiar o hash da cabeça"
              className="botao-secundario"
              onClick={() => void copiar(cabeca.data.hash!)}
            >
              Copiar hash
            </button>
            <span role="status" aria-live="polite" className="text-sm text-kyu-suave">
              {copiado === "sim" ? "Hash copiado." : copiado === "falhou" ? "Não deu para copiar: selecione o texto." : ""}
            </span>
          </div>
        </div>
      )}
    </section>
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
