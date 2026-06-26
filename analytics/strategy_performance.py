from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger('strategy_performance')

class StrategyPerformanceTracker:
    def __init__(self):
        # stats = { strategy_id: { "wins": int, "losses": int, "total": int } }
        self.stats: Dict[int, Dict[str, int]] = {}
        self.already_notified = set() # strategy_id to avoid spam

    def register_win(self, strategy_id: int):
        """Atualiza estatísticas para um WIN (Entrada ou Proteção)"""
        if strategy_id not in self.stats:
            self.stats[strategy_id] = {"wins": 0, "losses": 0, "total": 0}
        
        self.stats[strategy_id]["wins"] += 1
        self.stats[strategy_id]["total"] += 1
        logger.info(f"Analytics: Strategy #{strategy_id} WIN. Total: {self.stats[strategy_id]['total']}")

    def register_loss(self, strategy_id: int):
        """Atualiza estatísticas para um LOSS"""
        if strategy_id not in self.stats:
            self.stats[strategy_id] = {"wins": 0, "losses": 0, "total": 0}
        
        self.stats[strategy_id]["losses"] += 1
        self.stats[strategy_id]["total"] += 1
        logger.info(f"Analytics: Strategy #{strategy_id} LOSS. Total: {self.stats[strategy_id]['total']}")

    def get_winrate(self, strategy_id: int) -> float:
        """Calcula a taxa de acerto atual da estratégia"""
        if strategy_id not in self.stats or self.stats[strategy_id]["total"] == 0:
            return 0.0
        
        stat = self.stats[strategy_id]
        return (stat["wins"] / stat["total"]) * 100

    def get_hot_strategies(self, min_total: int = 10, min_winrate: float = 70.0) -> List[Tuple[int, float]]:
        """Retorna lista de estratégias que batem a meta de performance"""
        hot = []
        for sid in self.stats:
            rate = self.get_winrate(sid)
            if self.stats[sid]["total"] >= min_total and rate >= min_winrate:
                hot.append((sid, rate))
        return hot

    def should_notify(self, strategy_id: int, min_total: int = 10, min_winrate: float = 70.0) -> Optional[float]:
        """
        Verifica se deve enviar um alerta 'Hot Strategy' no Telegram.
        Retorna o winrate se atender aos critérios e ainda não tiver sido notificado 
        nesta sequência de performance.
        """
        stat = self.stats.get(strategy_id)
        if not stat or stat["total"] < min_total:
            return None
            
        winrate = self.get_winrate(strategy_id)
        if winrate >= min_winrate:
            if strategy_id not in self.already_notified:
                self.already_notified.add(strategy_id)
                return winrate
        else:
            # Se cair abaixo da meta, remove do set para permitir nova notificação se subir depois
            if strategy_id in self.already_notified:
                self.already_notified.remove(strategy_id)
                
        return None

# Instância Singleton
tracker = StrategyPerformanceTracker()
