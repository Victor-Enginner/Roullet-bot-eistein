import { useMetrics } from "@/hooks/use-metrics";
import { useReport } from "@/hooks/use-reports";
import { Card, CardContent } from "@/components/ui/card";
import { BarChart3, CheckCircle2, XCircle, RotateCcw, Target, Zap, TrendingUp, Award } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

function StatCard({
  icon: Icon,
  label,
  value,
  color = "text-white",
  iconBg = "bg-zinc-800",
  iconColor = "text-zinc-400",
  glow = false,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color?: string;
  iconBg?: string;
  iconColor?: string;
  glow?: boolean;
}) {
  return (
    <div className={`glass-panel rounded-xl p-5 flex items-center gap-4 transition-all duration-300 hover:-translate-y-0.5 ${glow ? 'signal-glow-green' : ''}`}>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${iconBg}`}>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>
      <div>
        <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-0.5">{label}</p>
        <p className={`text-2xl font-display ${color}`}>{value}</p>
      </div>
    </div>
  );
}

export default function RelatorioPage() {
  const { data: metrics, isLoading } = useMetrics();
  const { data: report } = useReport();

  const winRate = metrics?.winRate ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-display text-white tracking-wide flex items-center gap-3">
          <BarChart3 className="w-8 h-8 text-primary" />
          RELATÓRIO CONSOLIDADO
        </h1>
        <p className="text-zinc-500 text-sm font-medium">Estatísticas de performance do RADAR DO GREEN</p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl bg-white/4" />
          ))}
        </div>
      ) : (
        <>
          {/* Main Stats Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={RotateCcw}
              label="Total Giros"
              value={report?.totalSpins ?? 0}
              color="text-white"
              iconBg="bg-blue-500/15"
              iconColor="text-blue-400"
            />
            <StatCard
              icon={CheckCircle2}
              label="Total Greens"
              value={metrics?.totalGreens ?? 0}
              color="text-primary text-glow-green"
              iconBg="bg-primary/15"
              iconColor="text-primary"
              glow
            />
            <StatCard
              icon={XCircle}
              label="Total Reds"
              value={metrics?.totalReds ?? 0}
              color="text-destructive"
              iconBg="bg-destructive/15"
              iconColor="text-destructive"
            />
            <StatCard
              icon={Target}
              label="Assertividade"
              value={`${winRate}%`}
              color={winRate >= 60 ? "text-yellow-500 text-glow-gold" : "text-destructive"}
              iconBg="bg-yellow-500/15"
              iconColor="text-yellow-500"
            />
          </div>

          {/* Metrics from report */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={Zap}
              label="Sinais Hoje"
              value={metrics?.signalsToday ?? 0}
              color="text-primary"
              iconBg="bg-primary/10"
              iconColor="text-primary"
            />
            <StatCard
              icon={Award}
              label="Streak Atual"
              value={`+${metrics?.currentStreak ?? 0}`}
              color={(metrics?.currentStreak ?? 0) > 0 ? "text-primary" : "text-zinc-400"}
              iconBg={(metrics?.currentStreak ?? 0) > 0 ? "bg-primary/10" : "bg-zinc-800"}
              iconColor={(metrics?.currentStreak ?? 0) > 0 ? "text-primary" : "text-zinc-500"}
            />
            <StatCard
              icon={TrendingUp}
              label="Último Resultado"
              value={metrics?.lastSignalResult === 'win' ? 'WIN' : metrics?.lastSignalResult === 'loss' ? 'LOSS' : '—'}
              color={metrics?.lastSignalResult === 'win' ? 'text-primary' : metrics?.lastSignalResult === 'loss' ? 'text-destructive' : 'text-zinc-500'}
              iconBg={metrics?.lastSignalResult === 'win' ? 'bg-primary/10' : 'bg-destructive/10'}
              iconColor={metrics?.lastSignalResult === 'win' ? 'text-primary' : 'text-destructive'}
            />
            <StatCard
              icon={BarChart3}
              label="Último Número"
              value={metrics?.lastNumber ?? 0}
              color="text-white"
              iconBg="bg-zinc-800"
              iconColor="text-zinc-400"
            />
          </div>

          {/* Win Rate Visual */}
          <div className="glass-panel rounded-xl p-6 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-transparent" />
            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="flex-1">
                <h3 className="text-xl font-display text-white mb-1">TAXA DE ASSERTIVIDADE</h3>
                <p className="text-zinc-500 text-sm mb-6">Performance acumulada do algoritmo.</p>
                <div className="w-full bg-white/5 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full rounded-full confidence-fill ${winRate >= 60 ? 'bg-gradient-to-r from-primary to-primary/60' : 'bg-destructive'}`}
                    style={{ width: `${winRate}%` }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs font-bold text-zinc-600">
                  <span>0%</span>
                  <span className={winRate >= 60 ? 'text-primary' : 'text-destructive'}>{winRate}%</span>
                  <span>100%</span>
                </div>
              </div>
              <div className="w-28 h-28 rounded-full border-4 border-zinc-700 bg-zinc-900 flex items-center justify-center shadow-2xl flex-shrink-0">
                <div className="text-center">
                  <span className="text-4xl font-display font-bold text-white">{metrics?.lastNumber ?? '—'}</span>
                  <div className="text-xs text-zinc-600 font-bold mt-0.5">ÚLTIMO</div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
