import os

# Flag de debug engine
ENGINE_DEBUG = os.getenv('ENGINE_DEBUG', 'False').lower() == 'true'

from .core import StrategyState
from .registry import registry, ESTRATEGIAS
from .formatter import format_strategy_message

# Funções de compatibilidade para manter a interface antiga
def pre_process_strategies() -> int:
    return registry.preload()

def get_optimized_strategy(numero: int):
    return registry.get_strategy(numero)

def gerar_mensagem_por_numero(numero: int) -> str | None:
    from .formatter import format_legacy_message
    strategy = registry.get_strategy(numero)
    if strategy:
        return format_legacy_message(numero, strategy['raw'])
    return None
