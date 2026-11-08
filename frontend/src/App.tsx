import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { RotaProtegida } from "./auth/RotaProtegida";
import { Moldura } from "./components/Moldura";
import { AcessoPage } from "./pages/AcessoPage";
import { AuditoriaPage } from "./pages/AuditoriaPage";
import { CarteirasPage } from "./pages/CarteirasPage";
import { ConsultaPage } from "./pages/ConsultaPage";
import { DossiePage } from "./pages/DossiePage";
import { FilaPage } from "./pages/FilaPage";
import { FontesPage } from "./pages/FontesPage";
import { LoginPage } from "./pages/LoginPage";
import { ReciboPage } from "./pages/ReciboPage";

function Layout() {
  return (
    <RotaProtegida>
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-10 focus:rounded focus:bg-white focus:p-2"
      >
        Pular para o conteúdo
      </a>
      <Moldura>
        <Outlet />
      </Moldura>
    </RotaProtegida>
  );
}

/** Rotas das telas do design (01 a 05) e do N2 (06 carteiras e fila, 07 dossiê). Tela nova = uma <Route> dentro do Layout e uma página em pages/. */
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route index element={<ConsultaPage />} />
        <Route path="/recibos/:id" element={<ReciboPage />} />
        <Route path="/carteiras" element={<CarteirasPage />} />
        <Route path="/carteiras/:id" element={<FilaPage />} />
        <Route path="/fornecedores/:cnpj" element={<DossiePage />} />
        <Route path="/acesso" element={<AcessoPage />} />
        <Route path="/auditoria" element={<AuditoriaPage />} />
        <Route path="/fontes" element={<FontesPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
