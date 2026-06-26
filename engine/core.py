from typing import List, Optional, Set
from .registry import ESTRATEGIAS

class StrategyState:
    def __init__(self, max_attempts: int = 3):
        self.active = False
        self.strategy_id = None
        self.strategy_name = ""
        self.start_number = None
        self.entry_targets: Set[int] = set()
        self.protection_targets: Set[int] = set()
        self.attempt = 0
        self.max_attempts = max_attempts

    def activate(self, strategy_id: int, start_number: int, entry_targets: List[int], protection_targets: List[int]):
        """
        Ativa uma nova estratégia.
        """
        self.active = True
        self.strategy_id = strategy_id
        # Busca nome no dict raw se disponível, se não usa genérico
        # Aqui podemos melhorar se passarmos o objeto de estrategia completo, mas mantendo compatibilidade:
        self.strategy_name = ESTRATEGIAS.get(strategy_id, {}).get("leitura", "Estratégia")
        self.start_number = start_number
        self.entry_targets = set(entry_targets)
        self.protection_targets = set(protection_targets)
        self.attempt = 0

    def reset(self):
        """
        Reseta o estado para Idle.
        """
        self.active = False
        self.strategy_id = None
        self.strategy_name = ""
        self.start_number = None
        self.entry_targets.clear()
        self.protection_targets.clear()
        self.attempt = 0

    def process_number(self, number: int) -> Optional[str]:
        """
        Processa um novo número e transita o estado.
        Retorna: 'WIN_ENTRY', 'WIN_PROTECTION', 'LOSS', 'PROTECTION', ou None
        """
        if not self.active:
            return None

        # 1. Checa WIN na Entrada
        if number in self.entry_targets:
            return "WIN_ENTRY"

        # 2. Checa WIN na Proteção (Zero sempre conta como proteção se solicitado, ou se estiver explicitamente na proteção)
        # Regra do User: "Lógica de proteção 0 = WIN"
        if number == 0:
            return "WIN_PROTECTION"

        if number in self.protection_targets:
            return "WIN_PROTECTION"

        # 3. Incrementa tentativa (Gale)
        self.attempt += 1

        if self.attempt <= self.max_attempts:
            return "PROTECTION"
        else:
            return "LOSS"
