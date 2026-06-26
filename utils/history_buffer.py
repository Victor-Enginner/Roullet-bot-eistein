import collections
import logging
from typing import List, Optional
from config.settings import Settings

logger = logging.getLogger('history_buffer')

class HistoryBuffer:
    """
    Buffer persistente estruturado como fila FIFO para reter histórico da roleta.
    Implementa validação de integridade temporal para ambiente Windows 10.
    """
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.buffer = collections.deque(maxlen=max_size) # Armazena (numero, timestamp)
        self.last_ts = 0.0
        self.repetition_count = 0

    def add(self, number: int, timestamp: float) -> bool:
        """
        Adiciona um novo número validando a integridade temporal (Windows 10).
        """
        # 1. Tratamento de Batch Delivery do Windows (Timestamps idênticos)
        if timestamp <= self.last_ts:
            # Insere um delay sintético de 200ms para permitir o processamento do batch
            timestamp = self.last_ts + 0.2
            logger.info(f"💾 Windows Batch: Ajustando timestamp sintético para {number} (+200ms)")

        # 2. Validação de Repetição Suspeita (Somente se <= 200ms e mesmo número)
        delta = timestamp - self.last_ts
        last_num = list(self.buffer)[-1][0] if self.buffer else None
        
        if last_num is not None and last_num == number and delta <= 0.21: # Buffer de 0.01s
            self.repetition_count += 1
            if self.repetition_count >= Settings.MAX_REPETITIONS_FOR_INVALID:
                logger.warning(f"⚠️ Integridade: Repetição excessiva de {number} em batch. Ignorado.")
                return False
        else:
            self.repetition_count = 0

        self.buffer.append((number, timestamp))
        self.last_ts = timestamp
        return True

    def get_last(self, n: int) -> List[int]:
        """Retorna os últimos `n` números (apenas os valores)."""
        if n <= 0: return []
        lst = list(self.buffer)
        subset = lst[-n:] if n < len(lst) else lst
        return [item[0] for item in subset]

    def get_all(self) -> List[int]:
        """Retorna todos os números atualmente no buffer."""
        return [item[0] for item in self.buffer]

    def clear(self):
        """Limpa o buffer para reset de análise."""
        self.buffer.clear()
        self.last_ts = 0.0

    def __len__(self) -> int:
        return len(self.buffer)
