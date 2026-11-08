import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useApi } from "../api/ApiProvider";
import type { ErroApi } from "../api/http";
import type { ConsultaListada, StatusConsulta } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { pode } from "../auth/permissoes";
import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { Indicador } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import { CadeiaAuditoria } from "../features/auditoria/CadeiaAuditoria";
import { NOME_PERFIL, STATUS_CONSULTA, nomeIntent } from "../lib/apresentacao";
import { hora } from "../lib/formato";

type Filtro = "todas" | "respondidas" | "bloqueadas" | "sem_dados";

const FILTROS: { id: Filtro; rotulo: string; status: StatusConsulta[] | null; classe: string }[] = [
  { id: "todas", rotulo: "Todas", status: null, classe: "bg-kyu-verde-fundo text-kyu-verde" },
  { id: "respondidas", rotulo: "Respondidas", status: ["respondida"], classe: "bg-kyu-verde-fundo text-kyu-verde" },
  { id: "bloqueadas", rotulo: "Bloqueadas", status: ["negada", "erro"], classe: "bg-kyu-vermelho-fundo text-kyu-vermelho" },
  { id: "sem_dados", rotulo: "Sem registros", status: ["abstencao", "esclarecimento"], classe: "bg-kyu-ambar-fundo text-kyu-ambar" },
];

const DETALHE: Record<StatusConsulta, string> = {
  respondida: "Ver recibo",
  abstencao: "Sem registros",
  esclarecimento: "Pediu um detalhe",
  negada: "Permissão negada",
  erro: "Erro registrado",
};

function Linha({ c, meuId, meuPerfil, minhasUfs }: { c: ConsultaListada; meuId: string; meuPerfil: string; minhasUfs: string }) {
  const s = STATUS_CONSULTA[c.status] ?? STATUS_CONSULTA.erro;
  return (
    <tr className="border-b border-kyu-linha align-top">
      <th scope="row" className="px-4 py-5 font-mono text-sm font-bold" title={c.id}>
        {c.id.slice(0, 8)}
      </th>
      <td className="px-4 py-5">{hora(c.criada_em)}</td>
      <td className="px-4 py-5">
        <span className="block">{nomeIntent(c.intent)}</span>
        <span className="block max-w-md truncate text-sm text-kyu-suave" title={c.pergunta}>
          {c.pergunta}
        </span>
      </td>
      <td className="px-4 py-5">{c.usuario_id === meuId ? `${meuPerfil} ${minhasUfs}` : "Outro usuário do cliente"}</td>
      <td className="px-4 py-5">
        <Indicador tom={s.tom}>{s.resultado}</Indicador>
      </td>
      <td className="px-4 py-5 font-semibold">
        {c.recibo_id ? (
          <Link to={`/recibos/${c.recibo_id}`} className="foco text-kyu-laranja underline">
            Ver recibo
          </Link>
        ) : (
          <span className="text-kyu-laranja">{DETALHE[c.status]}</span>
        )}
      </td>
    </tr>
  );
}

/** Tela 04 do design: auditoria de consultas (GET /consultas; o que aparece é decidido pela RLS). */
export function AuditoriaPage() {
  const { usuario } = useAuth();
  const api = useApi();
  const permitido = pode(usuario?.perfil, "ver_historico");
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const consultas = useQuery<ConsultaListada[], ErroApi>({
    queryKey: ["consultas", usuario?.id],
    queryFn: () => api.consultas.listar(50),
    enabled: permitido,
  });
  if (!usuario) return null;

  const escolhido = FILTROS.find((f) => f.id === filtro)!;
  const linhas = (consultas.data ?? []).filter((c) => !escolhido.status || escolhido.status.includes(c.status));
  const veTenant = pode(usuario.perfil, "ver_auditoria");

  return (
    <div className="space-y-6">
      <TituloPagina numero="04" titulo="Auditoria de consultas">
        Histórico de perguntas, validações de acesso, fontes recuperadas e decisões do sistema.
      </TituloPagina>

      {!permitido ? (
        <p role="note" className="cartao p-5">
          Seu perfil ({NOME_PERFIL[usuario.perfil]}) não acompanha o histórico de consultas.
        </p>
      ) : (
        <>
          <div role="group" aria-label="Filtrar por resultado" className="flex flex-wrap gap-3">
            {FILTROS.map((f) => (
              <button
                key={f.id}
                type="button"
                aria-pressed={filtro === f.id}
                onClick={() => setFiltro(f.id)}
                className={`foco rounded-md px-3 py-1.5 text-sm font-semibold ${f.classe} ${
                  filtro === f.id ? "ring-2 ring-current" : ""
                }`}
              >
                {f.rotulo}
              </button>
            ))}
          </div>

          <section aria-labelledby="titulo-eventos" className="cartao p-6">
            <h2 id="titulo-eventos" className="text-xl font-bold text-kyu-texto">
              Eventos registrados
            </h2>
            <p className="mt-1 text-sm text-kyu-suave">
              {veTenant ? "Consultas de todo o cliente" : "Suas consultas"} ({usuario.tenant.nome}), mais recentes
              primeiro.
            </p>
            {consultas.isPending ? (
              <Carregando texto="Carregando o histórico…" />
            ) : consultas.isError ? (
              <div className="mt-4">
                <MensagemErro erro={consultas.error} titulo="Não foi possível carregar o histórico" />
              </div>
            ) : linhas.length === 0 ? (
              <p className="mt-4 text-kyu-suave">Nenhuma consulta com esse resultado.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[48rem] border-collapse text-left">
                  <caption className="sr-only">Consultas registradas, com horário, ação, perfil, resultado e detalhes</caption>
                  <thead className="tabela-cabecalho">
                    <tr>
                      <th scope="col" className="rounded-l-md px-4 py-3">ID</th>
                      <th scope="col" className="px-4 py-3">Horário</th>
                      <th scope="col" className="px-4 py-3">Ação</th>
                      <th scope="col" className="px-4 py-3">Perfil</th>
                      <th scope="col" className="px-4 py-3">Resultado</th>
                      <th scope="col" className="rounded-r-md px-4 py-3">Detalhes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {linhas.map((c) => (
                      <Linha key={c.id} c={c} meuId={usuario.id} meuPerfil={NOME_PERFIL[usuario.perfil]}
                        minhasUfs={usuario.ufs.join(", ")} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="mt-6 text-sm text-kyu-suave">
              Ao abrir o recibo: pergunta, perfil, escopo, horário, decisão, identificadores das fontes e resposta.
            </p>
          </section>
        </>
      )}

      {veTenant && <CadeiaAuditoria />}

      <p className="cartao p-5 text-kyu-texto">
        O histórico não guarda senhas nem tokens. Cada consulta respondida tem um recibo com selo sha256.
      </p>
    </div>
  );
}
