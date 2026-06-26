import { motion } from 'framer-motion';
import { AlertCircle, TrendingUp, Shield, CheckCircle } from 'lucide-react';
import { useSignalStore } from '@/store/signalStore';
import { cn } from '@/lib/utils';

const statusIcons = {
  IDLE: <AlertCircle className="w-4 h-4 text-gray-400" />,
  ANALYZING: <TrendingUp className="w-4 h-4 text-yellow-400 animate-spin" />,
  SIGNAL_READY: <CheckCircle className="w-4 h-4 text-green-400 pulse-glow" />,
  PROTECTION: <Shield className="w-4 h-4 text-orange-400" />
};

export function SignalCard() {
  const { activeSignal, serverStatus } = useSignalStore();

  if (!activeSignal) return null;

  const confidenceColor = activeSignal.confidence > 0.85 
    ? 'text-green-400' 
    : activeSignal.confidence > 0.7 
    ? 'text-yellow-400' 
    : 'text-orange-400';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={cn(
        "relative bg-card border border-primary/20 rounded-lg p-6 mb-4",
        "card-hover",
        serverStatus === 'analyzing' && "border-yellow-500/50"
      )}
    >
      {/* Status Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          {statusIcons[activeSignal.status]}
          <span className={cn(
            "text-sm font-medium",
            serverStatus === 'analyzing' && "text-yellow-400 animate-pulse"
          )}>
            {serverStatus === 'analyzing' ? 'IA Analisando...' : 'Sinal Pronto'}
          </span>
        </div>
        <div className={cn("text-xs px-2 py-1 rounded", confidenceColor)}>
          {(activeSignal.confidence * 100).toFixed(1)}%
        </div>
      </div>

      {/* Main Signal Info */}
      <div className="space-y-3">
        <div className="flex items-baseline space-x-2">
          <span className="text-3xl font-bold neon-text">
            {activeSignal.number}
          </span>
          <span className="text-sm text-muted-foreground">
            Estratégia: {activeSignal.strategy}
          </span>
        </div>

        {/* Entry & Protection */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-muted-foreground mb-1">Entrada:</div>
            <div className="text-primary font-medium">
              {activeSignal.entry.join(', ')}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Proteção:</div>
            <div className="text-accent font-medium">
              {activeSignal.protection.join(', ') || 'Nenhuma'}
            </div>
          </div>
        </div>
      </div>

      {/* Animated Border Effect */}
      <div className="absolute inset-0 rounded-lg border-2 border-primary/20 pointer-events-none" />
    </motion.div>
  );
}
