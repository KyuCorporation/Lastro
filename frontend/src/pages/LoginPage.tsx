import { useId, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { LogoKyu } from "../components/LogoKyu";
import { MensagemErro } from "../components/MensagemErro";
import { ambiente } from "../config/ambiente";
import { SENHA_SEED_DEMO, USUARIOS_DEMO } from "../config/demo";

interface EstadoNavegacao {
  de?: string;
  motivo?: "expirou" | "saiu";
}

const CLASSE_CAMPO = "foco mt-1 w-full rounded-md border border-kyu-suave bg-white p-2.5 text-kyu-texto";

export function LoginPage({ demo = ambiente.demo }: { demo?: boolean }) {
  const { estado, entrar } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();
  const destino = (local.state as EstadoNavegacao | null)?.de ?? "/";
  const motivo = (local.state as EstadoNavegacao | null)?.motivo;
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);
  const idEmail = useId();
  const idSenha = useId();

  if (estado.status === "autenticado") return <Navigate to={destino} replace />;

  async function autenticar(credenciais: { email: string; senha: string }) {
    setEnviando(true);
    setErro(null);
    try {
      await entrar(credenciais);
      navegar(destino, { replace: true });
    } catch (e) {
      setErro(e);
    } finally {
      setEnviando(false);
    }
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    void autenticar({ email: email.trim(), senha });
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
      <div className="flex flex-col justify-between bg-kyu-escuro px-8 py-8 text-white lg:py-12">
        <div>
          <LogoKyu />
          <p className="mt-3 text-xs font-bold uppercase tracking-wide text-white/90">Portal de transparência</p>
        </div>
        <p className="mt-8 max-w-sm text-lg text-white/90">
          Contratos, pagamentos e sanções de fornecedores, com a fonte oficial de cada número e o acesso decidido pelo
          banco de dados.
        </p>
      </div>
    <main className="mx-auto w-full max-w-md px-4 py-10 lg:py-16">
      <h1 className="text-3xl font-bold text-kyu-texto">Entrar no KYU</h1>
      <p className="mt-1 text-kyu-suave">Radar de risco de fornecedores, com recibo.</p>

      {motivo === "expirou" && (
        <p role="status" className="mt-4 rounded-md border border-kyu-borda bg-white p-3 text-kyu-texto">
          Sua sessão expirou. Entre novamente.
        </p>
      )}

      <form onSubmit={enviar} className="cartao mt-6 space-y-4 p-6" aria-busy={enviando}>
        <div>
          <label htmlFor={idEmail} className="block font-semibold text-kyu-texto">
            E-mail
          </label>
          <input
            id={idEmail}
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={CLASSE_CAMPO}
          />
        </div>
        <div>
          <label htmlFor={idSenha} className="block font-semibold text-kyu-texto">
            Senha
          </label>
          <input
            id={idSenha}
            type="password"
            autoComplete="current-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className={CLASSE_CAMPO}
          />
        </div>
        {erro !== null && <MensagemErro erro={erro} titulo="Não foi possível entrar" />}
        <button
          type="submit"
          disabled={enviando}
          className="botao-primario w-full py-2.5"
        >
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>

      {demo && (
        <section aria-labelledby="titulo-demo" className="mt-8 rounded-xl border-2 border-dashed border-kyu-ambar bg-kyu-ambar-fundo/40 p-4">
          <h2 id="titulo-demo" className="font-semibold text-kyu-texto">
            Usuários de demonstração
          </h2>
          <p className="text-sm text-kyu-suave">Modo demo: entra com o usuário do seed de desenvolvimento.</p>
          <ul className="mt-3 space-y-2">
            {USUARIOS_DEMO.map((u) => (
              <li key={u.email}>
                <button
                  type="button"
                  disabled={enviando}
                  onClick={() => void autenticar({ email: u.email, senha: SENHA_SEED_DEMO })}
                  className="foco w-full rounded-md border border-kyu-borda bg-white px-3 py-2 text-left text-sm text-kyu-texto hover:border-kyu-laranja"
                >
                  <strong>{u.nome}</strong> · {u.perfil} · {u.tenant} · UFs {u.ufs.join(", ")}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
    </div>
  );
}
