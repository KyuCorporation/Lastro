import type { ConsultaSaida, Recibo } from "../../api/types";
import { Selo } from "../../components/Selo";
import { nomeFonte } from "../../lib/formato";
import { nomesFontes } from "../recibo/leitura";

const VERIFICACAO: Record<string, string> = {
  aprovado: "Texto conferido pelo verificador",
  fallback: "Resposta padrão do sistema, com os valores do banco",
  abstencao: "Sem registros nas fontes: o sistema não conclui",
  negado: "Pedido negado",
};

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

      <h3 className="mt-5 text-sm font-semibold text-kyu-suave">Regras aplicadas</h3>
      <ul className="mt-2 space-y-2 text-kyu-texto">
        <Regra ok>Perfil validado antes da busca</Regra>
        <Regra ok={!negada}>{negada ? "Busca bloqueada fora do escopo" : "Escopo aplicado pelo banco de dados"}</Regra>
        <Regra ok={resultado.citacoes.length > 0}>Resposta vinculada a registros</Regra>
        <Regra ok>Consulta registrada para auditoria</Regra>
      </ul>
      {recibo && (
        <p className="mt-4 text-sm text-kyu-texto">
          <span className="font-semibold">Verificação:</span>{" "}
          {VERIFICACAO[recibo.conteudo.verificacao.status] ?? recibo.conteudo.verificacao.status}
        </p>
      )}

      <p className="mt-5 text-sm text-kyu-suave">Sem evidência suficiente, a IA não conclui.</p>
    </section>
  );
}
