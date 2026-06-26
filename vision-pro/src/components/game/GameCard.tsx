import { motion } from 'framer-motion';
import { Monitor, Play, Pause } from 'lucide-react';
import { cn } from '@/lib/utils';

interface GameCardProps {
  game: {
    id: number;
    name: string;
    provider: string;
    status: 'active' | 'inactive';
  };
}

export function GameCard({ game }: GameCardProps) {
  const isActive = game.status === 'active';

  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className={cn(
        "relative bg-card rounded-lg p-4 border cursor-pointer overflow-hidden",
        "card-hover",
        isActive ? "border-primary/50" : "border-muted"
      )}
    >
      {/* Background Animation */}
      {isActive && (
        <motion.div
          className="absolute inset-0 bg-primary/10"
          animate={{
            opacity: [0, 0.3, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
          }}
        />
      )}

      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          <Monitor className={cn(
            "w-6 h-6",
            isActive ? "text-primary" : "text-muted-foreground"
          )} />
          <div className={cn(
            "w-2 h-2 rounded-full",
            isActive ? "bg-green-400" : "bg-gray-400"
          )} />
        </div>

        <h3 className="font-bold text-sm mb-1">{game.name}</h3>
        <p className="text-xs text-muted-foreground">{game.provider}</p>

        {/* Play/Pause Button */}
        <motion.button
          className="mt-3 w-full py-1 px-2 rounded bg-primary/20 text-primary text-xs"
          whileTap={{ scale: 0.95 }}
        >
          {isActive ? 'MONITORAR' : 'INICIAR'}
        </motion.button>
      </div>
    </motion.div>
  );
}
