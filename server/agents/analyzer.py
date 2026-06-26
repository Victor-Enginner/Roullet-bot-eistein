from collections import Counter


def analyze_recent(history: list[int]) -> dict:
    """
    Analisa os últimos 500 números para frequência, terminais, etc.
    """
    last500 = history[-500:] if len(history) >= 500 else history

    # Frequência por número
    frequency = Counter(last500)

    # Frequência por terminal
    terminal_freq = Counter(n % 10 for n in last500)

    # Números quentes (mais frequentes)
    hot_numbers = frequency.most_common(5)

    # Números frios (menos frequentes)
    cold_numbers = sorted(frequency.items(), key=lambda x: x[1])[:5]

    # Dominância de terminais
    terminal_dominance = terminal_freq

    return {
        "hot_numbers": hot_numbers,
        "cold_numbers": cold_numbers,
        "terminal_dominance": terminal_dominance,
        "frequency": dict(frequency),
    }
