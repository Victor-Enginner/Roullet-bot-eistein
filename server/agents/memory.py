from typing import Dict

Stats = Dict[str, int]


class MemoryAgent:
    def __init__(self):
        self.stats_db: Dict[int, Stats] = {}

    def update_stats(self, base: int, result: str):
        """
        Atualiza as estatísticas para a base.
        result: "green" | "g1" | "loss"
        """
        if base not in self.stats_db:
            self.stats_db[base] = {"directGreen": 0, "protectionGreen": 0, "loss": 0}

        if result == "green":
            self.stats_db[base]["directGreen"] += 1
        elif result == "g1":
            self.stats_db[base]["protectionGreen"] += 1
        elif result == "loss":
            self.stats_db[base]["loss"] += 1

    def get_stats(self, base: int) -> Stats:
        return self.stats_db.get(
            base, {"directGreen": 0, "protectionGreen": 0, "loss": 0}
        )
