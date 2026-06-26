import { useState, useEffect, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Target, ExternalLink, Zap, RefreshCw, Shield, TrendingUp, TrendingDown } from "lucide-react";
import { useGenerateSignal } from "@/hooks/use-radar";
import { useMetrics } from "@/hooks/use-metrics";

function ConfidenceMeter({ value }: { value: number }) {
  const color = value >= 85 ? 'text-primary border-primary shadow-[0_0_20px_rgba(34,197,94,0.4)]'
    : value >= 70 ? 'text-yellow-500 border-yellow-500 shadow-[0_0_20px_rgba(234,179,8,0.4)]'
    : 'text-destructive border-destructive shadow-[0_0_20px_rgba(239,68,68,0.4)]';

  const bgColor = value >= 85 ? 'bg-primary' : value >= 70 ? 'bg-yellow-500' : 'bg-destructive';
  const degrees = (value / 100) * 180;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className={`w-32 h-32 rounded-full border-4 flex items-center justify-center ${color} bg-black/30 transition-all duration-1000`}>
        <div className="text-center">
          <div className="text-4xl font-display font-bold">{value}</div>
          <div className="text-xs font-bold opacity-60 tracking-wider">%</div>
        </div>
      </div>
      <div className="w-48 h-2 bg-white/5 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full confidence-fill ${bgColor}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">Índice de Confiança</span>
    </div>
  );
}

function Countdown({ seconds, onEnd }: { seconds: number; onEnd: () => void }) {
  const [remaining, setRemaining] = useState(seconds);
  const endedRef = useRef(false);

  useEffect(() => {
    setRemaining(seconds);
    endedRef.current = false;
  }, [seconds]);

  useEffect(() => {
    if (remaining <= 0 && !endedRef.current) {
      endedRef.current = true;
      onEnd();
      return;
    }
    if (remaining <= 0) return;

    const timer = setTimeout(() => {
      setRemaining(prev => Math.max(0, prev - 1));
    }, 1000);
    return () => clearTimeout(timer);
  }, [remaining, onEnd]);

  const pct = ((seconds - remaining) / seconds) * 100;
  const color = remaining > 15 ? 'text-primary' : remaining > 7 ? 'text-yellow-500' : 'text-destructive';

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-primary to-yellow-500 rounded-full confidence-fill"
          style={{ width: `${pct}%`, transition: "width 1s linear" }}
        />
      </div>
      <span className={`text-sm font-bold font-display ${color} transition-colors`}>
        Sinal expira em {remaining}s
      </span>
    </div>
  );
}

export default function EntradaPage() {
  const generateSignal = useGenerateSignal();
  const { data: metrics } = useMetrics();
  const [signal, setSignal] = useState<{
    entry: string; targetColor: string; confidence: number; protection: string; countdown: number;
  } | null>(null);
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    // Auto-generate on mount
    generateSignal.mutateAsync().then(setSignal).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    setExpired(false);
    const s = await generateSignal.mutateAsync();
    setSignal(s);
  };

  const colorIsRed = signal?.targetColor === 'red';
  const colorIsBlack = signal?.targetColor === 'black';

  return (
    <div className="space-y-8 max-w-3xl mx-auto mt-4">

      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-display text-white tracking-wide flex items-center justify-center gap-3">
          <Target className="w-8 h-8 text-yellow-500" />
          POSSÍVEL ENTRADA
        </h1>
        <p className="text-zinc-500 text-sm">Análise do algoritmo RADAR DO GREEN em tempo real</p>
      </div>

      {/* Win/Loss mini strip */}
      {metrics && (
        <div className="flex items-center justify-center gap-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary" />
            <span className="text-sm font-bold text-zinc-400">{metrics.winRate}% acerto</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm font-bold text-zinc-400">{metrics.currentStreak} streak</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-2">
            {metrics.lastSignalResult === 'win' ? (
              <TrendingUp className="w-4 h-4 text-primary" />
            ) : (
              <TrendingDown className="w-4 h-4 text-destructive" />
            )}
            <span className={`text-sm font-bold ${metrics.lastSignalResult === 'win' ? 'text-primary' : 'text-destructive'}`}>
              Último: {metrics.lastSignalResult === 'win' ? 'WIN' : metrics.lastSignalResult === 'loss' ? 'LOSS' : '—'}
            </span>
          </div>
        </div>
      )}

      {/* Main Signal Card — Glassmorphism */}
      <div className={`glass-casino rounded-2xl overflow-hidden border transition-all duration-700 relative
        ${!expired && signal
          ? signal.confidence >= 85
            ? 'border-primary/30 neon-border-green shadow-[0_30px_80px_rgba(0,0,0,0.6),0_0_60px_rgba(34,197,94,0.15)]'
            : signal.confidence >= 70
            ? 'border-yellow-500/25 neon-border-gold shadow-[0_30px_80px_rgba(0,0,0,0.6),0_0_40px_rgba(234,179,8,0.1)]'
            : 'border-destructive/25 shadow-[0_30px_80px_rgba(0,0,0,0.6)]'
          : 'border-white/6 shadow-[0_20px_60px_rgba(0,0,0,0.5)]'}
      `}>
        {/* Background depth layers */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-80 h-40 bg-primary/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-0 w-60 h-32 bg-yellow-500/4 rounded-full blur-2xl" />
        </div>
        {/* Top gradient bar */}
        {signal && !expired && (
          <div className={`h-1 w-full ${
            signal.confidence >= 85
              ? 'bg-gradient-to-r from-primary/0 via-primary to-primary/0'
              : signal.confidence >= 70
              ? 'bg-gradient-to-r from-yellow-500/0 via-yellow-500 to-yellow-500/0'
              : 'bg-gradient-to-r from-destructive/0 via-destructive to-destructive/0'
          }`} />
        )}

        <div className="relative z-10 p-8 md:p-12 flex flex-col items-center gap-8 text-center">
          {generateSignal.isPending ? (
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="w-16 h-16 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
              <p className="text-zinc-400 font-bold uppercase tracking-widest text-sm">Analisando padrões...</p>
            </div>
          ) : expired ? (
            <div className="flex flex-col items-center gap-4 py-8">
              <p className="text-xl font-display text-zinc-500">SINAL EXPIRADO</p>
              <button
                onClick={handleGenerate}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-primary/15 border border-primary/30 text-primary font-bold hover:bg-primary/25 transition-all"
              >
                <RefreshCw className="w-4 h-4" /> Gerar Novo Sinal
              </button>
            </div>
          ) : signal ? (
            <>
              {/* Confidence Meter */}
              <ConfidenceMeter value={signal.confidence} />

              {/* Signal direction badge */}
              <div className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-full border font-bold tracking-widest text-sm ${
                signal.confidence >= 85
                  ? 'bg-primary/15 border-primary/40 text-primary'
                  : 'bg-yellow-500/15 border-yellow-500/40 text-yellow-500'
              }`}>
                <Zap className="w-4 h-4 fill-current animate-pulse" />
                ENTRADA CONFIRMADA
              </div>

              {/* Entry Text */}
              <div className="space-y-2">
                <h2 className="text-2xl md:text-3xl font-display text-white leading-tight">
                  APOSTE NO{" "}
                  <span className={colorIsRed ? 'text-destructive text-glow-red' : colorIsBlack ? 'text-zinc-300' : 'text-primary text-glow-green'}>
                    {signal.targetColor === 'red' ? 'VERMELHO' : signal.targetColor === 'black' ? 'PRETO' : 'VERDE'}
                  </span>
                </h2>
                <p className="text-zinc-400 font-medium">{signal.entry}</p>
              </div>

              {/* Protection badge */}
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-zinc-300 text-sm font-bold">
                <Shield className="w-4 h-4 text-yellow-500" />
                Proteção: {signal.protection}
              </div>

              {/* Countdown */}
              <div className="w-full max-w-sm">
                <Countdown seconds={signal.countdown} onEnd={() => setExpired(true)} />
              </div>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 w-full max-w-sm">
                <a
                  href="https://geralbet.bet.br/games/playtech/roleta-brasileira"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 h-12 rounded-xl bg-primary text-primary-foreground font-bold text-sm hover:-translate-y-0.5 transition-all shadow-[0_8px_30px_rgba(34,197,94,0.3)]"
                >
                  <ExternalLink className="w-4 h-4" />
                  ABRIR ROLETA
                </a>
                <button
                  onClick={handleGenerate}
                  className="flex items-center justify-center gap-2 px-4 h-12 rounded-xl border border-white/10 text-zinc-400 hover:text-white hover:border-white/20 transition-all font-bold text-sm"
                >
                  <RefreshCw className="w-4 h-4" />
                  Novo Sinal
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center gap-4 py-8">
              <Target className="w-14 h-14 text-zinc-700" />
              <p className="text-zinc-500 font-bold uppercase tracking-widest text-sm">Nenhum sinal disponível</p>
              <button
                onClick={handleGenerate}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-primary/15 border border-primary/30 text-primary font-bold hover:bg-primary/25 transition-all"
              >
                <Zap className="w-4 h-4" /> Gerar Sinal
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
