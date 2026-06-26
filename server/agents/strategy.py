from strategy.presets.default_terminals import ESTRATEGIAS


def pick_strategy(last_number: int) -> dict:
    """
    Escolhe a estratégia baseada no último número.
    """
    return ESTRATEGIAS.get(last_number, {})
