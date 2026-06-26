from typing import List

# --- CONFIGURAÇÃO DA ROLETA ---
# Roleta Europeia (Single Zero)
ROULETTE_WHEEL = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

# Números da região "Tier" (Tiers du Cylindre)
TIER_NUMBERS = [5, 8, 10, 11, 13, 16, 23, 24, 27, 30, 33, 36]

def get_neighbors(number: int, count: int) -> List[int]:
    """
    Retorna a lista de vizinhos na roda (esquerda e direita).
    Inclui o próprio número.
    Complexidade: O(1) pois a roda é fixa e pequena.
    """
    try:
        idx = ROULETTE_WHEEL.index(number)
    except ValueError:
        return []

    indices = []
    wheel_len = len(ROULETTE_WHEEL)
    
    # Vizinhos para esquerda e direita
    for i in range(1, count + 1):
        indices.append((idx - i) % wheel_len)
        indices.append((idx + i) % wheel_len)

    # Inclui o próprio número
    result = [ROULETTE_WHEEL[i] for i in indices]
    result.append(number)
    
    return sorted(list(set(result)))

def get_terminal_numbers(terminal: int) -> List[int]:
    """
    Retorna todos os números que terminam com o dígito especificado.
    Ex: Terminal 4 -> [4, 14, 24, 34]
    """
    return [n for n in ROULETTE_WHEEL if n % 10 == terminal]
