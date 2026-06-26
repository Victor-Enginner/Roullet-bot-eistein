import sqlite3
from datetime import datetime
from typing import List, Optional


class DecisionEngine:
    """Motor de decisão enxuto para roleta ao vivo (Martingale modificada)."""

    def __init__(self, db_path: str = "data/live_bot.db"):
        self.db_path = db_path
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.db.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                color TEXT,
                strategy TEXT,
                bet_size INTEGER
            )
            """
        )
        self.db.commit()

    @staticmethod
    def number_color(number: int) -> str:
        """Retorna a cor básica da roleta (RED/BLACK/GREEN)."""
        if number == 0:
            return "GREEN"

        # Padrão europeu: 1-10: odd=red, even=black; 11-18: odd=black, even=red;
        # 19-28: odd=red, even=black; 29-36: odd=black, even=red
        if 1 <= number <= 10 or 19 <= number <= 28:
            return "RED" if number % 2 == 1 else "BLACK"
        return "BLACK" if number % 2 == 1 else "RED"

    def martingale_modificada(self, history: List[int]) -> int:
        """Martingale modificado com reset após 3 vitórias seguidas."""
        if len(history) < 3:
            return 1

        last_three = history[-3:]
        if all(h == last_three[0] for h in last_three):
            return 1

        if len(history) > 4:
            # Somatório das 4 últimas entradas (mais agressivo em sequência perdedora)
            return max(1, sum(history[-4:]))

        return 1

    def log_bet(self, number: int, color: str, strategy: str, bet_size: int):
        self.cursor.execute(
            """
            INSERT INTO history (number, timestamp, color, strategy, bet_size)
            VALUES (?, ?, ?, ?, ?)
            """,
            (number, datetime.now(), color, strategy, bet_size),
        )
        self.db.commit()

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass


# API de conveniência
def create_engine(db_path: Optional[str] = None) -> DecisionEngine:
    return DecisionEngine(db_path=db_path or "data/live_bot.db")
