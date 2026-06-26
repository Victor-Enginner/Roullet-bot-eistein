import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";

// Pages
import LoginPage from "@/pages/login";
import RegisterPage from "@/pages/register";
import SinaisPage from "@/pages/dashboard/sinais";
import EntradaPage from "@/pages/dashboard/entrada";
import AlertasPage from "@/pages/dashboard/alertas";
import RelatorioPage from "@/pages/dashboard/relatorio";
import SuportePage from "@/pages/dashboard/suporte";
import ConfiguracoesPage from "@/pages/dashboard/configuracoes";
import NotFound from "@/pages/not-found";

// Layouts & Auth
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { DashboardLayout } from "@/components/layout/DashboardLayout";

function Router() {
  return (
    <Switch>
      <Route path="/login" component={LoginPage} />
      <Route path="/register" component={RegisterPage} />
      
      {/* Dashboard Routes wrapped in Layout */}
      <Route path="/">
        <ProtectedRoute>
          <DashboardLayout>
            <SinaisPage />
          </DashboardLayout>
        </ProtectedRoute>
      </Route>
      
      <Route path="/entrada">
        <ProtectedRoute>
          <DashboardLayout>
            <EntradaPage />
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/alertas">
        <ProtectedRoute>
          <DashboardLayout>
            <AlertasPage />
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/relatorio">
        <ProtectedRoute>
          <DashboardLayout>
            <RelatorioPage />
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/suporte">
        <ProtectedRoute>
          <DashboardLayout>
            <SuportePage />
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/configuracoes">
        <ProtectedRoute>
          <DashboardLayout>
            <ConfiguracoesPage />
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      {/* Fallback to 404 */}
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Router />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
