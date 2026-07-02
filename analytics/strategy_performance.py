from typing import Dict, List, Tuple, Optional
import json
import logging
import os

logger = logging.getLogger('strategy_performance')

DEFAULT_STATS_PATH = "data/strategy_performance.json"

class StrategyPerformanceTracker:
    def __init__(self, file_path: str = DEFAULT_STATS_PATH):
        # stats = { strategy_id: { "wins": int, "losses": int, "total": int } }
        self.stats: Dict[int, Dict[str, int]] = {}
        self.already_notified = set() # strategy_id to avoid spam
        self.file_path = file_path
        self.load_stats()

    def load_stats(self):
        """Carrega estatísticas persistidas do disco (se existirem)."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                # Chaves em JSON são sempre strings -> normaliza de volta pra int
                # quando possível, mantendo compatibilidade com o uso interno.
                self.stats = {}
                for key, value in raw.items():
                    try:
                        sid = int(key)
                    except (TypeError, ValueError):
                        sid = key
                    self.stats[sid] = value
            except Exception as e:
                logger.warning(f"Erro ao carregar estatísticas de performance: {e}")
                self.stats = {}

    def save_stats(self):
        """Persiste as estatísticas atuais em disco."""
        try:
            dirname = os.path.dirname(self.file_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {str(k): v for k, v in self.stats.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.warning(f"Erro ao salvar estatísticas de performance: {e}")

    def register_win(self, strategy_id: int):
        """Atualiza estatísticas para um WIN (Entrada ou Proteção)"""
        if strategy_id not in self.stats:
            self.stats[strategy_id] = {"wins": 0, "losses": 0, "total": 0}

        self.stats[strategy_id]["wins"] += 1
        self.stats[strategy_id]["total"] += 1
        logger.info(f"Analytics: Strategy #{strategy_id} WIN. Total: {self.stats[strategy_id]['total']}")
        self.save_stats()

    def register_loss(self, strategy_id: int):
        """Atualiza estatísticas para um LOSS"""
        if strategy_id not in self.stats:
            self.stats[strategy_id] = {"wins": 0, "losses": 0, "total": 0}

        self.stats[strategy_id]["losses"] += 1
        self.stats[strategy_id]["total"] += 1
        logger.info(f"Analytics: Strategy #{strategy_id} LOSS. Total: {self.stats[strategy_id]['total']}")
        self.save_stats()

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

    def should_block(self, strategy_id: int, min_winrate: float = 0.60, min_samples: int = 30) -> bool:
        """
        Decide se uma estratégia deve ser BLOQUEADA de novas entradas por
        performance real ruim.

        Retorna True SOMENTE quando:
          - já existem >= min_samples amostras (wins+losses) para strategy_id; E
          - o winrate real está abaixo de min_winrate.

        Com poucas amostras (< min_samples) NUNCA bloqueia — evita falso
        bloqueio por pouco dado (amostra estatisticamente insignificante).

        Nota de escala: min_winrate é uma FRAÇÃO (0.0 a 1.0), ex.: 0.60 = 60%.
        Internamente get_winrate() retorna em escala percentual (0 a 100),
        então a conversão é feita aqui.
        """
        stat = self.stats.get(strategy_id)
        if not stat or stat.get("total", 0) < min_samples:
            return False

        winrate_fraction = self.get_winrate(strategy_id) / 100.0
        return winrate_fraction < min_winrate

# Instância Singleton
tracker = StrategyPerformanceTracker()
