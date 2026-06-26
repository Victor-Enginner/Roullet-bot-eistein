import { useState, useEffect, useRef } from "react";
import { TrendingUp, DollarSign, Zap } from "lucide-react";
import { useMetrics } from "@/hooks/use-metrics";

function useAnimatedNumber(target: number, duration = 800) {
  const [current, setCurrent] = useState(target);
  const prev = useRef(target);

  useEffect(() => {
    if (prev.current === target) return;
    const start = prev.current;
    const diff = target - start;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(start + diff * eased));
      if (progress < 1) requestAnimationFrame(tick);
      else prev.current = target;
    };

    requestAnimationFrame(tick);
  }, [target, duration]);

  return current;
}

export function ProfitCounter() {
  const { data: metrics } = useMetrics();
  const [flash, setFlash] = useState(false);
  const prevGreens = useRef(0);

  const greens = metrics?.totalGreens ?? 0;
  const reds = metrics?.totalReds ?? 0;
  const winRate = metrics?.winRate ?? 0;

  // Estimated profit: each green = +R$12, each red = -R$8 (gale simulation)
  const estimatedProfit = greens * 12 - reds * 8;
  const animatedProfit = useAnimatedNumber(estimatedProfit);
  const animatedGreens = useAnimatedNumber(greens);

  useEffect(() => {
    if (metrics && metrics.totalGreens > prevGreens.current) {
      setFlash(true);
      setTimeout(() => setFlash(false), 2000);
      prevGreens.current = metrics.totalGreens;
    }
  }, [metrics?.totalGreens]);

  const isPositive = estimatedProfit >= 0;

  return (
    <div
      className={`
        relative rounded-xl overflow-hidden border transition-all duration-700 p-4
        ${flash
          ? "border-yellow-500/60 bg-yellow-500/10 shadow-[0_0_40px_rgba(234,179,8,0.4)]"
          : "border-white/8 bg-black/40 backdrop-blur-md"
        }
      `}
    >
      {/* Flash overlay */}
      {flash && (
        <div className="absolute inset-0 bg-gradient-to-r from-yellow-500/10 via-yellow-300/20 to-yellow-500/10 animate-pulse rounded-xl pointer-events-none" />
      )}

      <div className="relative z-10 flex items-center justify-between gap-4">
        {/* Profit value */}
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg transition-all duration-700 ${flash ? "bg-yellow-500/20" : "bg-white/5"}`}>
            <DollarSign className={`w-5 h-5 transition-colors duration-700 ${flash ? "text-yellow-400" : "text-zinc-400"}`} />
          </div>
          <div>
            <p className="text-xs font-bold text-zinc-600 uppercase tracking-wider">Lucro Estimado</p>
            <p className={`text-xl font-display transition-all duration-700 ${
              flash ? "text-yellow-400 text-glow-gold" : isPositive ? "text-primary" : "text-destructive"
            }`}>
              {isPositive ? "+" : ""}R${animatedProfit.toLocaleString("pt-BR")}
            </p>
          </div>
        </div>

        {/* Green count */}
        <div className="flex items-center gap-2 text-right">
          <div>
            <p className="text-xs font-bold text-zinc-600 uppercase tracking-widest">Greens</p>
            <p className={`text-xl font-display text-primary tabular-nums transition-all duration-700 ${flash ? "text-glow-green" : ""}`}>
              {animatedGreens}
            </p>
          </div>
          <Zap className={`w-4 h-4 transition-colors duration-700 ${flash ? "text-yellow-400 fill-yellow-400" : "text-primary"}`} />
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3 w-full h-1 bg-white/5 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${flash ? "bg-yellow-500" : "bg-primary"}`}
          style={{ width: `${Math.min(winRate, 100)}%` }}
        />
      </div>
      <p className="text-xs text-zinc-700 mt-1 font-bold">{winRate}% assertividade</p>
    </div>
  );
}
