import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { pode } from "../auth/permissoes";
import { NOME_PERFIL, nomesUfs } from "../lib/apresentacao";
import { LogoKyu } from "./LogoKyu";

interface ItemMenu {
  rotulo: string;
  para: string;
  ativoEm?: RegExp;
}

function classeItem(ativo: boolean): string {
  return `foco block rounded-lg px-4 py-3 text-base ${
    ativo ? "bg-white font-semibold text-kyu-escuro" : "text-white/90 hover:bg-white/10"
  }`;
}

/** Moldura das telas autenticadas: lateral escura com a marca e o menu, barra do topo com escopo e perfil. */
export function Moldura({ children }: { children: ReactNode }) {
  const { usuario, sair } = useAuth();
  const local = useLocation();
  if (!usuario) return null;

  const itens: ItemMenu[] = [
    // O recibo é aberto a partir da consulta: o menu continua marcando "Consulta" (tela 02 do design).
    { rotulo: "Consulta", para: "/", ativoEm: /^\/(recibos\/.*)?$/ },
    { rotulo: "Fontes e catálogo", para: "/fontes" },
    { rotulo: "Acesso", para: "/acesso" },
    ...(pode(usuario.perfil, "ver_historico") ? [{ rotulo: "Auditoria", para: "/auditoria" }] : []),
  ];

  return (
    <div className="min-h-screen lg:flex">
      <aside className="flex flex-col bg-kyu-escuro px-3 pb-4 pt-5 text-white lg:sticky lg:top-0 lg:h-screen lg:w-60 lg:shrink-0">
        <div className="px-3">
          <LogoKyu />
          <p className="mt-3 text-xs font-bold uppercase tracking-wide text-white/90">Portal de transparência</p>
        </div>
        <nav aria-label="Principal" className="mt-6">
          <ul className="flex flex-wrap gap-1 lg:flex-col">
            {itens.map((item) => {
              const ativo = item.ativoEm ? item.ativoEm.test(local.pathname) : local.pathname.startsWith(item.para);
              return (
                <li key={item.para}>
                  <Link to={item.para} className={classeItem(ativo)} aria-current={ativo ? "page" : undefined}>
                    {item.rotulo}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="mt-6 border-t border-white/15 px-3 pt-4 text-sm lg:mt-auto">
          <p className="font-semibold">{usuario.nome}</p>
          <p className="text-white/80">
            {NOME_PERFIL[usuario.perfil]} · {usuario.tenant.nome}
          </p>
          <button
            type="button"
            onClick={sair}
            className="foco mt-3 rounded-md border border-white/40 px-3 py-1.5 text-white hover:bg-white/10"
          >
            Sair
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-kyu-borda bg-white px-6 py-3">
          <p className="font-semibold text-kyu-texto">
            <span aria-label={`Estados autorizados: ${usuario.ufs.join(", ")}`}>{nomesUfs(usuario.ufs)}</span>
            {" · "}
            {NOME_PERFIL[usuario.perfil]}
          </p>
        </header>
        <main id="conteudo" tabIndex={-1} className="flex-1 px-4 py-8 sm:px-7">
          <div className="max-w-[80rem]">{children}</div>
        </main>
      </div>
    </div>
  );
}
