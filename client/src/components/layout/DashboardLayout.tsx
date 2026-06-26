import { useState } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { useHealth, useStartRadar, useStopRadar } from "@/hooks/use-radar";
import { RadarScan } from "@/components/RadarScan";
import { AnalistaVIP } from "@/components/AnalistaVIP";
import {
  Dices, Target, AlertTriangle, BarChart3, Headset,
  Settings, LogOut, ShieldAlert, BadgeDollarSign,
  Menu, Power, PowerOff, Wifi, WifiOff, Activity, Radar
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarProvider,
  SidebarTrigger,
  SidebarHeader,
  SidebarFooter
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { title: "Sinais Ao Vivo", url: "/", icon: Dices },
  { title: "Possível Entrada", url: "/entrada", icon: Target },
  { title: "Alertas", url: "/alertas", icon: AlertTriangle },
  { title: "Relatório", url: "/relatorio", icon: BarChart3 },
  { title: "Suporte", url: "/suporte", icon: Headset },
  { title: "Configurações", url: "/configuracoes", icon: Settings },
];

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { logout, user } = useAuth();
  const { data: health, isLoading: healthLoading } = useHealth();
  const startRadar = useStartRadar();
  const stopRadar = useStopRadar();

  const isOnline = health !== null && health !== undefined;
  const radarActive = health?.radarActive ?? false;

  const handleRadarToggle = () => {
    if (radarActive) {
      stopRadar.mutate();
    } else {
      startRadar.mutate();
    }
  };

  return (
    <SidebarProvider style={{ "--sidebar-width": "18rem" } as React.CSSProperties}>
      <div className="flex min-h-screen w-full bg-background overflow-hidden">

        {/* SIDEBAR */}
        <Sidebar className="border-r border-white/5 bg-black/60 backdrop-blur-xl">
          <SidebarHeader className="p-6 pb-2">
            <div className="flex flex-col items-center text-center gap-2">
              <RadarScan size={88} active={radarActive} />
              <h1 className="text-2xl font-display text-glow-green text-primary tracking-widest mt-1">
                RADAR DO GREEN
              </h1>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/10">
                {isOnline ? (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-primary live-dot"></span>
                    <span className="text-xs font-bold text-primary tracking-widest uppercase">Sistema Online</span>
                  </>
                ) : (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 live-dot"></span>
                    <span className="text-xs font-bold text-yellow-500 tracking-widest uppercase">Modo Simulação</span>
                  </>
                )}
              </div>
            </div>
          </SidebarHeader>

          {/* START RADAR BUTTON */}
          <div className="px-4 py-4">
            <button
              onClick={handleRadarToggle}
              disabled={startRadar.isPending || stopRadar.isPending}
              className={`
                w-full h-12 rounded-xl font-display font-bold text-sm tracking-widest uppercase
                flex items-center justify-center gap-2 transition-all duration-300
                border relative overflow-hidden
                ${radarActive
                  ? 'bg-destructive/15 border-destructive/40 text-destructive hover:bg-destructive/25'
                  : 'bg-primary/15 border-primary/40 text-primary hover:bg-primary/25'}
                ${!radarActive && 'shadow-[0_0_20px_rgba(34,197,94,0.2)]'}
              `}
            >
              {radarActive ? (
                <>
                  <PowerOff className="w-4 h-4" />
                  Parar Radar
                </>
              ) : (
                <>
                  <Power className="w-4 h-4" />
                  Start Radar
                </>
              )}
            </button>
          </div>

          <SidebarContent className="px-4 py-2">
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu className="gap-1.5">
                  {NAV_ITEMS.map((item) => {
                    const isActive = location === item.url;
                    return (
                      <SidebarMenuItem key={item.title}>
                        <SidebarMenuButton
                          asChild
                          isActive={isActive}
                          className={`
                            h-11 text-sm transition-all duration-200 rounded-xl px-4
                            ${isActive
                              ? 'bg-primary/12 text-primary border border-primary/25 hover:bg-primary/18 hover:text-primary'
                              : 'text-zinc-400 hover:bg-white/5 hover:text-white border border-transparent'}
                          `}
                        >
                          <Link href={item.url} className="flex items-center gap-3 w-full">
                            <item.icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-primary' : ''}`} />
                            <span className="font-semibold">{item.title}</span>
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          <SidebarFooter className="p-4 border-t border-white/5">
            <div className="flex items-center justify-between px-2 mb-3">
              <div className="flex flex-col">
                <span className="text-sm font-bold text-white">{user?.name}</span>
                <span className="text-xs text-zinc-500">Membro VIP</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => logout()}
                className="text-zinc-500 hover:text-destructive hover:bg-destructive/10"
                title="Sair"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
            {/* System status indicator */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold ${
              isOnline
                ? 'bg-primary/8 border-primary/20 text-primary'
                : 'bg-yellow-500/8 border-yellow-500/20 text-yellow-500'
            }`}>
              {isOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
              {isOnline ? `v${health?.version} — Conectado` : 'Modo Simulação Ativo'}
            </div>
          </SidebarFooter>
        </Sidebar>

        {/* MAIN CONTENT */}
        <div className="flex-1 flex flex-col relative w-full h-screen overflow-y-auto">

          {/* HEADER */}
          <header className="sticky top-0 z-50 flex items-center justify-between p-4 px-6 bg-background/80 backdrop-blur-xl border-b border-white/5">
            <div className="flex items-center gap-4">
              <SidebarTrigger className="text-zinc-400 hover:text-primary transition-colors">
                <Menu className="w-5 h-5" />
              </SidebarTrigger>
              <div className="hidden sm:flex flex-col">
                <h2 className="text-lg font-display text-white tracking-wider flex items-center gap-2">
                  <Radar className="w-4 h-4 text-primary" />
                  RADAR DO GREEN
                </h2>
                <span className="text-xs text-primary font-bold tracking-widest text-glow-green">
                  SINAIS INTELIGENTES EM TEMPO REAL
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Live Activity */}
              <div className={`hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold ${
                radarActive
                  ? 'bg-primary/10 border-primary/30 text-primary'
                  : 'bg-zinc-900 border-white/10 text-zinc-400'
              }`}>
                <Activity className={`w-3 h-3 ${radarActive ? 'text-primary' : 'text-zinc-600'}`} />
                {radarActive ? 'RADAR ATIVO' : 'STANDBY'}
              </div>

              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-zinc-900 border border-white/8 text-xs font-semibold whitespace-nowrap text-zinc-400">
                <ShieldAlert className="w-3.5 h-3.5 text-yellow-500" />
                <span className="hidden sm:inline">Jogue com responsabilidade</span>
              </div>
              <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-zinc-900 border border-white/8 text-xs font-semibold whitespace-nowrap text-zinc-400">
                <BadgeDollarSign className="w-3.5 h-3.5 text-primary" />
                Saques Ilimitados
              </div>
            </div>
          </header>

          {/* MODE BANNER */}
          {!isOnline && !healthLoading && (
            <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-6 py-2 flex items-center gap-2">
              <WifiOff className="w-4 h-4 text-yellow-500" />
              <span className="text-xs font-bold text-yellow-500 uppercase tracking-widest">
                Modo Simulação — Reconectando automaticamente em 5s...
              </span>
            </div>
          )}

          {/* PAGE CONTENT */}
          <main className="flex-1 p-4 md:p-8 max-w-7xl mx-auto w-full">
            <div className="animate-in fade-in slide-in-from-bottom-3 duration-400 fill-mode-both">
              {children}
            </div>
          </main>

          {/* FOOTER */}
          <footer className="py-4 text-center border-t border-white/5 mt-auto">
            <p className="text-xs font-semibold text-zinc-600 uppercase tracking-widest">
              Powered by <span className="text-primary">RADAR DO GREEN</span> v2.0 — AI Signal Engine
            </p>
          </footer>
        </div>
      </div>

      {/* Floating AI Chat Agent */}
      <AnalistaVIP />
    </SidebarProvider>
  );
}
