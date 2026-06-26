from typing import Dict, Optional
from .parser import parse_strategy_targets, parse_protection_targets
from config.settings import Settings
import logging
from strategy.presets.default_terminals import ESTRATEGIAS
from estrategias import BLACKLIST

logger = logging.getLogger("engine.registry")

# --- ESTRATÉGIAS importadas do arquivo central ---


class StrategyRegistry:
    def __init__(self):
        self.optimized_strategies = {}
        self.initialized = False

    def preload(self) -> int:
        """
        Pré-compila todas as estratégias na inicialização.
        Retorna a contagem de estratégias válidas.
        """
        self.optimized_strategies.clear()
        count = 0
        ignored = 0

        logger.info("Iniciando preload de estratégias...")

        for numero, dados in ESTRATEGIAS.items():
            # Bloqueio conforme especificações do motor central
            if (
                numero in BLACKLIST
                or not dados
                or dados.get("leitura") == "Estratégia não definida."
                or not dados.get("entrada")
            ):
                ignored += 1
                continue

            entrada_str = dados["entrada"]

            # Normalização de texto para compatibilidade com parser novo
            if "laterais" in entrada_str:
                entrada_str = entrada_str.replace("laterais", "vizinhos")

            # Caso especial #8 "Cobrir Tier 7 vizinhos e 32 3 vizinhos" -> Parser não suporta isso ainda complexo assim
            # Vamos tentar simplificar ou ignorar por enquanto
            # O user pediu para melhorar o parser.

            entry_targets = parse_strategy_targets(entrada_str)
            protection_targets = parse_protection_targets(dados.get("cobertura", ""))

            if entry_targets:
                self.optimized_strategies[numero] = {
                    "entry": entry_targets,
                    "protection": protection_targets,
                    "raw": dados,
                }
                count += 1
            else:
                logger.warning(
                    f"Estratégia {numero} ignorada: Falha no parser de entrada ('{entrada_str}')"
                )
                ignored += 1

        self.initialized = True
        logger.info(
            f"⚡ Preload: {count} estratégias carregadas ({ignored} bloqueadas/inválidas)"
        )

        return count

    def get_strategy(self, numero: int) -> Optional[Dict]:
        if not self.initialized:
            self.preload()
        return self.optimized_strategies.get(numero)


# Instância global (Singleton)
registry = StrategyRegistry()
