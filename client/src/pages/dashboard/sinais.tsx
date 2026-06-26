import { useSignals } from "@/hooks/use-signals";
import { useMetrics } from "@/hooks/use-metrics";
import { ProfitCounter } from "@/components/ProfitCounter";
import { RadarScan } from "@/components/RadarScan";
import { useHealth } from "@/hooks/use-radar";
import { Card, CardContent } from "@/components/ui/card";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Radar, CheckCircle2, XCircle, Clock, TrendingUp, Target, Zap, Activity } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 85 ? 'bg-primary' : value >= 70 ? 'bg-yellow-500' : 'bg-destructive';
  return (
    <div className="w-full bg-white/5 rounded-full h-1.5 mt-2 overflow-hidden">
      <div
        className={`h-full rounded-full confidence-fill ${color}`}
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

export default function SinaisPage() {
  const { data: signals, isLoading } = useSignals();
  const { data: metrics } = useMetrics();

  const { data: health } = useHealth();
  const winRate = metrics?.winRate ?? 0;
  const streak = metrics?.currentStreak ?? 0;
  const signalsToday = metrics?.signalsToday ?? 0;
  const radarActive = health?.radarActive ?? false;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-display text-white tracking-wide flex items-center gap-3">
            <Radar className="w-8 h-8 text-primary" />
            SINAIS AO VIVO
          </h1>
          <p className="text-zinc-500 text-sm font-medium">Resultados processados pelo algoritmo RADAR DO GREEN</p>
        </div>
        <div className="flex items-center gap-3">
          <RadarScan size={52} active={radarActive} />
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/8 border border-primary/20 text-primary">
            <span className="w-2 h-2 rounded-full bg-primary live-dot"></span>
            <span className="text-sm font-bold tracking-widest">LIVE</span>
          </div>
        </div>
      </div>

      {/* Profit Counter */}
      <ProfitCounter />

      {/* Quick Metrics Strip */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-panel rounded-xl p-4 flex flex-col gap-1">
          <div className="flex items-center gap-2 text-zinc-500 text-xs font-bold uppercase tracking-wider">
            <Activity className="w-3.5 h-3.5" />
            Sinais Hoje
          </div>
          <span className="text-2xl font-display text-white">{signalsToday}</span>
        </div>
        <div className="glass-panel rounded-xl p-4 flex flex-col gap-1">
          <div className="flex items-center gap-2 text-zinc-500 text-xs font-bold uppercase tracking-wider">
            <Target className="w-3.5 h-3.5" />
            Win Rate
          </div>
          <span className={`text-2xl font-display ${winRate >= 60 ? 'text-primary' : 'text-destructive'}`}>
            {winRate}%
          </span>
        </div>
        <div className="glass-panel rounded-xl p-4 flex flex-col gap-1">
          <div className="flex items-center gap-2 text-zinc-500 text-xs font-bold uppercase tracking-wider">
            <Zap className="w-3.5 h-3.5" />
            Sequência
          </div>
          <span className={`text-2xl font-display ${streak > 0 ? 'text-primary' : 'text-zinc-400'}`}>
            {streak > 0 ? `+${streak}` : streak} greens
          </span>
        </div>
      </div>

      {/* Signal Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-44 rounded-xl bg-white/4" />
          ))}
        </div>
      ) : signals?.length === 0 ? (
        <div className="glass-panel rounded-xl py-20 text-center">
          <Radar className="w-14 h-14 text-zinc-700 mx-auto mb-4" />
          <h3 className="text-xl font-display text-white mb-2">Aguardando Sinais</h3>
          <p className="text-zinc-500 text-sm">Ative o RADAR para começar a receber sinais.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {signals?.map((signal) => (
            <div
              key={signal.id}
              className={`glass-panel rounded-xl overflow-hidden transition-all duration-300 hover:-translate-y-0.5 relative
                ${signal.status === 'green' ? 'signal-glow-green' : 'signal-glow-red'}
              `}
            >
              {/* Top accent bar */}
              <div className={`h-0.5 w-full ${signal.status === 'green' ? 'bg-gradient-to-r from-primary/0 via-primary to-primary/0' : 'bg-gradient-to-r from-destructive/0 via-destructive to-destructive/0'}`} />

              <div className="p-5">
                {/* Header row */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-1.5 text-zinc-500 text-xs font-medium">
                    <Clock className="w-3.5 h-3.5" />
                    {format(new Date(signal.timestamp), "HH:mm:ss", { locale: ptBR })}
                  </div>
                  {signal.status === 'green' ? (
                    <div className="flex items-center gap-1 px-2.5 py-1 bg-primary/15 text-primary border border-primary/30 rounded-full text-xs font-bold">
                      <CheckCircle2 className="w-3 h-3" />
                      GREEN
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 px-2.5 py-1 bg-destructive/15 text-destructive border border-destructive/30 rounded-full text-xs font-bold">
                      <XCircle className="w-3 h-3" />
                      RED
                    </div>
                  )}
                </div>

                {/* Number display */}
                <div className="flex items-center justify-center my-3">
                  <div className={`
                    w-16 h-16 rounded-full flex items-center justify-center border-2 font-display font-bold text-3xl
                    ${[1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(signal.number)
                      ? 'bg-destructive/15 border-destructive/50 text-destructive'
                      : signal.number === 0
                      ? 'bg-primary/15 border-primary/50 text-primary'
                      : 'bg-zinc-800 border-zinc-600 text-white'}
                  `}>
                    {signal.number}
                  </div>
                </div>

                {/* Confidence */}
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-zinc-500 font-medium">Confiança</span>
                    <span className={`font-bold ${signal.confidence >= 85 ? 'text-primary' : signal.confidence >= 70 ? 'text-yellow-500' : 'text-destructive'}`}>
                      {signal.confidence}%
                    </span>
                  </div>
                  <ConfidenceBar value={signal.confidence} />
                </div>

                {/* Entry type */}
                {signal.entry && (
                  <p className="text-xs text-zinc-600 mt-2 font-medium truncate">{signal.entry}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
