import { motion } from 'framer-motion';
import { GameCard } from './GameCard';

const games = [
  { id: 1, name: 'Roleta Brasileira', provider: 'Playtech', status: 'active' as const },
  { id: 2, name: 'Lightning Roulette', provider: 'Evolution', status: 'inactive' as const },
  { id: 3, name: 'Immersive Roulette', provider: 'Playtech', status: 'active' as const },
  { id: 4, name: 'Speed Roulette', provider: 'Evolution', status: 'inactive' as const },
];

export function GameGrid() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6">
      {games.map((game, index) => (
        <motion.div
          key={game.id}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.1 }}
        >
          <GameCard game={game} />
        </motion.div>
      ))}
    </div>
  );
}
