import type { ConsultaSaida, ConteudoRecibo, Recibo } from "../../api/types";
import { Selo } from "../../components/Selo";
import { nomeIntent, nomeMotivo } from "../../lib/apresentacao";
import { nomeFonte } from "../../lib/formato";
import { contextoCarteira, nomesFontes } from "../recibo/leitura";

const TEXTO: Record<string, string> = {
  aprovado: "conferido pelo verificador",
  fallback: "resposta padrão do sistema",
  abstencao: "sem registros nas fontes, o sistema não conclui",
  negado: "pedido negado",
};

/** O que aconteceu nesta consulta, lido do recibo dela: nada aqui é uma lista fixa. */
function regrasDoRecibo(c: ConteudoRecibo): string[] {
  const n = c.execucao.n_linhas;
  const motivos = (c.verificacao.motivos ?? []).map(nomeMotivo).join("; ");
  const texto = TEXTO[c.verificacao.status] ?? c.verificacao.status;
  const mostrarMotivos = c.verificacao.status === "fallback" && motivos;
  return [
    `Escopo aplicado pelo banco: ${(c.execucao.ufs_efetivas.length ? c.execucao.ufs_efetivas : c.ufs_autorizadas).join(", ")}`,
    `Consulta do catálogo: ${nomeIntent(c.execucao.consulta_catalogo)} (${c.execucao.consulta_catalogo})`,
    `${n} registro${n === 1 ? "" : "s"} citado${n === 1 ? "" : "s"}`,
    `Plano: ${c.ia.planejador_por_regras ? "regras do sistema, sem IA" : `modelo ${c.ia.modelo ?? c.ia.provedor ?? "de IA"}`}`,
    `Texto: ${texto}${mostrarMotivos ? ` (${motivos})` : ""}`,
    "Registrada na auditoria",
  ];
}

function Regra({ ok, children }: { ok: boolean; children: string }) {
  return (
    <li className="flex gap-2">
      <span aria-hidden="true" className={ok ? "text-kyu-verde" : "text-kyu-suave"}>
        {ok ? "✓" : "–"}
      </span>
      <span>
        <span className="sr-only">{ok ? "Cumprido: " : "Não se aplica: "}</span>
        {children}
      </span>
    </li>
  );
}

/** Cartão "Integridade da consulta" (tela 01): escopo, fonte e regras, lidos do recibo quando existe. */
export function IntegridadeConsulta({ resultado, recibo, ufs }: { resultado: ConsultaSaida; recibo?: Recibo; ufs: string[] }) {
  const escopo = recibo?.conteudo.execucao.ufs_efetivas.length ? recibo.conteudo.execucao.ufs_efetivas : ufs;
  const fontes = recibo
    ? nomesFontes(recibo.conteudo)
    : [...new Set(resultado.citacoes.map((c) => nomeFonte(c.fonte_id)))];
  const negada = resultado.status === "negada";
  const contexto = recibo ? contextoCarteira(recibo.conteudo) : null;

  return (
    <section aria-labelledby={`integridade-${resultado.consulta_id}`} className="cartao p-6">
      <h2 id={`integridade-${resultado.consulta_id}`} className="text-xl font-bold text-kyu-texto">
        Integridade da consulta
      </h2>
      <p className="mt-4">
        <Selo tom={negada ? "vermelho" : "verde"}>Escopo: {escopo.join(", ")}</Selo>
      </p>

      <h3 className="mt-5 text-sm font-semibold text-kyu-suave">{fontes.length > 1 ? "Fontes permitidas" : "Fonte permitida"}</h3>
      <p className="mt-1 text-lg font-bold text-kyu-texto">
        {fontes.length > 0 ? fontes.join(" · ") : negada ? "Nenhuma: a busca foi interrompida" : "Nenhum registro citado"}
      </p>

      {contexto && (
        <>
          <h3 className="mt-5 text-sm font-semibold text-kyu-suave">Contexto</h3>
          <p className="mt-1 text-kyu-texto">{contexto}</p>
        </>
      )}

      <h3 className="mt-5 text-sm font-semibold text-kyu-suave">Regras aplicadas</h3>
      <ul className="mt-2 space-y-2 text-kyu-texto">
        {recibo ? (
          regrasDoRecibo(recibo.conteudo).map((regra) => (
            <Regra key={regra} ok>
              {regra}
            </Regra>
          ))
        ) : (
          // Sem recibo (negação, pedido de detalhe): só o que vale para toda consulta.
          <>
            <Regra ok>Perfil validado antes da busca</Regra>
            <Regra ok={!negada}>{negada ? "Busca bloqueada fora do escopo" : "Escopo aplicado pelo banco de dados"}</Regra>
            <Regra ok={resultado.citacoes.length > 0}>Resposta vinculada a registros</Regra>
            <Regra ok>Consulta registrada para auditoria</Regra>
          </>
        )}
      </ul>

      <p className="mt-5 text-sm text-kyu-suave">Sem evidência suficiente, a IA não conclui.</p>
    </section>
  );
}
