import { useAlerts } from "@/hooks/use-alerts";
import { Card, CardContent } from "@/components/ui/card";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { AlertTriangle, TrendingUp, ShieldAlert, Clock, Radio } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function AlertasPage() {
  const { data: alerts, isLoading } = useAlerts();

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-display text-white tracking-wide flex items-center gap-3">
          <AlertTriangle className="w-8 h-8 text-yellow-500" />
          ALERTAS DO SISTEMA
        </h1>
        <p className="text-zinc-500 text-sm font-medium">Inteligência artificial monitorando anomalias na mesa em tempo real</p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl bg-white/4" />
          ))}
        </div>
      ) : alerts?.length === 0 ? (
        <div className="glass-panel rounded-xl py-20 text-center">
          <ShieldAlert className="w-14 h-14 text-zinc-700 mx-auto mb-4" />
          <h3 className="text-xl font-display text-white mb-2">Mesa Estável</h3>
          <p className="text-zinc-500 text-sm">Nenhuma anomalia detectada. O RADAR está monitorando continuamente.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts?.map((alert) => (
            <div
              key={alert.id}
              className={`
                glass-panel rounded-xl overflow-hidden transition-all duration-300
                ${alert.type === 'manipulacao'
                  ? 'border-destructive/20 bg-destructive/4 hover:border-destructive/30'
                  : 'border-yellow-500/20 bg-yellow-500/4 hover:border-yellow-500/30'}
              `}
            >
              {/* Top accent bar */}
              <div className={`h-0.5 w-full ${alert.type === 'manipulacao' ? 'bg-gradient-to-r from-destructive/0 via-destructive to-destructive/0' : 'bg-gradient-to-r from-yellow-500/0 via-yellow-500 to-yellow-500/0'}`} />

              <div className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className={`p-2.5 rounded-lg flex-shrink-0 ${
                    alert.type === 'manipulacao' ? 'bg-destructive/15 text-destructive' : 'bg-yellow-500/15 text-yellow-500'
                  }`}>
                    {alert.type === 'manipulacao'
                      ? <ShieldAlert className="w-5 h-5" />
                      : <TrendingUp className="w-5 h-5" />
                    }
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Radio className="w-3 h-3 text-zinc-600" />
                      <span className={`text-xs font-bold uppercase tracking-widest ${
                        alert.type === 'manipulacao' ? 'text-destructive' : 'text-yellow-500'
                      }`}>
                        {alert.type === 'manipulacao' ? 'RISCO DE MANIPULACAO' : 'SEQUENCIA INCOMUM'}
                      </span>
                    </div>
                    <p className="text-white font-semibold text-sm">{alert.message}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-zinc-500 text-xs font-medium px-3 py-2 rounded-lg bg-black/30 border border-white/5 self-start md:self-center flex-shrink-0">
                  <Clock className="w-3.5 h-3.5" />
                  {format(new Date(alert.timestamp), "dd/MM • HH:mm:ss", { locale: ptBR })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
